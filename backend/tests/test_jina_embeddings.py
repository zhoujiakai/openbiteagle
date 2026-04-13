#!/usr/bin/env python
"""测试 Jina Embeddings。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import cfg
from app.rag.embeddings import EmbeddingService


async def main():
    print(f"嵌入维度: {cfg.jina.JINA_EMBEDDING_DIM}")
    print()

    # 测试嵌入服务
    print("测试 Jina 嵌入服务...")
    service = EmbeddingService()

    test_text = "比特币是去中心化的数字货币"
    embedding = await service.embed_text(test_text)
    print(f"文本: {test_text}")
    print(f"维度: {len(embedding)}")
    print(f"前 5 个值: {embedding[:5]}")
    print()

    # 测试多条文本
    test_texts = [
        "ARB 代币有什么用？",
        "Arbitrum 是以太坊 Layer2 扩容方案",
    ]

    embeddings = await service.embed_texts(test_texts)
    print(f"生成了 {len(embeddings)} 个嵌入向量")

    # 测试相似度
    import numpy as np
    a = np.array(embeddings[0])
    b = np.array(embeddings[1])
    similarity = (a @ b) / (np.linalg.norm(a) * np.linalg.norm(b))
    print(f"相似度: {similarity:.4f}")
    print()

    print("✅ 嵌入服务测试通过！")
    await service.close()


if __name__ == "__main__":
    asyncio.run(main())
