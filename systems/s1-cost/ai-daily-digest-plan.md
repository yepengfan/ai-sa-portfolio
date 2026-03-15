---
date: 2026-03-15
plan: AISA
tags: [learning/AI-SA, plan, s1-cost]
---

# AI Daily Digest — Implementation Plan

> **目的**: 构建一个 AI/科技每日早报工具。从 Andrej Karpathy 推荐的 90 个顶级技术博客抓取文章，通过 Amazon Bedrock 评分、筛选、总结，生成中英双语早报保存到 Obsidian vault。每天早上打开 Obsidian 时自动触发。
>
> **一石二鸟**:
> - **个人价值**: 每天 5 分钟掌握 AI/科技动态，不用刷 Twitter
> - **学习价值**: 真实 Bedrock 用量 → CloudWatch metrics → Dashboard 观测（AISA SYS-1 Week 7-8）
>
> **对应学习计划**: AISA SYS-1 Week 7-8（CloudWatch Custom Metrics + 成本告警）
>
> **代码仓库**: https://github.com/yepengfan/ai-sa-portfolio → `systems/s1-cost/`
>
> **参考项目**: https://github.com/vigorX777/ai-daily-digest（90 个 HN 顶级博客 RSS + Gemini 评分/摘要）

---

## 0. 参考项目分析 (ai-daily-digest)

### 架构

```
90 RSS feeds → 并发抓取(10路) → 时间过滤 → AI 批量评分(10篇/批) → AI 批量摘要 → 趋势总结 → Markdown
```

### 做得好的（保留）

1. **90 个 Karpathy 推荐的 HN 顶级博客 RSS 源** — 信噪比极高，直接复用
2. **3 维度 AI 评分**（相关性/质量/时效性，1-10 分）— 比简单关键词过滤好得多
3. **结构化摘要 prompt** — 4-6 句摘要 + 推荐理由，prompt 写得很好
4. **批处理 + 并发控制** — 10 篇一批，2 批并发，控制 API 压力
5. **6 大分类体系**（AI/ML、安全、工程、工具、观点、其他）
6. **Mermaid 图表 + ASCII 柱状图 + 标签云** — 多种可视化

### 我们要改进的

| 问题 | 改进方案 |
|------|---------|
| **只有博客 RSS**，缺少讨论社区热度 | 加 HN Top Stories API + Reddit |
| **评分只看标题 + 300 字描述** | 对 Top N 篇用 defuddle/trafilatura 抓全文再总结 |
| **没有去重**，同一新闻多个博客写 | 标题相似度去重（简单 Jaccard 或让 AI 合并） |
| **AI/科技内容被通用内容稀释** | 加 AI-focused 源 + 评分时给 AI/ML 类加权 |
| **用 Gemini/OpenAI** | 改用 Bedrock（Haiku 评分 + Sonnet 总结） |
| **不追踪 AI 调用成本** | 每次调用推 CloudWatch metrics |
| **输出通用 Markdown** | 加 Obsidian frontmatter + callout 格式 |
| **TypeScript/Bun** | Python 重写，复用 s1-cost 的 boto3 生态 |

---

## 1. 项目结构

在现有 `systems/s1-cost/` 下新增 `digest/` 目录：

```
systems/s1-cost/
├── digest/
│   ├── __init__.py
│   ├── main.py              # 主入口：pipeline 编排 + CLI
│   ├── sources/
│   │   ├── __init__.py
│   │   └── rss.py           # RSS 并发抓取（90 个 Karpathy 博客）
│   ├── scoring.py           # Bedrock Haiku 评分（3 维度 + 分类 + 关键词）
│   ├── summarizer.py        # Bedrock Sonnet 摘要 + 趋势总结（中英双语）
│   ├── dedup.py             # 标题相似度去重
│   ├── report.py            # Obsidian Markdown 报告生成（中英两个文件）
│   └── feeds.py             # 90 个 RSS 源列表（从参考项目 digest.ts 第 18-111 行移植）
├── utils/
│   ├── bedrock.py           # 已有 → 新增 converse API 封装
│   ├── metrics.py           # 🆕 CloudWatch put_metric_data
│   ├── cost_explorer.py     # 🆕 Cost Explorer API
│   └── config.py            # 已有：model IDs + pricing
├── infra/
│   ├── dashboard.json       # 🆕 CloudWatch Dashboard 定义
│   └── alarm.py             # 🆕 创建 Alarm + SNS 的脚本
├── benchmark/               # 已有，不改
├── strategies/              # 已有，不改
└── requirements.txt         # 新增依赖
```

---

## 2. 数据源设计

### 2.1 核心数据源：Karpathy 推荐的 90 个 HN 顶级技术博客

直接复用 ai-daily-digest 的 90 个 RSS 源（完整列表见参考项目 `digest.ts` 第 18-111 行）。

这 90 个源来自 [Hacker News Popularity Contest 2025](https://refactoringenglish.com/tools/hn-popularity/)，由 Andrej Karpathy 推荐，涵盖：
- **AI/ML**: simonwillison.net, gwern.net, minimaxir.com
- **工程**: antirez.com, matklad.github.io, rachelbythebay.com
- **安全**: krebsonsecurity.com, troyhunt.com
- **思考**: paulgraham.com, dwarkesh.com, garymarcus.substack.com
- 等 90 个经 HN 社区验证的高质量独立博客

**为什么这组源足够好**: 这些博客是 HN 社区多年 upvote 筛选出来的，信噪比远高于任何新闻聚合站。AI/科技相关内容在这 90 个源中自然占比就很高（simonwillison 几乎每天写 AI）。

> 实现时直接将参考项目 `digest.ts` 第 18-111 行的 `RSS_FEEDS` 数组转为 Python list，保持 `name` + `xmlUrl` + `htmlUrl` 结构不变。

### 2.2 数据统一格式

所有数据源输出统一的 `Article` 结构：

```python
@dataclass
class Article:
    title: str
    link: str
    pub_date: datetime
    description: str        # RSS description（可能为空或很短）
    source_name: str        # "simonwillison.net" 等
    source_type: str        # "rss"
```

---

## 3. 处理流水线

```
Step 1: 并发抓取 90 个 RSS 源
  └─ asyncio + aiohttp, 10 路并发, 15s 超时

Step 2: 时间过滤 + 去重
  ├─ 过滤：只保留指定时间窗口内的文章（默认 48h）
  └─ 去重：标题 Jaccard 相似度 > 0.6 的合并

Step 3: Bedrock 评分（Haiku，便宜）
  ├─ 10 篇一批，2 批并发
  ├─ 3 维度评分：相关性 / 质量 / 时效性（1-10）
  ├─ 分类：ai-ml / security / engineering / tools / opinion / other
  ├─ 关键词：2-4 个
  ├─ AI/ML 类加权：总分 = relevance + quality + timeliness + (category == "ai-ml" ? 3 : 0)
  └─ → CloudWatch Metric（每批一次）

Step 4: Bedrock 摘要 ×2（Sonnet，中英双语）
  ├─ 只对 Top N 篇生成摘要（默认 15）
  ├─ 可选：用 trafilatura 抓全文再总结（如果 description < 100 字）
  ├─ 中文版：中文标题 + 中文摘要 + 中文推荐理由
  ├─ 英文版：保留原标题 + 英文摘要 + 英文推荐理由
  └─ → CloudWatch Metric（每批一次）

Step 5: 趋势总结 ×2（Sonnet，中英双语）
  ├─ 中文版：2-3 个宏观趋势（中文）
  ├─ 英文版：2-3 个宏观趋势（English）
  └─ → CloudWatch Metric
```

### Bedrock 调用成本估算

| 步骤 | 模型 | 估算调用次数 | 估算成本 |
|------|------|:-----------:|--------:|
| 评分（~60 篇 ÷ 10/批） | Haiku | ~6 次 | ~$0.003 |
| 摘要 — 中文版（15 篇 ÷ 10/批） | Sonnet | ~2 次 | ~$0.02 |
| 摘要 — 英文版（15 篇 ÷ 10/批） | Sonnet | ~2 次 | ~$0.02 |
| 趋势总结 × 2（中文 + 英文） | Sonnet | 2 次 | ~$0.02 |
| **每日总计** | | **~12 次** | **~$0.06** |

> 每月 ~$1.8，完全在 AWS 预算内。Dashboard 每天有 ~12 个 data points（比单语版更多数据，Dashboard 更好看）。

---

## 4. AI Prompt 设计

### 4.1 评分 Prompt

直接复用参考项目的评分 prompt（`digest.ts` 第 508-564 行），它已经写得很好：
- 3 个维度各有清晰的 1-10 评分标准
- 要求输出 JSON 格式
- 含分类和关键词提取

唯一修改：在 prompt 末尾加一句：
```
特别注意：与 AI、LLM、机器学习直接相关的文章，relevance 应至少给 7 分。
```

### 4.2 摘要 Prompt（中英各跑一次）

复用参考项目的摘要 prompt（`digest.ts` 第 629-673 行），质量很高：
- 结构化摘要（核心问题 → 关键论点 → 结论）
- 明确要求"不要用'本文讨论了'开头"
- 保留关键数字和指标

**中英双语实现**：用同一批 Top N 文章，调用 Sonnet 两次：
- 第一次：prompt 指令 `lang=zh`，输出中文标题 + 中文摘要 + 中文推荐理由
- 第二次：prompt 指令 `lang=en`，输出英文摘要 + 英文推荐理由（标题保留原文）

参考项目的 prompt 已经有 `langInstruction` 变量支持中英切换（第 637-639 行），直接复用。

### 4.3 趋势总结 Prompt（中英各跑一次）

复用参考项目（`digest.ts` 第 734-764 行），用 Top 10 篇归纳 2-3 个宏观趋势。同样中英各跑一次。

> **总结**：参考项目的 prompt 经过了社区验证（1.4k stars），质量高，直接移植。我们的改进在数据源、双语输出和 CloudWatch 基础设施层，不在 prompt 层。

---

## 5. 去重逻辑 (dedup.py)

```python
def deduplicate(articles: list[Article], threshold: float = 0.6) -> list[Article]:
    """
    基于标题的 Jaccard 相似度去重。

    1. 对每篇文章的标题做 word tokenize（小写 + split）
    2. 两两比较 Jaccard similarity = |A ∩ B| / |A ∪ B|
    3. 相似度 > threshold 的文章组成 cluster
    4. 每个 cluster 只保留 community_score 最高的一篇
    """
```

不需要 AI 也不需要外部库，纯 Python 字符串操作。

---

## 6. 报告生成 (report.py) — 中英双语

每次运行生成 **两个文件**，共享同一份评分和排序结果，只是摘要和趋势语言不同。

### 6.1 输出位置

```
Inbox/AI-Daily/2026-03-15.md        ← 中文版（主力阅读）
Inbox/AI-Daily/2026-03-15-en.md     ← 英文版（练英文 + 看原味表达）
```

两个文件互相 wikilink：中文版顶部有 `English version: [[2026-03-15-en]]`，英文版顶部有 `中文版: [[2026-03-15]]`。

### 6.2 中文版格式

```markdown
---
date: 2026-03-15
tags: [ai-daily, digest]
lang: zh
sources: 90 RSS (Karpathy curated)
articles_scanned: 156
articles_selected: 15
bedrock_cost: $0.063
---

# 🗞️ AI 早报 — 2026-03-15

> Karpathy 推荐的 90 个顶级技术博客 | Bedrock Haiku+Sonnet 生成
> English version: [[2026-03-15-en]]

## 📝 今日看点

[2-3 句中文宏观趋势总结]

---

## 🏆 今日必读

> [!tip] 🥇 GPT-5 Turbo 发布，推理成本降 40%
> [GPT-5 Turbo Released with 40% Cost Reduction](https://...)
> — openai.com · 3 小时前 · 🤖 AI/ML
>
> GPT-5 Turbo 在保持 GPT-5 水平的同时大幅降低推理成本...（中文摘要 4-6 句）
>
> 💡 **为什么值得读**: 对你的 AISA 成本优化项目直接相关...
> 🏷️ GPT-5, inference, cost-optimization

[更多文章...]

---

## 📊 数据概览

| 扫描源 | 抓取文章 | 时间范围 | 精选 |
|:---:|:---:|:---:|:---:|
| 82/90 blogs | 245 篇 → 156 篇(48h) → 去重 143 篇 | 48h | **15 篇** |

[Mermaid 饼图 + 关键词柱状图 + 标签云]

---

## 🤖 AI / ML
[按分类分组的文章列表，中文摘要...]

## ⚙️ 工程
[...]

---
*Bedrock: Haiku ×6 (评分) + Sonnet ×6 (摘要×2语言 + 趋势×2语言) = $0.063 → CloudWatch ✅*
```

### 6.3 英文版格式

结构与中文版完全相同，但：
- `lang: en` in frontmatter
- 标题: `# 🗞️ AI Daily Digest — 2026-03-15`
- 摘要和趋势总结用英文
- 原文标题不翻译
- 顶部链接: `中文版: [[2026-03-15]]`

---

## 7. CloudWatch Metrics 设计

每次 Bedrock 调用自动上报，这是本项目服务 W12 学习目标的核心。

### 7.1 Metric 结构

```python
Namespace = "BedrockCost"

Dimensions = [
    {"Name": "ModelId", "Value": "sonnet" | "haiku"},
    {"Name": "Caller", "Value": "ai-daily"},  # 区分来源
]

MetricData = [
    {"MetricName": "InputTokens",  "Value": input_tokens,  "Unit": "Count"},
    {"MetricName": "OutputTokens", "Value": output_tokens,  "Unit": "Count"},
    {"MetricName": "InferredCost", "Value": cost_usd,       "Unit": "None"},
]
```

### 7.2 metrics.py 接口

```python
import boto3
from datetime import datetime, timezone


def publish_metrics(
    model_id: str,        # "sonnet" | "haiku"
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    caller: str = "ai-daily",
) -> None:
    """发送一次 Bedrock 调用的 metrics 到 CloudWatch."""
    client = boto3.client("cloudwatch")
    client.put_metric_data(
        Namespace="BedrockCost",
        MetricData=[
            {
                "MetricName": name,
                "Dimensions": [
                    {"Name": "ModelId", "Value": model_id},
                    {"Name": "Caller", "Value": caller},
                ],
                "Timestamp": datetime.now(timezone.utc),
                "Value": value,
                "Unit": unit,
            }
            for name, value, unit in [
                ("InputTokens", input_tokens, "Count"),
                ("OutputTokens", output_tokens, "Count"),
                ("InferredCost", cost_usd, "None"),
            ]
        ],
    )
```

### 7.3 在 pipeline 中的集成点

每次调用 Bedrock 的函数都应包装为自动发 metrics：

```python
def call_bedrock_with_metrics(
    model: str,
    prompt: str,
    caller: str = "ai-daily",
) -> tuple[str, dict]:
    """调用 Bedrock 并自动推送 CloudWatch metrics。返回 (response_text, usage_dict)."""
    response = invoke_bedrock(model, prompt)
    cost = calculate_cost(model, response["input_tokens"], response["output_tokens"])
    publish_metrics(model, response["input_tokens"], response["output_tokens"], cost, caller)
    return response["text"], {"input_tokens": response["input_tokens"], "output_tokens": response["output_tokens"], "cost": cost}
```

---

## 8. CloudWatch Dashboard

### 8.1 Widgets

| Widget | 类型 | Metric | 说明 |
|--------|------|--------|------|
| 成本曲线 | Line | `InferredCost` by `ModelId` | Haiku vs Sonnet 成本趋势 |
| 当日累计成本 | Number | `InferredCost` Sum, 1 Day | 大数字显示 |
| Token 消耗 | Bar | `InputTokens` + `OutputTokens` by `ModelId` | 模型用量对比 |
| 调用来源 | Line | `InputTokens` Count by `Caller` | ai-daily vs benchmark |

### 8.2 创建方式

1. 先在 AWS Console 手动创建，确认效果
2. 导出 Dashboard JSON → `infra/dashboard.json`
3. 写脚本 `infra/create_dashboard.py` 一键重建

---

## 9. CloudWatch Alarm + SNS

### 9.1 SNS Topic

```
Topic Name: bedrock-cost-alert
Protocol: Email
Endpoint: <用户邮箱>
```

### 9.2 Alarm 配置

```
Alarm Name: bedrock-daily-cost-high
Namespace: BedrockCost
Metric: InferredCost
Statistic: Sum
Period: 86400 (1 day)
Threshold: > 10 (USD)
Comparison: GreaterThanThreshold
Action: SNS → bedrock-cost-alert
```

### 9.3 测试方法

把 threshold 临时设为 $0.001，跑一次 digest，确认收到邮件，改回 $10。

---

## 10. Cost Explorer API

独立脚本 `utils/cost_explorer.py`：

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

    return [
        {"date": item["TimePeriod"]["Start"], "cost": float(item["Total"]["UnblendedCost"]["Amount"])}
        for item in response["ResultsByTime"]
    ]
```

> ⚠️ Cost Explorer 数据有 24-48h 延迟。IAM 需要 `ce:GetCostAndUsage` 权限。

---

## 11. 运行方式

### 11.1 CLI

```bash
cd systems/s1-cost

# 默认：48h 内文章，Top 15，中英双语，输出到 Obsidian vault
python -m digest.main

# 自定义参数
python -m digest.main --hours 24 --top-n 10

# 只输出到终端（不写文件）
python -m digest.main --stdout

# 跳过 CloudWatch（离线调试）
python -m digest.main --no-metrics
```

### 11.2 CLI 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--hours` | 48 | 时间窗口 |
| `--top-n` | 15 | 精选文章数 |
| `--vault-path` | `~/Vaults/Workspace` | Obsidian vault 根路径 |
| `--stdout` | false | 只打印到终端，不写文件 |
| `--no-metrics` | false | 跳过 CloudWatch metrics |

输出固定为中英双语两个文件：
- `{vault-path}/Inbox/AI-Daily/YYYY-MM-DD.md`（中文）
- `{vault-path}/Inbox/AI-Daily/YYYY-MM-DD-en.md`（英文）

### 11.3 Obsidian 启动触发

**目标**: 每天早上打开 Obsidian 时自动运行 digest，打开 vault 就能看到今天的早报。

**方案**: 使用 Obsidian **Shell Commands** 插件（社区插件，免费）

配置步骤：
1. 安装 Shell Commands 插件（`obsidian-shellcommands`）
2. 添加一条 shell command：
   ```bash
   # 检查今天的早报是否已生成，避免重复运行
   [ -f "{{vault_path}}/Inbox/AI-Daily/$(date +%Y-%m-%d).md" ] || \
   cd /path/to/ai-sa-portfolio/systems/s1-cost && \
   python -m digest.main --vault-path "{{vault_path}}" &
   ```
3. 在插件设置中启用 "Events" → "Obsidian starts" 触发该命令
4. `&` 让脚本后台运行，不阻塞 Obsidian 启动

**工作流**：
```
早上打开 Obsidian
  → Shell Commands 插件检测到启动事件
  → 检查今天 Inbox/AI-Daily/2026-03-15.md 是否存在
  → 不存在 → 后台运行 digest（~30s-1min）
  → 完成后两个文件出现在 Inbox/AI-Daily/
  → 已存在 → 跳过，不重复运行
```

> **备选方案（如果不想装插件）**: macOS LaunchAgent，每天早上 7:00 定时运行：
> ```xml
> <!-- ~/Library/LaunchAgents/com.ai-daily-digest.plist -->
> <dict>
>   <key>Label</key><string>com.ai-daily-digest</string>
>   <key>ProgramArguments</key>
>   <array>
>     <string>/path/to/python</string>
>     <string>-m</string>
>     <string>digest.main</string>
>   </array>
>   <key>WorkingDirectory</key><string>/path/to/systems/s1-cost</string>
>   <key>StartCalendarInterval</key>
>   <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
> </dict>
> ```
> 这样早上打开 Obsidian 时文件已经在了。

### 11.4 IAM 权限

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "cloudwatch:PutMetricData",
    "ce:GetCostAndUsage"
  ],
  "Resource": "*"
}
```

---

## 12. 验收标准

### AI Daily Digest 功能

| # | 标准 | 通过条件 |
|---|------|---------|
| 1 | RSS 抓取 | 90 个源中 ≥70 个成功返回数据 |
| 2 | AI 评分 | 每篇有 3 维度分数 + 分类 + 关键词 |
| 3 | 中文版 | Top 15 篇都有中文标题 + 中文摘要 + 中文推荐理由 |
| 4 | 英文版 | Top 15 篇都有英文摘要 + 英文推荐理由 |
| 5 | 双文件 | `Inbox/AI-Daily/` 下生成 `YYYY-MM-DD.md` + `YYYY-MM-DD-en.md` |
| 6 | 去重 | 明显重复的标题被合并 |
| 7 | Obsidian 渲染 | frontmatter、callout、Mermaid 图表在 Obsidian 中正确显示 |
| 8 | 启动触发 | 打开 Obsidian 时自动运行（不重复） |

### CloudWatch 监控（AISA W12 核心目标）

| # | 标准 | 通过条件 |
|---|------|---------|
| 9 | Metrics 上报 | 每次 Bedrock 调用后 CloudWatch → BedrockCost 可见数据 |
| 10 | Dashboard | 显示成本曲线，能按 ModelId (haiku/sonnet) 维度筛选 |
| 11 | Alarm | 触发时收到邮件通知（低阈值测试） |
| 12 | Cost Explorer | 脚本能查询过去 7 天 Bedrock 成本趋势 |

---

## 13. 不做什么

- ❌ HN API / Reddit API — v1 只用 Karpathy 的 90 个 RSS 源，已经足够高质量
- ❌ 全文抓取所有文章 — 只对 Top N 且 description 过短的文章抓全文
- ❌ 数据库存储历史 — 每次跑都是独立的，不记历史
- ❌ Web UI — 纯 CLI + Obsidian Markdown
- ❌ Twitter/X API — 贵且不稳定
- ❌ 修改现有 `strategies/` 或 `benchmark/` 代码

---

## 14. 依赖

```
boto3           # 已有
aiohttp         # 异步 HTTP（RSS 并发抓取）
trafilatura     # 全文提取（可选，对 description 过短的文章抓全文）
```

不需要 `langchain`、`feedparser`、`beautifulsoup`。RSS 解析用 Python 标准库 `xml.etree.ElementTree`（参考 ai-daily-digest 的手写 parser 逻辑），保持轻量。

---

## 15. 实现优先级

给 Claude Code 的建议实现顺序：

| 顺序 | 模块 | 原因 |
|:----:|------|------|
| 1 | `utils/metrics.py` + `utils/config.py` 扩展 | 基础设施，所有 Bedrock 调用都依赖 |
| 2 | `utils/bedrock.py` 扩展（`converse` API + metrics 集成） | Bedrock 调用封装 |
| 3 | `digest/feeds.py` + `digest/sources/rss.py` | 数据源：移植 90 个 RSS 源 + 并发抓取 |
| 4 | `digest/dedup.py` | 去重 |
| 5 | `digest/scoring.py` | Haiku 评分（移植参考项目 prompt） |
| 6 | `digest/summarizer.py` | Sonnet 摘要 + 趋势总结（中英双语，各跑一次） |
| 7 | `digest/report.py` | Obsidian Markdown 生成（两个文件，互相 wikilink） |
| 8 | `digest/main.py` | Pipeline 编排 + CLI + 幂等检查（今天已跑过就跳过） |
| 9 | `infra/` | Dashboard JSON + Alarm + SNS 脚本 |
| 10 | `utils/cost_explorer.py` | Cost Explorer 查询 |

---

## 16. 双目标总结

本项目同时服务两个目标：

```
┌─────────────────────────────────────────────────────┐
│  AI Daily Digest                                     │
│  每天早上 → 抓取 90 个博客 → Bedrock 评分+总结       │
│  → 中英双语早报保存到 Obsidian                       │
│                                                      │
│  个人价值: 5 分钟掌握 AI/科技动态                     │
└──────────────────────┬──────────────────────────────┘
                       │ 每次 Bedrock 调用
                       │ 自动 put_metric_data
                       ▼
┌─────────────────────────────────────────────────────┐
│  CloudWatch 监控（AISA SYS-1 W7-8）                  │
│                                                      │
│  Custom Metrics ──→ Dashboard (成本曲线, 模型维度)    │
│       │                                              │
│       └──→ Alarm ($10/日) ──→ SNS ──→ 邮件通知       │
│                                                      │
│  学习价值: 真实数据 → 真实 Dashboard → 真实 Alarm     │
└─────────────────────────────────────────────────────┘
```

不是为了练习而造假数据，而是用一个你**每天真的会用**的工具来产生真实 Bedrock 流量。Dashboard 上的每一个数据点都是一篇真实文章的评分或摘要。
