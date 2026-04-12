#!/usr/bin/env python3
"""Test script for Knowledge Graph functionality."""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.kg.client import Neo4jClient, Neo4jSettings
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
    """Run knowledge graph tests."""
    print("=" * 50)
    print("Knowledge Graph Verification Test")
    print("=" * 50)

    # Step 1: Connect to Neo4j
    print("\n1. Connecting to Neo4j...")
    settings = Neo4jSettings()
    client = await Neo4jClient.create(settings)
    print("   ✅ Connected to Neo4j")

    # Step 2: Initialize constraints
    print("\n2. Initializing graph constraints...")
    loader = GraphLoader(client)
    await loader.create_constraints()
    print("   ✅ Constraints created")

    # Step 3: Create test data
    print("\n3. Creating test data...")

    # Create chain
    await loader.create_chain(ChainNode(
        name="Ethereum",
        description="Open-source blockchain with smart contract functionality",
        website="https://ethereum.org",
    ))
    print("   ✅ Created Ethereum chain")

    # Create project
    await loader.create_project(ProjectNode(
        name="Uniswap",
        description="Decentralized exchange protocol",
        website="https://uniswap.org",
        twitter="Uniswap",
    ))
    print("   ✅ Created Uniswap project")

    # Create another project
    await loader.create_project(ProjectNode(
        name="Aave",
        description="Decentralized lending protocol",
        website="https://aave.com",
        twitter="Aave",
    ))
    print("   ✅ Created Aave project")

    # Create tokens
    await loader.create_token(TokenNode(
        symbol="UNI",
        name="Uniswap",
        contract_address="0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
        chain="Ethereum",
    ))
    print("   ✅ Created UNI token")

    await loader.create_token(TokenNode(
        symbol="AAVE",
        name="Aave Token",
        contract_address="0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9",
        chain="Ethereum",
    ))
    print("   ✅ Created AAVE token")

    # Create relationships
    await loader.relate_token_to_project("UNI", "Uniswap")
    print("   ✅ UNI -> Uniswap")

    await loader.relate_token_to_project("AAVE", "Aave")
    print("   ✅ AAVE -> Aave")

    await loader.relate_project_to_chain("Uniswap", "Ethereum")
    print("   ✅ Uniswap -> Ethereum")

    await loader.relate_project_to_chain("Aave", "Ethereum")
    print("   ✅ Aave -> Ethereum")

    # Create person
    await loader.create_person(PersonNode(
        name="Hayden Adams",
        role=PersonRole.FOUNDER,
        twitter="haydenzadams",
    ))
    print("   ✅ Created Hayden Adams")

    await loader.relate_person_to_project("Hayden Adams", "Uniswap", RelationTypes.FOUNDED)
    print("   ✅ Hayden Adams -> Uniswap (FOUNDED)")

    # Create institution
    await loader.create_institution(InstitutionNode(
        name="Andreessen Horowitz",
        website="https://a16z.com",
        twitter="a16z",
    ))
    print("   ✅ Created a16z")

    await loader.relate_institution_to_project("Andreessen Horowitz", "Uniswap", "Series B", "$11M")
    print("   ✅ a16z -> Uniswap (Series B)")

    # Step 4: Query tests
    print("\n4. Testing queries...")
    query_service = GraphQuery(client)

    # Get stats
    stats = await query_service.get_graph_stats()
    print(f"   📊 Graph stats: {stats}")

    # Get project context
    context = await query_service.get_project_context("Uniswap")
    print("\n   📦 Uniswap context:")
    print(f"      - Tokens: {len(context.get('tokens', []))}")
    print(f"      - Team: {len(context.get('team', []))}")
    print(f"      - Investors: {len(context.get('investors', []))}")
    print(f"      - Chain: {context.get('chain', {}).get('name', 'N/A')}")

    # Get related projects
    related = await query_service.find_related_projects("Uniswap", max_hops=2)
    print(f"\n   🔗 Related projects to Uniswap: {len(related)}")
    for r in related[:3]:
        print(f"      - {r['project'].get('name', 'Unknown')} (distance: {r['distance']})")

    # Search projects
    results = await query_service.search_projects_by_keyword("decentralized")
    print(f"\n   🔍 Search 'decentralized': {len(results)} results")
    for r in results:
        print(f"      - {r.get('name', 'Unknown')}")

    # Get chain projects
    eth_projects = await query_service.get_chain_projects("Ethereum")
    print(f"\n   ⛓️ Ethereum projects: {len(eth_projects)}")
    for p in eth_projects:
        print(f"      - {p.get('name', 'Unknown')}")

    # Get person projects
    person_projects = await query_service.get_person_projects("Hayden Adams")
    print(f"\n   👤 Hayden Adams projects: {len(person_projects)}")
    for p in person_projects:
        print(f"      - {p['project'].get('name', 'Unknown')} ({p.get('relationship', 'Unknown')})")

    # Get token info
    token_info = await query_service.get_token_info("UNI")
    if token_info:
        print("\n   💰 UNI token:")
        print(f"      - Project: {token_info['project'].get('name', 'Unknown')}")

    # Step 5: Cleanup
    print("\n5. Closing connection...")
    await client.close()
    print("   ✅ Connection closed")

    print("\n" + "=" * 50)
    print("All tests passed! ✅")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
