#!/usr/bin/env python3
"""将 Rootdata 项目导入 Neo4j 知识图谱。

用法:
    python scripts/import_rootdata_to_kg.py --limit 50

该脚本从 Rootdata 获取项目，并将其导入 Neo4j 知识图谱，
创建相应的节点和关系。
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """主导入函数。"""
    import argparse

    from app.kg.client import Neo4jClient
    from app.kg.importers import RootdataKGImporter
    from app.kg.loader import GraphLoader
    from app.kg.query import GraphQuery
    from app.wrappers.rootdata import scrape_rootdata_projects

    parser = argparse.ArgumentParser(
        description="将 Rootdata 项目导入 Neo4j 知识图谱"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="最大导入项目数（默认: 20）",
    )
    parser.add_argument(
        "--headless",
        type=bool,
        default=True,
        help="以无头模式运行浏览器（默认: True）",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="跳过知识图谱中已存在的项目",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_false",
        dest="skip_existing",
        help="不跳过已存在的项目（更新它们）",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="仅显示图谱统计信息，不导入",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Rootdata → Neo4j 知识图谱导入")
    print("=" * 60)
    print(f"数量限制: {args.limit}")
    print(f"跳过已有: {args.skip_existing}")
    print()

    # 连接到 Neo4j
    print("正在连接到 Neo4j...")
    client = Neo4jClient()
    await client.connect()
    print("   ✅ 已连接到 Neo4j")

    try:
        loader = GraphLoader(client)
        query_service = GraphQuery(client)

        # 初始化约束
        print("\n正在初始化图谱约束...")
        await loader.create_constraints()
        print("   ✅ 约束就绪")

        # 显示当前统计
        print("\n📊 当前图谱统计:")
        stats_before = await query_service.get_graph_stats()
        for key, value in stats_before.items():
            print(f"   - {key}: {value}")

        if args.stats_only:
            print("\n--stats-only 模式，退出--")
            return

        # 从 Rootdata 获取项目
        print(f"\n正在从 Rootdata 获取 {args.limit} 个项目...")
        print("(使用 Playwright，可能需要一些时间...)")
        projects = await scrape_rootdata_projects(limit=args.limit)
        print(f"   ✅ 已获取 {len(projects)} 个项目")

        if not projects:
            print("未获取到项目，退出。")
            return

        # 显示示例项目信息
        print("\n📦 示例项目:")
        sample = projects[0]
        print(f"   名称: {sample.name}")
        print(f"   代币: {sample.token.symbol if sample.token else 'None'}")
        print(f"   链: {', '.join(sample.chains) if sample.chains else 'None'}")
        print(f"   投资方: {len(sample.investors)}")

        # 导入到知识图谱
        print(f"\n正在将 {len(projects)} 个项目导入 Neo4j 知识图谱...")
        print("-" * 60)

        importer = RootdataKGImporter(loader)
        result = await importer.import_batch(
            projects,
            skip_existing=args.skip_existing,
        )

        print("-" * 60)
        print("\n" + "=" * 60)
        print("导入结果")
        print("=" * 60)
        print(f"总项目数:   {result['total']}")
        print(f"✅ 成功:       {result['success']}")
        print(f"❌ 失败:        {result['failed']}")
        print(f"⏭️  跳过:       {result['skipped']}")
        print(f"\n创建的节点:     {result['nodes_created']}")
        print(f"创建的关系:      {result['relationships_created']}")

        if result["errors"]:
            print(f"\n错误 ({len(result['errors'])}):")
            for error in result["errors"][:5]:
                print(f"   - {error['project']}: {error['error']}")
            if len(result["errors"]) > 5:
                print(f"   ... 还有 {len(result['errors']) - 5} 个")

        # 显示更新后的统计
        print("\n📊 更新后的图谱统计:")
        stats_after = await query_service.get_graph_stats()
        for key, value in stats_after.items():
            before = stats_before.get(key, 0)
            delta = value - before
            delta_str = f" (+{delta})" if delta > 0 else ""
            print(f"   - {key}: {value}{delta_str}")

        print("\n✅ 导入完成!")

        # 测试查询
        if result["success"] > 0:
            print("\n🔍 正在测试已导入项目的查询...")
            first_project = projects[0]
            context = await query_service.get_project_context(first_project.name)
            if context.get("project"):
                print(f"   项目: {context['project'].get('name')}")
                print(f"   代币: {len(context.get('tokens', []))}")
                chain = context.get('chain')
                print(f"   链: {chain.get('name', 'N/A') if chain else 'N/A'}")
                print(f"   投资方: {len(context.get('investors', []))}")

    finally:
        await client.close()
        print("\n✅ 连接已关闭")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户取消了导入")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
