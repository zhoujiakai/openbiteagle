#!/usr/bin/env python3
"""从 docs/rag.yaml 导入文档到 RAG 知识库，并生成向量嵌入。

用法：
  python scripts/import_rag_yaml.py           # 增量导入（跳过已存在的文档）
  python scripts/import_rag_yaml.py --force    # 强制重新导入（删除旧数据后重新导入）
"""

import argparse
import asyncio
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.db import AsyncSessionLocal
from app.data.vector import get_all_documents, insert_document
from app.rag.embeddings import get_embedding_service


def load_rag_yaml(yaml_path: str) -> list[dict]:
    """读取 rag.yaml 文件，返回文档列表。"""
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("documents", [])


async def delete_existing_docs():
    """删除 rag.yaml 导入的所有文档及其分块（按标题匹配）。"""
    from sqlalchemy import delete as sql_delete

    from app.models.document import Document, DocumentChunk

    yaml_path = Path(__file__).parent.parent.parent / "docs" / "rag.yaml"
    docs_data = load_rag_yaml(str(yaml_path))
    titles = [d["title"] for d in docs_data]

    async with AsyncSessionLocal() as db:
        # 先找出要删除的文档 ID
        from sqlalchemy import select

        result = await db.execute(
            select(Document.id).where(Document.title.in_(titles))
        )
        doc_ids = [row[0] for row in result.all()]

        if not doc_ids:
            print("   没有需要删除的旧数据")
            return

        # 删除对应的分块
        await db.execute(
            sql_delete(DocumentChunk).where(DocumentChunk.document_id.in_(doc_ids))
        )
        # 删除文档
        await db.execute(
            sql_delete(Document).where(Document.id.in_(doc_ids))
        )
        await db.commit()
        print(f"   已删除 {len(doc_ids)} 篇旧文档及其分块")


async def main():
    """导入 rag.yaml 中的文档并生成嵌入向量。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="强制重新导入（删除旧数据）")
    args = parser.parse_args()

    yaml_path = Path(__file__).parent.parent.parent / "docs" / "rag.yaml"

    if not yaml_path.exists():
        print(f"❌ 文件不存在: {yaml_path}")
        return

    print("=" * 60)
    print("从 rag.yaml 导入文档到 RAG 知识库")
    print("=" * 60)
    print()

    docs = load_rag_yaml(str(yaml_path))
    if not docs:
        print("❌ rag.yaml 中没有找到文档数据")
        return

    print(f"📋 共找到 {len(docs)} 篇文档")
    print()

    # --force 模式：先删除旧数据
    if args.force:
        print("🗑  强制模式：正在删除旧数据...")
        await delete_existing_docs()
        print()

    # 第一阶段：插入文档
    inserted_ids = []
    skipped = 0

    existing_docs = await get_all_documents(limit=500)
    existing_titles = {doc.title for doc in existing_docs}

    for i, doc in enumerate(docs, 1):
        title = doc["title"]
        print(f"{i}. {title}")

        if title in existing_titles:
            print(f"   ⏭  已存在，跳过")
            skipped += 1
            continue

        doc_id = await insert_document(
            title=title,
            content=doc["content"],
            source_url=doc.get("source_url"),
            source_type=doc.get("source_type", "manual"),
            metadata=doc.get("metadata", {}),
        )
        inserted_ids.append(doc_id)
        print(f"   ✅ 已插入，文档 ID: {doc_id}")

    print()
    print(f"📊 插入: {len(inserted_ids)} 篇，跳过: {skipped} 篇")

    if not inserted_ids:
        print()
        print("没有新文档需要处理。如需重新导入，请使用 --force 参数。")
        return

    # 第二阶段：生成向量嵌入
    print()
    print("=" * 60)
    print("正在生成向量嵌入...")
    print("=" * 60)
    print()

    embedding_service = get_embedding_service()
    total_chunks = 0

    for doc_id in inserted_ids:
        try:
            result = await embedding_service.process_document(
                document_id=doc_id,
                chunk_size=500,
                chunk_overlap=100,
            )
            total_chunks += result["chunks_created"]
            print(f"   文档 {doc_id}: {result['chunks_created']} 个分块，维度 {result['embedding_dim']}")
        except Exception as e:
            print(f"   ❌ 文档 {doc_id} 嵌入失败: {e}")

    await embedding_service.close()

    print()
    print("=" * 60)
    print(f"✅ 导入完成: {len(inserted_ids)} 篇文档，共 {total_chunks} 个分块")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
