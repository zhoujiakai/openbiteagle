#!/usr/bin/env python3
"""Import deep articles from Odaily into the knowledge base.

Usage:
    python scripts/import_from_odaily.py [--limit 20] [--no-embed] [--real]
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """Import Odaily deep articles."""
    import argparse

    from app.services.knowledge_loader import get_knowledge_loader

    parser = argparse.ArgumentParser(description="Import Odaily deep articles")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of articles to import (default: 20)",
    )
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="Skip generating embeddings",
    )
    parser.add_argument(
        "--real",
        action="store_true",
        help="Fetch real articles from Odaily (default: use mock data)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Odaily Deep Articles Knowledge Base Import")
    print("=" * 60)
    print(f"Limit: {args.limit}")
    print(f"Embed: {not args.no_embed}")
    print(f"Real data: {args.real}")
    print()

    loader = get_knowledge_loader()

    stats = await loader.import_odaily_articles(
        limit=args.limit,
        embed=not args.no_embed,
        use_real=args.real,
    )

    print()
    print("=" * 60)
    print("Import Results")
    print("=" * 60)
    print(f"Fetched:    {stats['fetched']}")
    print(f"Imported:   {stats['imported']}")
    print(f"Embedded:   {stats['embedded']}")
    print(f"Failed:     {stats['failed']}")

    if stats["errors"]:
        print()
        print("Errors:")
        for error in stats["errors"][:5]:
            print(f"  - {error}")

    print()
    print("✅ Import completed")


if __name__ == "__main__":
    asyncio.run(main())
