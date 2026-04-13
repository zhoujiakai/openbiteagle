#!/usr/bin/env python3
"""知识图谱功能测试脚本。"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.kg.client import Neo4jClient
from app.kg.loader import GraphLoader
from app.kg.models import (
    ChainNode,
    InstitutionNode,
    PersonNode,
    PersonRole,
    ProjectNode,
    RelationTypes,
    TokenNode,
)
from app.kg.query import GraphQuery


async def main():
    """运行知识图谱测试。"""
    print("=" * 50)
    print("知识图谱验证测试")
    print("=" * 50)

    # 步骤 1：连接 Neo4j
    print("\n1. 连接 Neo4j...")
    client = Neo4jClient()
    await client.connect()
    print("   ✅ 已连接 Neo4j")

    # 步骤 2：初始化约束
    print("\n2. 初始化图约束...")
    loader = GraphLoader(client)
    await loader.create_constraints()
    print("   ✅ 约束创建完成")

    # 步骤 3：创建测试数据
    print("\n3. 创建测试数据...")

    # 创建链
    await loader.create_chain(ChainNode(
        name="Ethereum",
        description="具有智能合约功能的开源区块链",
        website="https://ethereum.org",
    ))
    print("   ✅ 创建 Ethereum 链")

    # 创建项目
    await loader.create_project(ProjectNode(
        name="Uniswap",
        description="去中心化交易所协议",
        website="https://uniswap.org",
        twitter="Uniswap",
    ))
    print("   ✅ 创建 Uniswap 项目")

    # 创建另一个项目
    await loader.create_project(ProjectNode(
        name="Aave",
        description="去中心化借贷协议",
        website="https://aave.com",
        twitter="Aave",
    ))
    print("   ✅ 创建 Aave 项目")

    # 创建代币
    await loader.create_token(TokenNode(
        symbol="UNI",
        name="Uniswap",
        contract_address="0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
        chain="Ethereum",
    ))
    print("   ✅ 创建 UNI 代币")

    await loader.create_token(TokenNode(
        symbol="AAVE",
        name="Aave Token",
        contract_address="0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9",
        chain="Ethereum",
    ))
    print("   ✅ 创建 AAVE 代币")

    # 创建关系
    await loader.relate_token_to_project("UNI", "Uniswap")
    print("   ✅ UNI -> Uniswap")

    await loader.relate_token_to_project("AAVE", "Aave")
    print("   ✅ AAVE -> Aave")

    await loader.relate_project_to_chain("Uniswap", "Ethereum")
    print("   ✅ Uniswap -> Ethereum")

    await loader.relate_project_to_chain("Aave", "Ethereum")
    print("   ✅ Aave -> Ethereum")

    # 创建人物
    await loader.create_person(PersonNode(
        name="Hayden Adams",
        role=PersonRole.FOUNDER,
        twitter="haydenzadams",
    ))
    print("   ✅ 创建 Hayden Adams")

    await loader.relate_person_to_project("Hayden Adams", "Uniswap", RelationTypes.FOUNDED)
    print("   ✅ Hayden Adams -> Uniswap (创始人)")

    # 创建机构
    await loader.create_institution(InstitutionNode(
        name="Andreessen Horowitz",
        website="https://a16z.com",
        twitter="a16z",
    ))
    print("   ✅ 创建 a16z")

    await loader.relate_institution_to_project("Andreessen Horowitz", "Uniswap", "B 轮", "$11M")
    print("   ✅ a16z -> Uniswap (B 轮融资)")

    # 步骤 4：查询测试
    print("\n4. 测试查询...")
    query_service = GraphQuery(client)

    # 获取统计信息
    stats = await query_service.get_graph_stats()
    print(f"   📊 图统计: {stats}")

    # 获取项目上下文
    context = await query_service.get_project_context("Uniswap")
    print("\n   📦 Uniswap 上下文:")
    print(f"      - 代币: {len(context.get('tokens', []))}")
    print(f"      - 团队: {len(context.get('team', []))}")
    print(f"      - 投资者: {len(context.get('investors', []))}")
    print(f"      - 链: {context.get('chain', {}).get('name', 'N/A')}")

    # 获取关联项目
    related = await query_service.find_related_projects("Uniswap", max_hops=2)
    print(f"\n   🔗 与 Uniswap 关联的项目: {len(related)}")
    for r in related[:3]:
        print(f"      - {r['project'].get('name', '未知')} (距离: {r['distance']})")

    # 搜索项目
    results = await query_service.search_projects_by_keyword("去中心化")
    print(f"\n   🔍 搜索 '去中心化': {len(results)} 个结果")
    for r in results:
        print(f"      - {r.get('name', '未知')}")

    # 获取链上的项目
    eth_projects = await query_service.get_chain_projects("Ethereum")
    print(f"\n   ⛓️ Ethereum 项目: {len(eth_projects)}")
    for p in eth_projects:
        print(f"      - {p.get('name', '未知')}")

    # 获取人物关联的项目
    person_projects = await query_service.get_person_projects("Hayden Adams")
    print(f"\n   👤 Hayden Adams 的项目: {len(person_projects)}")
    for p in person_projects:
        print(f"      - {p['project'].get('name', '未知')} ({p.get('relationship', '未知')})")

    # 获取代币信息
    token_info = await query_service.get_token_info("UNI")
    if token_info:
        print("\n   💰 UNI 代币:")
        print(f"      - 项目: {token_info['project'].get('name', '未知')}")

    # 步骤 5：清理
    print("\n5. 关闭连接...")
    await client.close()
    print("   ✅ 连接已关闭")

    print("\n" + "=" * 50)
    print("所有测试通过！ ✅")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
