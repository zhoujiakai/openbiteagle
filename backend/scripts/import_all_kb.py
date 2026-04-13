#!/usr/bin/env python3
"""从所有来源导入文档到知识库。

用法:
    python scripts/import_all_kb.py [--rootdata 20] [--odaily 20] [--tokenomics 20] [--no-embed]
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """从所有来源导入。"""
    import argparse

    from app.services.knowledge_loader import get_knowledge_loader

    parser = argparse.ArgumentParser(description="从所有知识库来源导入")
    parser.add_argument(
        "--rootdata",
        type=int,
        default=20,
        metavar="N",
        help="导入 Rootdata 项目数量（默认: 20）",
    )
    parser.add_argument(
        "--odaily",
        type=int,
        default=20,
        metavar="N",
        help="导入 Odaily 文章数量（默认: 20）",
    )
    parser.add_argument(
        "--tokenomics",
        type=int,
        default=20,
        metavar="N",
        help="导入代币经济学文档数量（默认: 20）",
    )
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="跳过生成向量嵌入",
    )
    parser.add_argument(
        "--skip-rootdata",
        action="store_true",
        help="跳过 Rootdata 导入",
    )
    parser.add_argument(
        "--skip-odaily",
        action="store_true",
        help="跳过 Odaily 导入",
    )
    parser.add_argument(
        "--skip-tokenomics",
        action="store_true",
        help="跳过代币经济学导入",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("知识库 - 从所有来源导入")
    print("=" * 60)
    print(f"Rootdata:   {args.rootdata if not args.skip_rootdata else '(已跳过)'}")
    print(f"Odaily:     {args.odaily if not args.skip_odaily else '(已跳过)'}")
    print(f"代币经济学: {args.tokenomics if not args.skip_tokenomics else '(已跳过)'}")
    print(f"嵌入:       {not args.no_embed}")
    print()

    loader = get_knowledge_loader()
    embed = not args.no_embed

    total_stats = {
        "fetched": 0,
        "imported": 0,
        "embedded": 0,
        "failed": 0,
        "errors": [],
    }

    # 从 Rootdata 导入
    if not args.skip_rootdata:
        print("-" * 60)
        print("正在从 Rootdata 导入...")
        print("-" * 60)
        stats = await loader.import_rootdata_projects(
            limit=args.rootdata,
            embed=embed,
        )
        for key in total_stats:
            if key != "errors":
                total_stats[key] += stats.get(key, 0)
        total_stats["errors"].extend(stats.get("errors", []))
        print()

    # 从 Odaily 导入
    if not args.skip_odaily:
        print("-" * 60)
        print("正在从 Odaily 导入...")
        print("-" * 60)
        stats = await loader.import_odaily_articles(
            limit=args.odaily,
            embed=embed,
        )
        for key in total_stats:
            if key != "errors":
                total_stats[key] += stats.get(key, 0)
        total_stats["errors"].extend(stats.get("errors", []))
        print()

    # 导入代币经济学
    if not args.skip_tokenomics:
        print("-" * 60)
        print("正在导入代币经济学文档...")
        print("-" * 60)
        stats = await loader.import_tokenomics_docs(
            limit=args.tokenomics,
            embed=embed,
        )
        for key in total_stats:
            if key != "errors":
                total_stats[key] += stats.get(key, 0)
        total_stats["errors"].extend(stats.get("errors", []))
        print()

    # 打印汇总
    print()
    print("=" * 60)
    print("总导入结果")
    print("=" * 60)
    print(f"已获取:    {total_stats['fetched']}")
    print(f"已导入:   {total_stats['imported']}")
    print(f"已嵌入:   {total_stats['embedded']}")
    print(f"失败:     {total_stats['failed']}")

    if total_stats["errors"]:
        print()
        print("错误:")
        for error in total_stats["errors"][:10]:
            print(f"  - {error}")
        if len(total_stats["errors"]) > 10:
            print(f"  ... 还有 {len(total_stats['errors']) - 10} 个")

    print()
    print("✅ 所有导入已完成")


if __name__ == "__main__":
    asyncio.run(main())
