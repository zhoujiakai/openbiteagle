#!/usr/bin/env python3
"""Test RAG knowledge base retrieval."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.chain import get_rag_chain


async def main():
    """Test RAG retrieval."""
    print("=" * 60)
    print("Testing RAG Knowledge Base")
    print("=" * 60)
    print()

    rag = get_rag_chain(top_k=3, threshold=0.0)  # Low threshold for testing

    # Test 1: Token query
    print("Test 1: Query about Bitcoin")
    print("-" * 60)
    result = await rag.query("What is Bitcoin?")
    print(f"Answer: {result['answer']}")
    print(f"Sources: {len(result['sources'])} chunks")
    print()

    # Test 2: Token-specific retrieval
    print("Test 2: Token-filtered query about Ethereum")
    print("-" * 60)
    result = await rag.query("What are the key features?", filter_tokens=["ETH", "Ethereum"])
    print(f"Answer: {result['answer']}")
    print(f"Sources: {len(result['sources'])} chunks")
    print()

    # Test 3: Enhance token context
    print("Test 3: Enhance token context with news")
    print("-" * 60)
    result = await rag.enhance_token_context(
        token="SOL",
        news_content="Solana just announced a new partnership with a major payment provider."
    )
    print(f"Token: {result['token']}")
    print(f"KB Found: {result['kb_found']}")
    print(f"Chunks: {result.get('kb_chunks', 0)}")
    print(f"Analysis: {result.get('analysis', 'N/A')[:200]}...")
    print()

    print("=" * 60)
    print("✅ RAG tests completed")


if __name__ == "__main__":
    asyncio.run(main())
