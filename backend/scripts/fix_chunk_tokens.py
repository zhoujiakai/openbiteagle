#!/usr/bin/env python3
"""修复现有 DocumentChunk 的 tokens 字段。

对每个文档，调用 LLM 提取代币符号，然后批量更新该文档下所有 chunks。
1 个文档 = 1 次 LLM 调用。

用法：
  python scripts/fix_chunk_tokens.py          # 预览模式，只显示将做的修改
  python scripts/fix_chunk_tokens.py --apply   # 实际写入数据库
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update

from app.data.db import AsyncSessionLocal
from app.models.document import Document, DocumentChunk
from app.rag.embeddings import extract_tokens_from_text


async def build_doc_tokens_map() -> dict[int, list[str]]:
    """为每个文档调用 LLM 提取 tokens（1 个文档 1 次 LLM 调用）。

    优先使用 metadata["tokens"]，否则用 LLM 从标题+内容提取。
    """
    doc_tokens: dict[int, list[str]] = {}

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document))
        docs = result.scalars().all()

        for doc in docs:
            tokens = (doc.meta_data or {}).get("tokens", [])
            if not tokens:
                text = f"{doc.title} {doc.content[:2000]}"
                print(f"   🤖 LLM 提取代币: 文档 {doc.id} ({doc.title})")
                tokens = await extract_tokens_from_text(text)
            doc_tokens[doc.id] = tokens

    return doc_tokens


async def fix_chunk_tokens(apply: bool = False):
    """扫描并修复所有 chunk 的 tokens。"""
    print("=" * 60)
    print("修复 DocumentChunk tokens 字段")
    print(f"模式: {'写入' if apply else '预览（加 --apply 实际写入）'}")
    print("=" * 60)
    print()

    # 1. 构建文档 → tokens 映射（按文档调用 LLM）
    print("正在扫描文档并提取代币...")
    doc_tokens = await build_doc_tokens_map()
    print(f"   共 {len(doc_tokens)} 篇文档")
    print()

    # 2. 遍历所有 chunk
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DocumentChunk).order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
        )
        chunks = result.scalars().all()

        print(f"共 {len(chunks)} 个分块")
        print()

        to_update = []
        empty_count = 0

        for chunk in chunks:
            # 文档级 tokens 直接继承
            new_tokens = doc_tokens.get(chunk.document_id, [])
            old_tokens = list(chunk.tokens) if chunk.tokens else []

            if new_tokens != old_tokens:
                to_update.append((chunk.id, old_tokens, new_tokens))
                if not old_tokens:
                    empty_count += 1

        # 3. 汇总统计
        print(f"需要修复: {len(to_update)} 个分块（其中 {empty_count} 个 tokens 为空）")

        if not to_update:
            print()
            print("所有分块 tokens 已正确，无需修复。")
            return

        # 按文档分组显示
        current_doc_id = None
        for chunk_id, old, new in to_update[:30]:
            for chunk in chunks:
                if chunk.id == chunk_id:
                    if chunk.document_id != current_doc_id:
                        current_doc_id = chunk.document_id
                        doc_tok = doc_tokens.get(current_doc_id, [])
                        print(f"\n   文档 {current_doc_id} (tokens: {doc_tok})")
                    break
            old_str = ", ".join(old) if old else "(empty)"
            new_str = ", ".join(new) if new else "(empty)"
            print(f"     chunk {chunk_id}: [{old_str}] -> [{new_str}]")

        if len(to_update) > 30:
            print(f"\n   ... 还有 {len(to_update) - 30} 个分块未显示")

        if not apply:
            print()
            print("这是预览模式。运行 'python scripts/fix_chunk_tokens.py --apply' 实际写入。")
            return

        # 4. 批量更新
        print()
        print("正在写入数据库...")

        updated = 0
        for chunk_id, old, new in to_update:
            await db.execute(
                update(DocumentChunk)
                .where(DocumentChunk.id == chunk_id)
                .values(tokens=new)
            )
            updated += 1
            if updated % 100 == 0:
                print(f"   已更新 {updated}/{len(to_update)}...")

        await db.commit()

        print()
        print("=" * 60)
        print(f"已修复 {updated} 个分块的 tokens 字段")
        print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="修复 DocumentChunk 的 tokens 字段")
    parser.add_argument("--apply", action="store_true", help="实际写入数据库（默认为预览模式）")
    args = parser.parse_args()

    asyncio.run(fix_chunk_tokens(apply=args.apply))
