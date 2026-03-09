# AI SA Portfolio Monorepo Makefile

.PHONY: help setup test clean
.DEFAULT_GOAL := help

## Display this help message
help:
	@echo "AI SA Portfolio Monorepo Commands:"
	@echo ""
	@grep -E '^##.*$$' $(MAKEFILE_LIST) | sed 's/##/  /' | sort

## Setup development environment for all systems
setup:
	@echo "Setting up AI SA Portfolio development environment..."
	uv sync
	@echo "Installing system dependencies..."
	cd systems/s1-cost && uv sync

## Run tests for S1 (Cost Optimization)
test-s1:
	@echo "Testing S1: Cost Optimization System..."
	cd systems/s1-cost && uv run python test_implementation.py

## Run quick demo for S1
demo-s1:
	@echo "Running S1 quick demo..."
	cd systems/s1-cost && uv run python quick_demo.py

## Run enhanced chat for S1
chat-s1:
	@echo "Starting S1 enhanced chat..."
	cd systems/s1-cost && uv run python enhanced_chat.py

## Run baseline chat for S1
baseline-s1:
	@echo "Starting S1 baseline chat..."
	cd systems/s1-cost && uv run python chat.py

## Clean all generated files
clean:
	@echo "Cleaning generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -type d -name "results" -exec rm -rf {} +
	find . -name "*.csv" -delete
	find . -name "*.json" -delete
	find . -name "*.jsonl" -delete

## Check system status
status:
	@echo "AI SA Portfolio System Status:"
	@echo "=========================="
	@echo "✅ S1-Cost: Ready (Bedrock optimization)"
	@echo "🚧 S2-Pipeline: Planned"
	@echo "🚧 S3-HA: Planned"
	@echo "🚧 S4-Observability: Planned"
	@echo ""
	@echo "📚 Portfolio Projects:"
	@echo "🚧 RAG-QA: Planned"
	@echo "🚧 Multi-Agent: Planned"
	@echo "🚧 MCP-DevOps: Planned"

## Format code using black and ruff
format:
	@echo "Formatting code..."
	ruff format .
	ruff check --fix .

## Check code quality
lint:
	@echo "Checking code quality..."
	ruff check .
	mypy systems/s1-cost/

## Run all tests (when more systems are implemented)
test-all:
	@echo "Running all tests..."
	make test-s1
	# Add other system tests as they are implemented

## Generate architecture documentation
docs:
	@echo "Generating architecture documentation..."
	@echo "📁 Current structure:" > docs/architecture.md
	tree -a -I '.git|__pycache__|*.pyc|.venv|node_modules' >> docs/architecture.md

## Development shortcuts
dev-s1: setup test-s1 demo-s1  ## Complete S1 development setup and testing