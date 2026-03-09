"""Bedrock Batch Inference implementation for non-realtime processing with cost optimization."""

import boto3
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

class BatchJobStatus(Enum):
    """Batch job status options."""
    SUBMITTED = "Submitted"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    STOPPED = "Stopped"

class BedrockBatchProcessor:
    """
    Implements Bedrock Batch Inference for non-realtime processing.
    Offers cost savings for batch operations that don't require immediate responses.
    """

    def __init__(self, region_name: str = "us-east-1", s3_bucket: str = None):
        self.bedrock_client = boto3.client("bedrock", region_name=region_name)
        self.s3_client = boto3.client("s3", region_name=region_name)
        self.region_name = region_name
        self.s3_bucket = s3_bucket or f"bedrock-batch-{uuid.uuid4().hex[:8]}"

        # Batch processing statistics
        self.batch_stats = {
            "jobs_submitted": 0,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "total_queries_batched": 0,
            "total_batch_cost": 0.0,
            "total_realtime_equivalent_cost": 0.0
        }

    def create_batch_job(self,
                        queries: List[Dict[str, Any]],
                        model_id: str,
                        job_name: Optional[str] = None,
                        output_data_config: Optional[Dict[str, str]] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Create a batch inference job.

        Args:
            queries: List of query dictionaries with 'messages' and optional parameters
            model_id: Bedrock model ID to use
            job_name: Optional job name (auto-generated if not provided)
            output_data_config: S3 output configuration

        Returns:
            Tuple of (job_arn, job_metadata)
        """
        if not queries:
            raise ValueError("No queries provided for batch processing")

        # Generate job name if not provided
        if not job_name:
            job_name = f"aisa-batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"

        # Prepare input data in JSONL format
        input_s3_key = f"batch-input/{job_name}/input.jsonl"
        self._upload_batch_input(queries, input_s3_key)

        # Configure output location
        if not output_data_config:
            output_data_config = {
                "s3OutputDataConfig": {
                    "s3Uri": f"s3://{self.s3_bucket}/batch-output/{job_name}/"
                }
            }

        try:
            # Create batch job
            response = self.bedrock_client.create_model_invocation_job(
                jobName=job_name,
                roleArn=self._get_or_create_batch_role(),
                modelId=model_id,
                inputDataConfig={
                    "s3InputDataConfig": {
                        "s3Uri": f"s3://{self.s3_bucket}/{input_s3_key}"
                    }
                },
                outputDataConfig=output_data_config,
                timeoutDurationInHours=24  # 24-hour timeout
            )

            job_arn = response["jobArn"]
            self.batch_stats["jobs_submitted"] += 1
            self.batch_stats["total_queries_batched"] += len(queries)

            job_metadata = {
                "job_arn": job_arn,
                "job_name": job_name,
                "model_id": model_id,
                "query_count": len(queries),
                "input_s3_uri": f"s3://{self.s3_bucket}/{input_s3_key}",
                "output_s3_uri": output_data_config["s3OutputDataConfig"]["s3Uri"],
                "created_at": datetime.now().isoformat(),
                "status": BatchJobStatus.SUBMITTED.value
            }

            return job_arn, job_metadata

        except Exception as e:
            self.batch_stats["jobs_failed"] += 1
            raise Exception(f"Failed to create batch job: {str(e)}")

    def monitor_batch_job(self, job_arn: str) -> Dict[str, Any]:
        """
        Monitor the status of a batch job.

        Args:
            job_arn: ARN of the batch job to monitor

        Returns:
            Job status and metrics
        """
        try:
            response = self.bedrock_client.get_model_invocation_job(jobIdentifier=job_arn)

            status = response["status"]
            job_details = {
                "job_arn": job_arn,
                "status": status,
                "created_at": response["creationTime"].isoformat(),
                "model_id": response["modelId"],
                "input_token_count": response.get("inputTokenCount", 0),
                "output_token_count": response.get("outputTokenCount", 0)
            }

            if "endTime" in response:
                job_details["ended_at"] = response["endTime"].isoformat()
                job_details["duration_seconds"] = (response["endTime"] - response["creationTime"]).total_seconds()

            if "failureMessage" in response:
                job_details["failure_message"] = response["failureMessage"]

            # Update statistics based on status
            if status == BatchJobStatus.COMPLETED.value:
                self._update_completion_stats(job_details)
            elif status == BatchJobStatus.FAILED.value:
                self.batch_stats["jobs_failed"] += 1

            return job_details

        except Exception as e:
            return {"job_arn": job_arn, "error": str(e), "status": "ERROR"}

    def get_batch_results(self, job_arn: str, output_s3_uri: str) -> List[Dict[str, Any]]:
        """
        Retrieve results from a completed batch job.

        Args:
            job_arn: ARN of the batch job
            output_s3_uri: S3 URI where results are stored

        Returns:
            List of result dictionaries
        """
        try:
            # Parse S3 URI to get bucket and key
            s3_parts = output_s3_uri.replace("s3://", "").split("/", 1)
            bucket = s3_parts[0]
            key_prefix = s3_parts[1] if len(s3_parts) > 1 else ""

            # List objects in output location
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=key_prefix)

            results = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    if obj["Key"].endswith(".jsonl"):
                        # Download and parse JSONL output
                        obj_response = self.s3_client.get_object(Bucket=bucket, Key=obj["Key"])
                        content = obj_response["Body"].read().decode("utf-8")

                        # Parse JSONL
                        for line in content.strip().split("\n"):
                            if line.strip():
                                try:
                                    result = json.loads(line)
                                    results.append(result)
                                except json.JSONDecodeError:
                                    continue

            return results

        except Exception as e:
            raise Exception(f"Failed to retrieve batch results: {str(e)}")

    def _upload_batch_input(self, queries: List[Dict[str, Any]], s3_key: str):
        """Upload batch input data to S3 in JSONL format."""
        # Ensure S3 bucket exists
        self._ensure_s3_bucket()

        # Convert queries to JSONL format
        jsonl_content = ""
        for i, query in enumerate(queries):
            batch_record = {
                "recordId": f"query-{i:04d}",
                "modelInput": {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": query.get("max_tokens", 1024),
                    "messages": query["messages"]
                }
            }

            # Add optional parameters
            if "system" in query:
                batch_record["modelInput"]["system"] = query["system"]
            if "temperature" in query:
                batch_record["modelInput"]["temperature"] = query["temperature"]

            jsonl_content += json.dumps(batch_record) + "\n"

        # Upload to S3
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=s3_key,
            Body=jsonl_content.encode("utf-8"),
            ContentType="application/x-jsonlines"
        )

    def _ensure_s3_bucket(self):
        """Ensure S3 bucket exists for batch processing."""
        try:
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
        except:
            # Bucket doesn't exist, create it
            if self.region_name == "us-east-1":
                self.s3_client.create_bucket(Bucket=self.s3_bucket)
            else:
                self.s3_client.create_bucket(
                    Bucket=self.s3_bucket,
                    CreateBucketConfiguration={"LocationConstraint": self.region_name}
                )

    def _get_or_create_batch_role(self) -> str:
        """Get or create IAM role for batch processing."""
        # This is a simplified implementation
        # In practice, you'd create a proper IAM role with required permissions
        return f"arn:aws:iam::{self._get_account_id()}:role/BedrockBatchProcessingRole"

    def _get_account_id(self) -> str:
        """Get AWS account ID."""
        sts_client = boto3.client("sts")
        return sts_client.get_caller_identity()["Account"]

    def _update_completion_stats(self, job_details: Dict[str, Any]):
        """Update statistics when a job completes."""
        self.batch_stats["jobs_completed"] += 1

        # Estimate costs (this would be more accurate with actual pricing data)
        input_tokens = job_details.get("input_token_count", 0)
        output_tokens = job_details.get("output_token_count", 0)

        # Estimate batch cost (typically 50% discount over real-time)
        batch_discount = 0.5
        estimated_realtime_cost = (input_tokens / 1000 * 0.003) + (output_tokens / 1000 * 0.015)  # Sonnet pricing
        estimated_batch_cost = estimated_realtime_cost * batch_discount

        self.batch_stats["total_batch_cost"] += estimated_batch_cost
        self.batch_stats["total_realtime_equivalent_cost"] += estimated_realtime_cost

    def get_batch_statistics(self) -> Dict[str, Any]:
        """Get comprehensive batch processing statistics."""
        total_jobs = self.batch_stats["jobs_submitted"]
        if total_jobs == 0:
            return {"message": "No batch jobs submitted yet"}

        completion_rate = self.batch_stats["jobs_completed"] / total_jobs
        failure_rate = self.batch_stats["jobs_failed"] / total_jobs

        cost_savings = (self.batch_stats["total_realtime_equivalent_cost"] -
                       self.batch_stats["total_batch_cost"])

        savings_percentage = (cost_savings / self.batch_stats["total_realtime_equivalent_cost"] * 100
                            if self.batch_stats["total_realtime_equivalent_cost"] > 0 else 0)

        return {
            "total_jobs_submitted": total_jobs,
            "jobs_completed": self.batch_stats["jobs_completed"],
            "jobs_failed": self.batch_stats["jobs_failed"],
            "completion_rate": round(completion_rate, 3),
            "failure_rate": round(failure_rate, 3),
            "total_queries_batched": self.batch_stats["total_queries_batched"],
            "avg_queries_per_job": (self.batch_stats["total_queries_batched"] / total_jobs
                                  if total_jobs > 0 else 0),
            "estimated_batch_cost": round(self.batch_stats["total_batch_cost"], 6),
            "estimated_realtime_cost": round(self.batch_stats["total_realtime_equivalent_cost"], 6),
            "estimated_cost_savings": round(cost_savings, 6),
            "estimated_savings_percentage": round(savings_percentage, 2)
        }

class BatchQueryManager:
    """
    High-level manager for batch query operations.
    Handles queueing, batching, and result management.
    """

    def __init__(self, region_name: str = "us-east-1", s3_bucket: str = None):
        self.processor = BedrockBatchProcessor(region_name, s3_bucket)
        self.query_queue = []
        self.active_jobs = {}

    def queue_query(self, user_input: str, messages: List[Dict[str, str]],
                   max_tokens: int = 1024, **kwargs):
        """
        Queue a query for batch processing.

        Args:
            user_input: User input text
            messages: Conversation messages
            max_tokens: Maximum output tokens
            **kwargs: Additional parameters
        """
        query = {
            "messages": messages,
            "max_tokens": max_tokens,
            "user_input": user_input,
            "queued_at": datetime.now().isoformat(),
            **kwargs
        }

        self.query_queue.append(query)

    def submit_batch_when_ready(self, batch_size: int = 10,
                               model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0") -> Optional[str]:
        """
        Submit queued queries as batch job when enough queries are accumulated.

        Args:
            batch_size: Minimum queries to trigger batch submission
            model_id: Model to use for batch processing

        Returns:
            Job ARN if batch was submitted, None otherwise
        """
        if len(self.query_queue) >= batch_size:
            # Submit current queue as batch
            queries_to_batch = self.query_queue[:batch_size]
            self.query_queue = self.query_queue[batch_size:]

            job_arn, job_metadata = self.processor.create_batch_job(
                queries=queries_to_batch,
                model_id=model_id
            )

            self.active_jobs[job_arn] = job_metadata
            return job_arn

        return None

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        return {
            "queued_queries": len(self.query_queue),
            "active_jobs": len(self.active_jobs),
            "oldest_queued": (self.query_queue[0]["queued_at"] if self.query_queue else None),
            "active_job_arns": list(self.active_jobs.keys())
        }

    def check_completed_jobs(self) -> List[Dict[str, Any]]:
        """Check for completed jobs and return their results."""
        completed_jobs = []

        for job_arn in list(self.active_jobs.keys()):
            job_status = self.processor.monitor_batch_job(job_arn)

            if job_status["status"] == BatchJobStatus.COMPLETED.value:
                # Job completed, get results
                job_metadata = self.active_jobs[job_arn]
                try:
                    results = self.processor.get_batch_results(
                        job_arn, job_metadata["output_s3_uri"]
                    )
                    job_status["results"] = results
                    completed_jobs.append(job_status)

                    # Remove from active jobs
                    del self.active_jobs[job_arn]

                except Exception as e:
                    job_status["result_error"] = str(e)
                    completed_jobs.append(job_status)

            elif job_status["status"] == BatchJobStatus.FAILED.value:
                # Job failed
                completed_jobs.append(job_status)
                del self.active_jobs[job_arn]

        return completed_jobs