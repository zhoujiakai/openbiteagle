#!/usr/bin/env python
"""测试 RAG 检索（使用真实嵌入）。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.retriever import get_retriever


async def main():
    retriever = get_retriever(top_k=3, threshold=0.5)

    queries = [
        "ARB 代币有什么用？",
        "比特币去中心化",
        "Layer2 扩容方案",
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"查询: {query}")
        print('='*60)

        results = await retriever.search(query)

        if not results:
            print("未找到结果")
            continue

        for i, r in enumerate(results, 1):
            print(f"\n[{i}] 相似度: {r['similarity']:.4f}")
            print(f"    内容: {r['content'][:150]}...")


if __name__ == "__main__":
    asyncio.run(main())
