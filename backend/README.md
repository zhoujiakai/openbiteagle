# Biteagle Backend

FastAPI 后端服务，提供 Web3 数据分析和知识图谱功能。

## 开发环境设置

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 复制环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库等

# 运行开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 项目结构

```
app/
├── api/v1/           # API 路由
│   ├── health.py     # 健康检查
│   ├── news.py       # 新闻相关
│   ├── analysis.py   # 分析相关
│   └── kg.py         # 知识图谱
├── core/             # 核心配置
├── data/             # 数据层 (DB, Cache, Queue)
├── graph/            # LangGraph 工作流
│   └── news_analysis/
├── kg/               # Neo4j 知识图谱
│   ├── client.py     # Neo4j 客户端
│   ├── models.py     # 节点/关系定义
│   ├── loader.py     # 图数据导入
│   ├── query.py      # 图查询
│   └── importers.py  # Rootdata 导入器
├── models/           # 数据库模型
├── rag/              # 向量检索 (RAG)
├── schemas/          # Pydantic schemas
├── services/         # 业务逻辑
├── wrappers/         # 第三方服务封装
│   ├── llm/          # LLM 服务
│   ├── rootdata/     # Rootdata API
│   └── odaily/       # Odaily 抓取
└── main.py           # 应用入口
```

## 核心模块

### 知识图谱 (KG)

- **节点类型**: Project, Token, Person, Institution, Chain
- **关系类型**: ISSUED, INVESTED, BELONGS_TO, COLLABORATES_WITH, WORKS_AT, ADVISES, FOUNDED
- **API 端点**:
  - `POST /api/v1/kg/init` - 初始化图结构
  - `GET /api/v1/kg/stats` - 获取统计信息
  - `GET /api/v1/kg/projects/{name}` - 查询项目
  - `GET /api/v1/kg/projects/{name}/context` - 获取项目上下文
  - `GET /api/v1/kg/search` - 搜索节点

### RAG 检索

- 向量存储: PostgreSQL + pgvector
- 嵌入模型: OpenAI embeddings
- 检索链: LangChain

### LangGraph 分析

- 多节点新闻分析工作流
- 集成 RAG 和 KG 上下文

## 依赖服务

| 服务 | 连接字符串 |
|------|-----------|
| PostgreSQL | `postgresql://postgres:postgres@localhost:5433/biteagle` |
| Redis | `redis://localhost:6380` |
| RabbitMQ | `amqp://admin:admin@localhost:5672` |
| Neo4j | `bolt://neo4j:biteagle_password@localhost:7687` |
