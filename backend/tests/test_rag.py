#!/usr/bin/env python3
"""测试 RAG 知识库检索。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.chain import get_rag_chain


async def main():
    """测试 RAG 检索功能。"""
    print("=" * 60)
    print("测试 RAG 知识库")
    print("=" * 60)
    print()

    rag = get_rag_chain(top_k=3, threshold=0.0)  # 使用低阈值以便测试

    # 测试 1：代币查询
    print("测试 1：查询比特币相关信息")
    print("-" * 60)
    result = await rag.query("比特币是什么？")
    print(f"回答：{result['answer']}")
    print(f"来源：{len(result['sources'])} 个分块")
    print()

    # 测试 2：按代币过滤查询
    print("测试 2：按代币过滤查询以太坊")
    print("-" * 60)
    result = await rag.query("有哪些关键特性？", filter_tokens=["ETH", "Ethereum"])
    print(f"回答：{result['answer']}")
    print(f"来源：{len(result['sources'])} 个分块")
    print()

    # 测试 3：增强代币上下文
    print("测试 3：结合新闻增强代币上下文")
    print("-" * 60)
    result = await rag.enhance_token_context(
        token="SOL",
        news_content="Solana 刚刚宣布与一家主要支付提供商达成新的合作关系。"
    )
    print(f"代币：{result['token']}")
    print(f"知识库匹配：{result['kb_found']}")
    print(f"匹配分块数：{result.get('kb_chunks', 0)}")
    print(f"分析结果：{result.get('analysis', 'N/A')[:200]}...")
    print()

    print("=" * 60)
    print("✅ RAG 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
