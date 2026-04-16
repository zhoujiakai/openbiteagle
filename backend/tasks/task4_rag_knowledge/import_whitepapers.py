"""将 docs/whitepaper 目录下的白皮书 PDF 导入数据库并分块向量化。

流程：
  1. 扫描 docs/whitepaper 目录下的所有 PDF 文件
  2. 提取 PDF 文本内容
  3. 调用 LLM 根据内容识别白皮书所属项目名
  4. 按项目名去重：如果数据库中已存在该项目的白皮书（即使文件名不同），则跳过
  5. 将白皮书存入 Document 表（source_type=whitepaper）
  6. 分块并向量化存入 DocumentChunk 表
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage
from sqlalchemy import select

from app.data.db import AsyncSessionLocal, Base, ensure_schema, engine
from app.data.logger import create_logger
from app.data.vector import insert_document
from app.models.document import Document, DocumentChunk  # noqa: F401
from app.rag.embeddings import get_embedding_service
from app.wrappers.llm.client import get_llm

logger = create_logger("task4_whitepaper")

# 白皮书目录（相对于项目根目录）
WHITEPAPER_DIR = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "whitepaper"


def _extract_pdf_text(pdf_path: Path) -> str:
    """从 PDF 文件中提取全部文本内容。"""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


async def _identify_project(content: str) -> str:
    """调用 LLM 根据白皮书内容识别所属项目名。

    取前 2000 字符送入 LLM，避免 token 过多。

    Returns:
        项目名（小写英文，如 bitcoin、ethereum）
    """
    llm = get_llm(temperature=0)
    excerpt = content[:2000]
    prompt = (
        "请根据以下白皮书内容片段，判断这篇白皮书属于哪个区块链/加密货币项目。\n"
        "只回复项目名称的英文小写形式（如 bitcoin、ethereum、sui 等），"
        "不要回复任何其他内容。\n\n"
        f"---\n{excerpt}\n---"
    )
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    project = response.content.strip().lower()
    # 清理可能的多余输出
    project = project.split("\n")[0].strip()
    return project


async def _find_by_project(project: str) -> int | None:
    """根据项目名查找是否已存在该项目的白皮书。

    Returns:
        已存在的文档 ID，不存在则返回 None
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Document.id).where(
                Document.source_type == "whitepaper",
                Document.meta_data["project"].as_string() == project,
            )
        )
        return result.scalar_one_or_none()


async def _process_whitepaper(pdf_path: Path) -> dict:
    """处理单个白皮书：提取文本 -> LLM识别项目 -> 去重 -> 入库 -> 分块向量化。

    Returns:
        处理结果
    """
    filename = pdf_path.name
    logger.info(f"处理: {filename}")

    # 提取文本
    content = _extract_pdf_text(pdf_path)
    if not content:
        logger.warning(f"  {filename} 无法提取文本，跳过")
        return {"file": filename, "status": "empty"}

    # LLM 识别项目名
    project = await _identify_project(content)
    logger.info(f"  LLM 识别项目: {project}")

    # 按项目名去重
    existing_id = await _find_by_project(project)
    if existing_id is not None:
        logger.info(f"  {project} 白皮书已存在（doc_id={existing_id}），跳过")
        return {"file": filename, "status": "duplicate", "existing_id": existing_id}

    # 存入 Document 表
    # 不设 tokens，让 process_document 通过 LLM 从内容中提取
    doc_id = await insert_document(
        title=pdf_path.stem,
        content=content,
        source_url=None,
        source_type="whitepaper",
        metadata={"project": project, "filename": filename},
    )
    logger.info(f"  {filename}（{project}）已入库 doc_id={doc_id}")

    # 分块向量化
    embedding_service = get_embedding_service()
    result = await embedding_service.process_document(doc_id)
    logger.info(
        f"  {filename} 分块完成: {result['chunks_created']} 个分块, "
        f"向量维度={result['embedding_dim']}"
    )
    return {"file": filename, "status": "ok", "doc_id": doc_id, "project": project, **result}


async def main():
    # 建表
    await ensure_schema()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 扫描白皮书目录
    if not WHITEPAPER_DIR.exists():
        logger.error(f"白皮书目录不存在: {WHITEPAPER_DIR}")
        await engine.dispose()
        return

    pdf_files = sorted(WHITEPAPER_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.info(f"未找到 PDF 文件: {WHITEPAPER_DIR}")
        await engine.dispose()
        return

    logger.info(f"发现 {len(pdf_files)} 个白皮书文件")

    stats = {"ok": 0, "duplicate": 0, "empty": 0, "error": 0}
    total_chunks = 0

    for pdf_path in pdf_files:
        try:
            result = await _process_whitepaper(pdf_path)
            status = result["status"]
            stats[status] += 1
            if status == "ok":
                total_chunks += result.get("chunks_created", 0)
        except Exception as e:
            logger.error(f"  {pdf_path.name} 处理失败: {e}")
            stats["error"] += 1

    # 关闭嵌入服务 HTTP 客户端
    embedding_service = get_embedding_service()
    await embedding_service.close()

    logger.info(
        f"完成：新增 {stats['ok']} 篇，重复跳过 {stats['duplicate']} 篇，"
        f"空内容 {stats['empty']} 篇，失败 {stats['error']} 篇，"
        f"共生成 {total_chunks} 个分块"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
