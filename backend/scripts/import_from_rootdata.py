#!/usr/bin/env python3
"""从 Rootdata 导入项目到知识库。

用法:
    python scripts/import_from_rootdata.py [--limit 20] [--no-embed] [--kg]
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """导入 Rootdata 项目。"""
    import argparse

    from app.services.knowledge_loader import get_knowledge_loader

    parser = argparse.ArgumentParser(description="导入 Rootdata 项目")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="最大导入项目数（默认: 20）",
    )
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="跳过生成向量嵌入",
    )
    parser.add_argument(
        "--kg",
        "--import-to-kg",
        action="store_true",
        dest="import_to_kg",
        help="同时导入到 Neo4j 知识图谱",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Rootdata 知识库导入")
    print("=" * 60)
    print(f"数量限制: {args.limit}")
    print(f"嵌入: {not args.no_embed}")
    print(f"导入到知识图谱: {args.import_to_kg}")
    print()

    loader = get_knowledge_loader()

    stats = await loader.import_rootdata_projects(
        limit=args.limit,
        embed=not args.no_embed,
        import_to_kg=args.import_to_kg,
    )

    print()
    print("=" * 60)
    print("导入结果")
    print("=" * 60)
    print(f"已获取:    {stats['fetched']}")
    print(f"已导入:   {stats['imported']}")
    print(f"已嵌入:   {stats['embedded']}")
    print(f"失败:     {stats['failed']}")

    if stats.get("kg_stats"):
        kg = stats["kg_stats"]
        print()
        print("知识图谱:")
        print(f"  成功:   {kg['success']}")
        print(f"  失败:    {kg['failed']}")
        print(f"  节点:     {kg['nodes_created']}")
        print(f"  关系: {kg['relationships_created']}")

    if stats["errors"]:
        print()
        print("错误:")
        for error in stats["errors"][:5]:  # 显示前 5 个错误
            print(f"  - {error}")
        if len(stats["errors"]) > 5:
            print(f"  ... 还有 {len(stats['errors']) - 5} 个")

    print()
    print("✅ 导入完成")


if __name__ == "__main__":
    asyncio.run(main())
