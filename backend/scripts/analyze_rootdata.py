#!/usr/bin/env python3
"""Analyze Rootdata page structure and fix scraper."""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """Analyze Rootdata and extract data."""
    from playwright.async_api import async_playwright

    print("Analyzing Rootdata...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        # Navigate to projects page
        print("Loading projects page...")
        await page.goto("https://www.rootdata.com/projects", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Get page content and analyze
        content = await page.content()

        # Look for __NUXT__ data (common pattern in Nuxt apps)
        nuxt_data = await page.evaluate("""() => {
            // Try to find window.__NUXT__
            if (window.__NUXT__) {
                return window.__NUXT__;
            }
            // Try to find data in script tags
            const scripts = document.querySelectorAll('script');
            for (let script of scripts) {
                if (script.textContent.includes('__NUXT__')) {
                    try {
                        const match = script.textContent.match(/window.__NUXT__\s*=\s*({.*?});/);
                        if (match) {
                            return JSON.parse(match[1]);
                        }
                    } catch (e) {}
                }
            }
            return null;
        }""")

        if nuxt_data:
            print(f"\n✅ Found __NUXT__ data!")
            # Save for analysis
            output_path = Path(__file__).parent.parent / "data" / "kb_docs" / "nuxt_data.json"
            with open(output_path, "w") as f:
                json.dump(nuxt_data, f, indent=2, default=str)
            print(f"Saved to: {output_path}")

            # Try to extract projects from the data
            if "data" in str(nuxt_data):
                print("\nSearching for project data...")

        # Also check for API calls in network
        print("\nLooking for links to project detail pages...")
        links = await page.query_selector_all("a")
        project_ids = set()

        for link in links:
            href = await link.get_attribute("href")
            if href:
                # Look for project detail links
                if "/project_detail/" in href or "/project/detail/" in href:
                    # Extract ID
                    import re
                    match = re.search(r'/project[_/]?detail/?/(\d+)', href)
                    if match:
                        project_ids.add(match.group(1))

        print(f"Found {len(project_ids)} project IDs from links:")
        for pid in sorted(project_ids)[:20]:
            print(f"  - {pid}")

        # Try to get project names
        for pid in list(project_ids)[:5]:
            link = await page.query_selector(f'a[href*="/project_detail/{pid}"], a[href*="/project/detail/{pid}"]')
            if link:
                text = await link.inner_text()
                print(f"  Project {pid}: {text[:50]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
