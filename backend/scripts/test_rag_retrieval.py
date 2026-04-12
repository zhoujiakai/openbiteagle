#!/usr/bin/env python
"""Test RAG retrieval with real embeddings."""

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
        print(f"Query: {query}")
        print('='*60)

        results = await retriever.search(query)

        if not results:
            print("No results found")
            continue

        for i, r in enumerate(results, 1):
            print(f"\n[{i}] Similarity: {r['similarity']:.4f}")
            print(f"    Content: {r['content'][:150]}...")


if __name__ == "__main__":
    asyncio.run(main())
