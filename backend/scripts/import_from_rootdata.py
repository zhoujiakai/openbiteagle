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
    """Import Rootdata projects."""
    import argparse

    from app.services.knowledge_loader import get_knowledge_loader

    parser = argparse.ArgumentParser(description="Import Rootdata projects")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of projects to import (default: 20)",
    )
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="Skip generating embeddings",
    )
    parser.add_argument(
        "--kg",
        "--import-to-kg",
        action="store_true",
        dest="import_to_kg",
        help="Also import to Neo4j Knowledge Graph",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Rootdata Knowledge Base Import")
    print("=" * 60)
    print(f"Limit: {args.limit}")
    print(f"Embed: {not args.no_embed}")
    print(f"Import to KG: {args.import_to_kg}")
    print()

    loader = get_knowledge_loader()

    stats = await loader.import_rootdata_projects(
        limit=args.limit,
        embed=not args.no_embed,
        import_to_kg=args.import_to_kg,
    )

    print()
    print("=" * 60)
    print("Import Results")
    print("=" * 60)
    print(f"Fetched:    {stats['fetched']}")
    print(f"Imported:   {stats['imported']}")
    print(f"Embedded:   {stats['embedded']}")
    print(f"Failed:     {stats['failed']}")

    if stats.get("kg_stats"):
        kg = stats["kg_stats"]
        print()
        print("Knowledge Graph:")
        print(f"  Success:   {kg['success']}")
        print(f"  Failed:    {kg['failed']}")
        print(f"  Nodes:     {kg['nodes_created']}")
        print(f"  Relations: {kg['relationships_created']}")

    if stats["errors"]:
        print()
        print("Errors:")
        for error in stats["errors"][:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(stats["errors"]) > 5:
            print(f"  ... and {len(stats['errors']) - 5} more")

    print()
    print("✅ Import completed")


if __name__ == "__main__":
    asyncio.run(main())
