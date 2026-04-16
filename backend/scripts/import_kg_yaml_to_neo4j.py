#!/usr/bin/env python3
"""将 docs/kg.yaml 中的团队和投融资信息导入 Neo4j 知识图谱。

用法:
    python scripts/import_kg_yaml_to_neo4j.py

该脚本读取 docs/kg.yaml，解析其中的项目、团队和投融资数据，
通过 GraphLoader 写入 Neo4j。
"""

import asyncio
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

# docs/kg.yaml 相对于 backend 目录的路径
YAML_PATH = Path(__file__).parent.parent.parent / "docs" / "kg.yaml"


def load_yaml(path: Path) -> dict:
    """加载 YAML 文件。"""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def determine_relation_type(role: str):
    """根据角色描述判断关系类型。"""
    from app.kg.models import RelationTypes

    if "创始人" in role:
        return RelationTypes.FOUNDED
    return RelationTypes.WORKS_AT


def collect_all_investors(entry: dict) -> list[str]:
    """从投资记录中收集所有投资方（含领投和参投）。"""
    names: list[str] = []
    names.extend(entry.get("lead_investors", []))
    names.extend(entry.get("participants", []))
    names.extend(entry.get("investors", []))
    return names


async def import_project(loader, project_data: dict) -> dict:
    """导入单个项目的所有数据到 Neo4j。"""
    from app.kg.models import (
        ChainNode,
        InstitutionNode,
        PersonNode,
        ProjectNode,
    )

    name = project_data["name"]
    chain_name = project_data["chain"]
    stats = {"nodes_created": 0, "relationships_created": 0}

    # 1. 创建 Chain 节点
    await loader.create_chain(ChainNode(name=chain_name))
    stats["nodes_created"] += 1

    # 2. 创建主 Project 节点 + BELONGS_TO 关系
    await loader.create_project(ProjectNode(name=name))
    stats["nodes_created"] += 1
    await loader.relate_project_to_chain(name, chain_name)
    stats["relationships_created"] += 1

    # 3. 遍历团队
    for member in project_data.get("team", []):
        person = PersonNode(name=member["name"])
        await loader.create_person(person)
        stats["nodes_created"] += 1

        role = member.get("role", "")
        rel_type = determine_relation_type(role)
        await loader.relate_person_to_project(
            person_name=member["name"],
            project_name=name,
            relation_type=rel_type,
            role=role,
        )
        stats["relationships_created"] += 1

    # 4. 遍历投融资
    for funding_round in project_data.get("funding", []):
        round_name = funding_round.get("round", "")

        for entry in funding_round.get("investments", []):
            target_project = entry.get("project")
            amount = entry.get("amount")
            year = entry.get("year")

            # 构造轮次描述
            round_type = round_name
            if year:
                round_type = f"{round_name}（{year}）"

            # 如果有生态项目字段，创建生态 Project 节点
            if target_project:
                await loader.create_project(ProjectNode(name=target_project))
                stats["nodes_created"] += 1
                await loader.relate_project_to_chain(target_project, chain_name)
                stats["relationships_created"] += 1

            invest_target = target_project or name

            # 为每个投资方创建 Institution 节点 + INVESTED 关系
            investor_names = collect_all_investors(entry)
            for investor_name in investor_names:
                await loader.create_institution(
                    InstitutionNode(name=investor_name)
                )
                stats["nodes_created"] += 1
                await loader.relate_institution_to_project(
                    institution_name=investor_name,
                    project_name=invest_target,
                    round_type=round_type,
                    amount=amount,
                )
                stats["relationships_created"] += 1

    return stats


async def main():
    """主入口。"""
    from app.data.logger import create_logger
    from app.kg.client import Neo4jClient
    from app.kg.loader import GraphLoader

    logger = create_logger("kg-yaml-import")

    print("=" * 60)
    print("kg.yaml → Neo4j 知识图谱导入")
    print("=" * 60)

    # 读取 YAML
    if not YAML_PATH.exists():
        print(f"错误: 找不到 {YAML_PATH}")
        sys.exit(1)

    data = load_yaml(YAML_PATH)
    projects = data.get("projects", [])
    print(f"已加载 {len(projects)} 个项目: {[p['name'] for p in projects]}")
    print()

    # 连接 Neo4j
    print("正在连接到 Neo4j...")
    client = Neo4jClient()
    await client.connect()
    print("   已连接到 Neo4j")

    total_nodes = 0
    total_rels = 0

    try:
        loader = GraphLoader(client)

        # 初始化约束
        print("\n正在初始化图谱约束...")
        await loader.create_constraints()
        print("   约束就绪")

        # 逐项目导入
        for project_data in projects:
            project_name = project_data["name"]
            print(f"\n正在导入: {project_name}")
            print("-" * 40)

            stats = await import_project(loader, project_data)
            total_nodes += stats["nodes_created"]
            total_rels += stats["relationships_created"]

            print(f"   节点: {stats['nodes_created']}")
            print(f"   关系: {stats['relationships_created']}")
            logger.info(f"已导入项目 {project_name}: {stats}")

        # 汇总
        print("\n" + "=" * 60)
        print("导入完成")
        print("=" * 60)
        print(f"总节点数: {total_nodes}")
        print(f"总关系数: {total_rels}")

        # 查询统计验证
        from app.kg.query import GraphQuery

        query_service = GraphQuery(client)
        stats = await query_service.get_graph_stats()
        print("\n图谱统计:")
        for key, value in stats.items():
            print(f"   - {key}: {value}")

    finally:
        await client.close()
        print("\n连接已关闭")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户取消了导入")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
