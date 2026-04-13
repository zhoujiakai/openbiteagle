#!/usr/bin/env python3
"""从 Odaily 导入深度文章到知识库。

用法:
    python scripts/import_from_odaily.py [--limit 20] [--no-embed] [--real]
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """导入 Odaily 深度文章。"""
    import argparse

    from app.services.knowledge_loader import get_knowledge_loader

    parser = argparse.ArgumentParser(description="导入 Odaily 深度文章")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="最大导入文章数（默认: 20）",
    )
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="跳过生成向量嵌入",
    )
    parser.add_argument(
        "--real",
        action="store_true",
        help="从 Odaily 获取真实文章（默认: 使用模拟数据）",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Odaily 深度文章知识库导入")
    print("=" * 60)
    print(f"数量限制: {args.limit}")
    print(f"嵌入: {not args.no_embed}")
    print(f"真实数据: {args.real}")
    print()

    loader = get_knowledge_loader()

    stats = await loader.import_odaily_articles(
        limit=args.limit,
        embed=not args.no_embed,
        use_real=args.real,
    )

    print()
    print("=" * 60)
    print("导入结果")
    print("=" * 60)
    print(f"已获取:    {stats['fetched']}")
    print(f"已导入:   {stats['imported']}")
    print(f"已嵌入:   {stats['embedded']}")
    print(f"失败:     {stats['failed']}")

    if stats["errors"]:
        print()
        print("错误:")
        for error in stats["errors"][:5]:
            print(f"  - {error}")

    print()
    print("✅ 导入完成")


if __name__ == "__main__":
    asyncio.run(main())
