# OpenBitEagle

AI 驱动的 Web3 投资分析系统，从 Odaily 快讯获取 Web3 行业新闻，通过多阶段 AI 分析流水线对每条快讯进行投资价值分析，判断是否具有投资价值，如果有价值则提取相关代币，并分析代币的涨跌趋势，给出买入/卖出建议。

## 目标指标

- 投资分析准确率 ≥ 90%
- 代币命中准确率 ≥ 90%

## 技术栈

- **后端**: Python 3.12+ / FastAPI / Pydantic
- **数据库**: PostgreSQL / SQLAlchemy / Redis / Neo4j
- **LLM**: LangChain / LangGraph / LangSmith
- **消息队列**: RabbitMQ

## 目录结构

```
backend/   # 后端服务
frontend/  # 前端界面
infra/     # 基础设施
```

## 许可证

MIT
