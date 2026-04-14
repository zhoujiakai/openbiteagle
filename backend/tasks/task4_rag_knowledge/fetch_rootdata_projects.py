"""从 RootData API 批量导入项目数据到 RAG 知识库。

流程：
  1. 初始化 RootdataClient
  2. check_credits() 检查 API 余额
  3. get_project_list(limit) 通过搜索发现项目
  4. 逐个 get_project_detail() 获取详情
  5. 按 rootdata_id 去重（查 Document.meta_data JSON 字段）
  6. project.to_kb_document() → insert_document() 入库
  7. embedding_service.process_document() 分块向量化
  8. 统计 ok/duplicate/error
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select

from app.data.db import AsyncSessionLocal, Base, ensure_schema, engine
from app.data.logger import create_logger
from app.data.vector import insert_document
from app.models.document import Document, DocumentChunk  # noqa: F401
from app.rag.embeddings import get_embedding_service
from app.wrappers.rootdata import RootdataClient

logger = create_logger("task4_rootdata")

# 导入项目数量上限
LIMIT = 20


async def _find_by_rootdata_id(rootdata_id: str) -> int | None:
    """根据 rootdata_id 查找是否已存在该项目的文档。

    Returns:
        已存在的文档 ID，不存在则返回 None
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Document.id).where(
                Document.source_type == "rootdata",
                Document.meta_data["rootdata_id"].as_string() == rootdata_id,
            )
        )
        return result.scalar_one_or_none()


async def _process_project(client: RootdataClient, project_summary: dict) -> dict:
    """处理单个项目：获取详情 -> 去重 -> 入库 -> 分块向量化。

    Args:
        client: RootdataClient 实例
        project_summary: get_project_list 返回的项目摘要

    Returns:
        处理结果
    """
    pid = project_summary["id"]
    name = project_summary["name"]
    logger.info(f"处理: [{pid}] {name}")

    # 获取详情
    detail = await client.get_project_detail(pid, raw_data=project_summary.get("raw_data"))
    if detail is None:
        logger.warning(f"  {name} 获取详情失败，跳过")
        return {"project": name, "status": "error", "error": "detail fetch failed"}

    # 按 rootdata_id 去重
    existing_id = await _find_by_rootdata_id(detail.rootdata_id)
    if existing_id is not None:
        logger.info(f"  {name} 已存在（doc_id={existing_id}），跳过")
        return {"project": name, "status": "duplicate", "existing_id": existing_id}

    # 转为知识库文档格式并入库
    doc_data = detail.to_kb_document()
    doc_id = await insert_document(
        title=doc_data["title"],
        content=doc_data["content"],
        source_url=doc_data.get("source_url"),
        source_type=doc_data["source_type"],
        metadata=doc_data["metadata"],
    )
    logger.info(f"  {name} 已入库 doc_id={doc_id}")

    # 分块向量化
    embedding_service = get_embedding_service()
    result = await embedding_service.process_document(doc_id)
    logger.info(
        f"  {name} 分块完成: {result['chunks_created']} 个分块, "
        f"向量维度={result['embedding_dim']}"
    )
    return {"project": name, "status": "ok", "doc_id": doc_id, **result}


async def main():
    # 建表
    await ensure_schema()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with RootdataClient() as client:
        # 检查 API 余额
        try:
            credits_info = await client.check_credits()
            remaining = credits_info.get("credits", "N/A")
            total = credits_info.get("total_credits", "N/A")
            logger.info(f"API 余额: {remaining}/{total} credits")
        except Exception as e:
            logger.warning(f"无法查询余额: {e}")

        # 发现项目
        projects = await client.get_project_list(limit=LIMIT)
        if not projects:
            logger.info("未发现任何项目")
            await engine.dispose()
            return

        logger.info(f"发现 {len(projects)} 个项目，开始处理")

        stats = {"ok": 0, "duplicate": 0, "error": 0}
        total_chunks = 0

        for i, project in enumerate(projects):
            try:
                result = await _process_project(client, project)
                status = result["status"]
                stats[status] += 1
                if status == "ok":
                    total_chunks += result.get("chunks_created", 0)
            except Exception as e:
                logger.error(f"  {project['name']} 处理失败: {e}")
                stats["error"] += 1

    # 关闭嵌入服务 HTTP 客户端
    embedding_service = get_embedding_service()
    await embedding_service.close()

    logger.info(
        f"完成：新增 {stats['ok']} 篇，重复跳过 {stats['duplicate']} 篇，"
        f"失败 {stats['error']} 篇，共生成 {total_chunks} 个分块"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
