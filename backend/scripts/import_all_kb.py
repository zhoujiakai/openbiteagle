#!/usr/bin/env python3
"""Import documents from all sources into the knowledge base.

Usage:
    python scripts/import_all_kb.py [--rootdata 20] [--odaily 20] [--tokenomics 20] [--no-embed]
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """Import from all sources."""
    import argparse

    from app.services.knowledge_loader import get_knowledge_loader

    parser = argparse.ArgumentParser(description="Import from all knowledge base sources")
    parser.add_argument(
        "--rootdata",
        type=int,
        default=20,
        metavar="N",
        help="Number of Rootdata projects to import (default: 20)",
    )
    parser.add_argument(
        "--odaily",
        type=int,
        default=20,
        metavar="N",
        help="Number of Odaily articles to import (default: 20)",
    )
    parser.add_argument(
        "--tokenomics",
        type=int,
        default=20,
        metavar="N",
        help="Number of tokenomics docs to import (default: 20)",
    )
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="Skip generating embeddings",
    )
    parser.add_argument(
        "--skip-rootdata",
        action="store_true",
        help="Skip Rootdata import",
    )
    parser.add_argument(
        "--skip-odaily",
        action="store_true",
        help="Skip Odaily import",
    )
    parser.add_argument(
        "--skip-tokenomics",
        action="store_true",
        help="Skip tokenomics import",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Knowledge Base - Import from All Sources")
    print("=" * 60)
    print(f"Rootdata:   {args.rootdata if not args.skip_rootdata else '(skipped)'}")
    print(f"Odaily:     {args.odaily if not args.skip_odaily else '(skipped)'}")
    print(f"Tokenomics: {args.tokenomics if not args.skip_tokenomics else '(skipped)'}")
    print(f"Embed:      {not args.no_embed}")
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

    # Import from Rootdata
    if not args.skip_rootdata:
        print("-" * 60)
        print("Importing from Rootdata...")
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

    # Import from Odaily
    if not args.skip_odaily:
        print("-" * 60)
        print("Importing from Odaily...")
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

    # Import tokenomics
    if not args.skip_tokenomics:
        print("-" * 60)
        print("Importing tokenomics documents...")
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

    # Print summary
    print()
    print("=" * 60)
    print("Total Import Results")
    print("=" * 60)
    print(f"Fetched:    {total_stats['fetched']}")
    print(f"Imported:   {total_stats['imported']}")
    print(f"Embedded:   {total_stats['embedded']}")
    print(f"Failed:     {total_stats['failed']}")

    if total_stats["errors"]:
        print()
        print("Errors:")
        for error in total_stats["errors"][:10]:
            print(f"  - {error}")
        if len(total_stats["errors"]) > 10:
            print(f"  ... and {len(total_stats['errors']) - 10} more")

    print()
    print("✅ All imports completed")


if __name__ == "__main__":
    asyncio.run(main())
