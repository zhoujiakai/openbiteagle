# Task 4: RAG Knowledge Base

构建 RAG（检索增强生成）知识库，将多来源数据导入 PostgreSQL + pgvector 向量数据库。

## 数据流

```
数据源 → 脚本 → Document 表 → 分块 + Jina Embeddings → DocumentChunk 表
                                                       (pgvector 向量索引)
```

## 脚本说明

| 脚本 | 数据源 | 说明 |
|------|--------|------|
| `fetch_rootdata_projects.py` | RootData API | 通过 REST API 批量导入 Web3 项目信息 |
| `import_whitepapers.py` | `docs/whitepaper/*.pdf` | 导入白皮书 PDF，LLM 识别项目后去重入库 |
| `chunk_and_embed.py` | Document 表 | 对未生成嵌入的文档进行分块向量化 |

## 配置要求

### RootData API（`fetch_rootdata_projects.py`）

在 `config.yaml` 中配置：

```yaml
rootdata:
    ROOTDATA_API_KEY: your-rootdata-api-key
    ROOTDATA_BASE_URL: https://api.rootdata.com/open
    ROOTDATA_LANGUAGE: en
    ROOTDATA_TIMEOUT: 15.0
```

API Key 需要在 [RootData](https://cn.rootdata.com/Api/Doc) 申请。主要消耗：
- `ser_inv`（搜索）：免费，不限次数
- `get_item`（详情）：2 credits/次
- `quotacredits`（余额查询）：免费

### Jina Embeddings（所有脚本共用）

```yaml
jina:
    JINA_API_KEY: your-jina-api-key
    JINA_EMBEDDING_MODEL: jina-embeddings-v3
```

### Embedding 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CHUNK_SIZE` | 500 | 文本分块大小（字符数） |
| `CHUNK_OVERLAP` | 100 | 相邻分块重叠字符数 |
| `JINA_EMBEDDING_DIM` | 1024 | 向量维度 |
| `JINA_BATCH_SIZE` | 8 | 每次 API 请求的批量大小 |

## 运行方式

```bash
cd backend

# 导入 RootData 项目
python tasks/task4_rag_knowledge/fetch_rootdata_projects.py

# 导入白皮书
python tasks/task4_rag_knowledge/import_whitepapers.py

# 对未嵌入的文档进行分块向量化
python tasks/task4_rag_knowledge/chunk_and_embed.py
```

## 去重策略

- **RootData 项目**：按 `Document.meta_data.rootdata_id` 去重
- **白皮书**：按 `Document.meta_data.project`（LLM 识别的项目名）去重
