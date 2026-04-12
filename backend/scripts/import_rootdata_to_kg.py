#!/usr/bin/env python3
"""Import Rootdata projects into Neo4j Knowledge Graph.

Usage:
    python scripts/import_rootdata_to_kg.py --limit 50

This script fetches projects from Rootdata and imports them into
the Neo4j knowledge graph with proper nodes and relationships.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """Main import function."""
    import argparse

    from app.kg.client import Neo4jClient, Neo4jSettings
    from app.kg.importers import RootdataKGImporter
    from app.kg.loader import GraphLoader
    from app.kg.query import GraphQuery
    from app.wrappers.rootdata import scrape_rootdata_projects

    parser = argparse.ArgumentParser(
        description="Import Rootdata projects to Neo4j Knowledge Graph"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of projects to import (default: 20)",
    )
    parser.add_argument(
        "--headless",
        type=bool,
        default=True,
        help="Run browser in headless mode (default: True)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip projects that already exist in KG",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_false",
        dest="skip_existing",
        help="Don't skip existing projects (update them)",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show graph statistics, don't import",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Rootdata → Neo4j Knowledge Graph Import")
    print("=" * 60)
    print(f"Limit: {args.limit}")
    print(f"Skip existing: {args.skip_existing}")
    print()

    # Connect to Neo4j
    print("Connecting to Neo4j...")
    settings = Neo4jSettings()
    client = await Neo4jClient.create(settings)
    print("   ✅ Connected to Neo4j")

    try:
        loader = GraphLoader(client)
        query_service = GraphQuery(client)

        # Initialize constraints
        print("\nInitializing graph constraints...")
        await loader.create_constraints()
        print("   ✅ Constraints ready")

        # Show current stats
        print("\n📊 Current Graph Statistics:")
        stats_before = await query_service.get_graph_stats()
        for key, value in stats_before.items():
            print(f"   - {key}: {value}")

        if args.stats_only:
            print("\n--stats-only mode, exiting--")
            return

        # Fetch projects from Rootdata
        print(f"\nFetching {args.limit} projects from Rootdata...")
        print("(This may take a minute with Playwright...)")
        projects = await scrape_rootdata_projects(limit=args.limit)
        print(f"   ✅ Fetched {len(projects)} projects")

        if not projects:
            print("No projects fetched, exiting.")
            return

        # Show sample project info
        print("\n📦 Sample Project:")
        sample = projects[0]
        print(f"   Name: {sample.name}")
        print(f"   Token: {sample.token.symbol if sample.token else 'None'}")
        print(f"   Chains: {', '.join(sample.chains) if sample.chains else 'None'}")
        print(f"   Investors: {len(sample.investors)}")

        # Import to KG
        print(f"\nImporting {len(projects)} projects to Neo4j KG...")
        print("-" * 60)

        importer = RootdataKGImporter(loader)
        result = await importer.import_batch(
            projects,
            skip_existing=args.skip_existing,
        )

        print("-" * 60)
        print("\n" + "=" * 60)
        print("Import Results")
        print("=" * 60)
        print(f"Total projects:   {result['total']}")
        print(f"✅ Success:       {result['success']}")
        print(f"❌ Failed:        {result['failed']}")
        print(f"⏭️  Skipped:       {result['skipped']}")
        print(f"\nNodes created:     {result['nodes_created']}")
        print(f"Relationships:      {result['relationships_created']}")

        if result["errors"]:
            print(f"\nErrors ({len(result['errors'])}):")
            for error in result["errors"][:5]:
                print(f"   - {error['project']}: {error['error']}")
            if len(result["errors"]) > 5:
                print(f"   ... and {len(result['errors']) - 5} more")

        # Show updated stats
        print("\n📊 Updated Graph Statistics:")
        stats_after = await query_service.get_graph_stats()
        for key, value in stats_after.items():
            before = stats_before.get(key, 0)
            delta = value - before
            delta_str = f" (+{delta})" if delta > 0 else ""
            print(f"   - {key}: {value}{delta_str}")

        print("\n✅ Import completed!")

        # Test a query
        if result["success"] > 0:
            print("\n🔍 Testing query on imported project...")
            first_project = projects[0]
            context = await query_service.get_project_context(first_project.name)
            if context.get("project"):
                print(f"   Project: {context['project'].get('name')}")
                print(f"   Tokens: {len(context.get('tokens', []))}")
                chain = context.get('chain')
                print(f"   Chains: {chain.get('name', 'N/A') if chain else 'N/A'}")
                print(f"   Investors: {len(context.get('investors', []))}")

    finally:
        await client.close()
        print("\n✅ Connection closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Import cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
