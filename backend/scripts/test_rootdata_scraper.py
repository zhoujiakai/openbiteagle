#!/usr/bin/env python3
"""Test Rootdata scraper functionality."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """Test Rootdata scraper."""
    print("=" * 60)
    print("Testing Rootdata Scraper")
    print("=" * 60)
    print()

    from app.wrappers.rootdata import RootdataClient, ProjectInfo

    # Test 1: Initialize client
    print("Test 1: Initialize client")
    print("-" * 60)
    try:
        client = RootdataClient(headless=True)
        await client.start()
        print("✅ Client started successfully")
    except Exception as e:
        print(f"❌ Failed to start client: {e}")
        return
    print()

    # Test 2: Fetch project list
    print("Test 2: Fetch project list (limit: 5)")
    print("-" * 60)
    try:
        projects = await client.get_project_list(limit=5)
        print(f"✅ Found {len(projects)} projects:")
        for p in projects:
            print(f"  - [{p['id']}] {p['name']}")
    except Exception as e:
        print(f"❌ Failed to fetch projects: {e}")
        import traceback
        traceback.print_exc()
    print()

    # Test 3: Fetch project detail
    if projects:
        print("Test 3: Fetch project detail")
        print("-" * 60)
        try:
            test_project = projects[0]
            detail = await client.get_project_detail(test_project["id"])
            if detail:
                print(f"✅ Project detail fetched:")
                print(f"  Name: {detail.name}")
                print(f"  Description: {detail.description[:100] if detail.description else 'N/A'}...")
                print(f"  Categories: {detail.categories}")
                print(f"  Token: {detail.token.symbol if detail.token else 'N/A'}")
                print(f"  Chains: {detail.chains}")
            else:
                print("❌ No detail returned")
        except Exception as e:
            print(f"❌ Failed to fetch detail: {e}")
            import traceback
            traceback.print_exc()
    print()

    # Test 4: Convert to KB document
    if projects:
        print("Test 4: Convert to KB document format")
        print("-" * 60)
        try:
            test_project = projects[0]
            detail = await client.get_project_detail(test_project["id"])
            if detail:
                doc_data = detail.to_kb_document()
                print(f"✅ Converted to KB document:")
                print(f"  Title: {doc_data['title']}")
                print(f"  Content length: {len(doc_data['content'])} chars")
                print(f"  Source type: {doc_data['source_type']}")
                print(f"  Tokens: {doc_data['metadata'].get('tokens', [])}")
        except Exception as e:
            print(f"❌ Failed to convert: {e}")
    print()

    # Close client
    await client.close()

    print("=" * 60)
    print("✅ Tests completed")


if __name__ == "__main__":
    asyncio.run(main())
