---
date: 2026-03-14
plan: AISA
tags: [learning/AI-SA, plan, s1-cost]
---

# Nano Claude Code — Implementation Plan

> **目的**: 为 s1-cost 项目构建一个轻量终端 AI 助手 (Nano Claude Code)，通过 Amazon Bedrock 调用 Claude 模型。每次调用自动发送 metrics 到 CloudWatch，为成本监控 Dashboard / Alarm 提供真实数据。
>
> **对应学习计划**: AISA SYS-1 Week 7-8（CloudWatch Custom Metrics + 成本告警）
>
> **代码仓库**: https://github.com/yepengfan/ai-sa-portfolio → `systems/s1-cost/`

---

## 1. 项目结构

在现有 `systems/s1-cost/` 下新增 `cli/` 目录，复用已有的 `utils/`：

```
systems/s1-cost/
├── cli/
│   ├── __init__.py
│   ├── chat.py            # 主入口：REPL 循环 + 命令解析
│   ├── session.py         # 会话管理：messages history + cost tracking
│   └── commands.py        # slash commands 处理
├── utils/
│   ├── bedrock.py         # 已有 → 新增 streaming 支持
│   ├── metrics.py         # 🆕 CloudWatch put_metric_data wrapper
│   └── config.py          # 已有：model IDs + pricing
├── benchmark/             # 已有，不改
│   └── ...
├── strategies/            # 已有，不改
│   └── ...
└── requirements.txt       # 新增 boto3, rich 依赖（如果还没有）
```

---

## 2. 功能需求

### 2.1 核心交互 (P0)

**多轮对话 REPL**

- 启动后进入交互式循环，等待用户输入
- 维护 `messages` 数组（Bedrock Converse/Messages API 格式），支持多轮上下文
- 每次用户输入 → 拼入 messages → 调用 Bedrock → streaming 输出 → 记录 metrics
- Ctrl+C 优雅退出，打印会话总成本

**Streaming 输出**

- 使用 `bedrock-runtime` 的 `invoke_model_with_response_stream` 或 `converse_stream`
- 逐 chunk 打印到终端（打字机效果）
- streaming 结束后从 response 提取 `usage` (input_tokens, output_tokens)

**CloudWatch Metrics 自动上报 (每次调用)**

- 每次 Bedrock 调用完成后，自动调用 `publish_metrics()`
- 这是本项目的核心目的——为 CloudWatch Dashboard 和 Alarm 提供数据

### 2.2 Slash Commands (P1)

| 命令 | 行为 |
|------|------|
| `/model <name>` | 切换模型。支持 `sonnet` 和 `haiku`（映射到 config.py 中的 model ID） |
| `/file <path>` | 读取本地文件内容，作为下一条 user message 的前缀注入 |
| `/cost` | 打印本次会话累计统计：调用次数、总 token、总费用、按模型分布 |
| `/clear` | 清空 messages history，保留 system prompt，重新开始对话 |
| `/help` | 显示可用命令列表 |
| `/quit` 或 `/exit` | 退出程序，打印会话总成本 |

### 2.3 终端美化 (P2，可选)

- 如果安装了 `rich`，用 `rich.markdown.Markdown` 渲染 AI 回复（代码块语法高亮）
- 如果没有 `rich`，fallback 到纯文本输出
- 每次回复后显示一行 metadata：`[model | tokens in | tokens out | $cost]`

---

## 3. CloudWatch Metrics 设计

这是 W12 学习目标的核心部分。

### 3.1 Metric 结构

```python
Namespace = "BedrockCost"

# Dimensions（每次调用都带）
Dimensions = [
    {"Name": "ModelId", "Value": "sonnet" | "haiku"},
    {"Name": "Caller", "Value": "nano-cc"},      # 区分来源（后续 benchmark 用 "benchmark"）
]

# Metrics（每次调用发 3 个）
MetricData = [
    {"MetricName": "InputTokens",  "Value": input_tokens,  "Unit": "Count"},
    {"MetricName": "OutputTokens", "Value": output_tokens,  "Unit": "Count"},
    {"MetricName": "InferredCost", "Value": cost_usd,       "Unit": "None"},
]
```

### 3.2 metrics.py 接口

```python
import boto3
from datetime import datetime, timezone


def publish_metrics(
    model_id: str,        # "sonnet" | "haiku"
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    caller: str = "nano-cc",
) -> None:
    """发送一次 Bedrock 调用的 metrics 到 CloudWatch."""
    client = boto3.client("cloudwatch")
    client.put_metric_data(
        Namespace="BedrockCost",
        MetricData=[
            {
                "MetricName": "InputTokens",
                "Dimensions": [
                    {"Name": "ModelId", "Value": model_id},
                    {"Name": "Caller", "Value": caller},
                ],
                "Timestamp": datetime.now(timezone.utc),
                "Value": input_tokens,
                "Unit": "Count",
            },
            {
                "MetricName": "OutputTokens",
                "Dimensions": [
                    {"Name": "ModelId", "Value": model_id},
                    {"Name": "Caller", "Value": caller},
                ],
                "Timestamp": datetime.now(timezone.utc),
                "Value": output_tokens,
                "Unit": "Count",
            },
            {
                "MetricName": "InferredCost",
                "Dimensions": [
                    {"Name": "ModelId", "Value": model_id},
                    {"Name": "Caller", "Value": caller},
                ],
                "Timestamp": datetime.now(timezone.utc),
                "Value": cost_usd,
                "Unit": "None",
            },
        ],
    )
```

### 3.3 成本计算

复用 `utils/config.py` 已有的 pricing 常量：

```python
def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """基于 Bedrock pricing 计算单次调用成本 (USD)."""
    pricing = MODEL_PRICING[model]  # 来自 config.py
    return (input_tokens * pricing["input_per_token"]) + (output_tokens * pricing["output_per_token"])
```

---

## 4. CloudWatch Dashboard

在 Nano CC 跑出一些数据后，创建 Dashboard。

### 4.1 Dashboard Widgets

| Widget | 类型 | Metric | 说明 |
|--------|------|--------|------|
| 成本曲线 | Line | `InferredCost` by `ModelId` | 按模型维度的成本趋势 |
| 当日累计成本 | Number | `InferredCost` Sum, 1 Day | 大数字显示 |
| Token 消耗 | Bar | `InputTokens` + `OutputTokens` by `ModelId` | 对比 Sonnet vs Haiku 用量 |
| 调用次数 | Line | `InputTokens` Count by `Caller` | 区分 nano-cc vs benchmark |

### 4.2 创建方式

1. **先在 AWS Console 手动拖拽创建**，确认视觉效果
2. 然后用 `boto3` 或 AWS CLI 导出 Dashboard JSON，保存到代码仓库 `infra/dashboard.json`
3. 提供一个脚本 `infra/create_dashboard.py` 可以一键重建

---

## 5. CloudWatch Alarm + SNS

### 5.1 SNS Topic

```
Topic Name: bedrock-cost-alert
Protocol: Email
Endpoint: <用户邮箱>
```

创建后需要去邮箱确认订阅。

### 5.2 Alarm 配置

```
Alarm Name: bedrock-daily-cost-high
Namespace: BedrockCost
Metric: InferredCost
Statistic: Sum
Period: 86400 (1 day)
Threshold: > 10 (USD)
Comparison: GreaterThanThreshold
Action: 通知 SNS Topic bedrock-cost-alert
```

### 5.3 测试方法

临时把 threshold 设为极低值（如 $0.001），用 Nano CC 发一条消息触发告警，确认收到邮件后改回 $10。

---

## 6. Cost Explorer API

独立脚本，不在 Nano CC 内，放 `utils/cost_explorer.py`：

```python
import boto3
from datetime import date, timedelta


def get_bedrock_cost_trend(days: int = 7) -> list[dict]:
    """拉取过去 N 天 Bedrock 服务的每日成本."""
    ce = boto3.client("ce")
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=days)).isoformat()

    response = ce.get_cost_and_usage(
        TimePeriod={"Start": start, "End": end},
        Granularity="DAILY",
        Filter={
            "Dimensions": {
                "Key": "SERVICE",
                "Values": ["Amazon Bedrock"],
            }
        },
        Metrics=["UnblendedCost"],
    )

    results = []
    for item in response["ResultsByTime"]:
        results.append({
            "date": item["TimePeriod"]["Start"],
            "cost": float(item["Total"]["UnblendedCost"]["Amount"]),
        })
    return results
```

可以作为独立脚本运行，也可以后续集成为 Nano CC 的 `/trend` 命令。

> ⚠️ 注意：Cost Explorer 数据有 24-48h 延迟，看不到今天的数据是正常的。
> ⚠️ IAM 需要 `ce:GetCostAndUsage` 权限。

---

## 7. Bedrock Streaming 实现

扩展现有 `utils/bedrock.py`，新增 streaming 方法：

```python
def stream_bedrock(
    model_id: str,
    messages: list[dict],
    system_prompt: str,
    max_tokens: int = 1024,
) -> Generator[str, None, dict]:
    """
    Streaming 调用 Bedrock，yield 每个 text chunk。
    最终 return usage dict: {"input_tokens": int, "output_tokens": int}

    使用 converse_stream API:
    - client.converse_stream(modelId=..., messages=..., system=[...])
    - 从 stream events 中提取 contentBlockDelta.delta.text
    - 从 metadata.usage 提取 token counts
    """
```

推荐用 `converse_stream` 而非 `invoke_model_with_response_stream`，因为：
- `converse_stream` 是 Bedrock 的统一 API，支持所有模型
- 自动返回 `usage` 在 `metadata` event 里，不需要自己拼

---

## 8. System Prompt

```
You are a helpful coding assistant running in a terminal.
Keep responses concise and use markdown formatting.
When showing code changes, use diff format or clearly indicate what to modify.
Respond in the same language the user uses.
```

---

## 9. 运行方式

```bash
cd systems/s1-cost
python -m cli.chat
```

或者加 alias：

```bash
alias nano-cc="python -m cli.chat --dir /path/to/s1-cost"
```

### IAM 权限要求

调用方（本地 AWS profile 或 IAM role）需要：

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream",
    "cloudwatch:PutMetricData",
    "ce:GetCostAndUsage"
  ],
  "Resource": "*"
}
```

---

## 10. 验收标准

### Nano CC 功能

| # | 标准 | 通过条件 |
|---|------|---------|
| 1 | 多轮对话 | 连续 3 轮对话，AI 能引用之前的上下文 |
| 2 | Streaming | 回复逐字打印，不是等全部完成再输出 |
| 3 | `/model` 切换 | 切换 haiku ↔ sonnet，下一次调用用新模型 |
| 4 | `/file` 读文件 | 读入一个 .py 文件，AI 能分析其内容 |
| 5 | `/cost` 统计 | 显示调用次数 + 总 token + 总费用 + 模型分布 |
| 6 | 每次调用后 metrics 已发送 | CloudWatch Console → Custom Namespaces → BedrockCost 可见数据 |

### CloudWatch 监控

| # | 标准 | 通过条件 |
|---|------|---------|
| 7 | Dashboard | 显示实时成本曲线，能按模型维度筛选 |
| 8 | Alarm | 触发时收到邮件通知（低阈值测试） |
| 9 | Cost Explorer | 脚本能查询过去 7 天 Bedrock 成本趋势 |

---

## 11. 不做什么

- ❌ `/run` 执行 shell 命令 — 安全性复杂，不在 scope 内
- ❌ Tool use / function calling — 这是阶段 2 LangChain Agent 的内容
- ❌ 对话持久化（保存到文件/DB）— 退出即丢失，保持简单
- ❌ 认证/多用户 — 纯本地 CLI
- ❌ 修改现有 `strategies/` 或 `benchmark/` 代码

---

## 12. 依赖

```
boto3          # 已有
rich           # 新增：终端 Markdown 渲染（可选，graceful fallback）
```

不需要 `langchain`。直接用 `boto3` 调用 Bedrock，保持轻量。
