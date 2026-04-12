#!/usr/bin/env python3
"""Debug Rootdata page structure."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """Debug Rootdata page."""
    print("=" * 60)
    print("Debugging Rootdata Page Structure")
    print("=" * 60)
    print()

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser for debugging
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        print("Navigating to Rootdata projects page...")
        await page.goto("https://www.rootdata.com/projects", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Save screenshot
        screenshot_path = Path(__file__).parent.parent / "data" / "kb_docs" / "rootdata_debug.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path))
        print(f"Screenshot saved: {screenshot_path}")

        # Get page title
        title = await page.title()
        print(f"Page title: {title}")

        # Try to find project links
        print("\nSearching for project links...")

        # Try different patterns
        patterns = [
            'a[href*="/project_detail/"]',
            'a[href*="/project/"]',
            'a[href*="detail"]',
            '[class*="project"] a',
            '[class*="card"] a',
            'a[class*="item"]',
        ]

        for pattern in patterns:
            try:
                elements = await page.query_selector_all(pattern)
                if elements:
                    print(f"\n✅ Pattern '{pattern}' found {len(elements)} elements")
                    # Show first few
                    for i, el in enumerate(elements[:3]):
                        href = await el.get_attribute("href")
                        text = await el.inner_text()
                        print(f"  [{i+1}] href={href}, text={text[:50]}")
            except Exception as e:
                print(f"  Pattern '{pattern}': {e}")

        # Get all links
        print("\n\nAll links on page:")
        links = await page.query_selector_all("a")
        project_links = []
        for link in links:
            href = await link.get_attribute("href")
            if href and ("project" in href.lower() or "detail" in href.lower()):
                text = await link.inner_text()
                project_links.append((href, text.strip()[:50]))

        print(f"Found {len(project_links)} project-related links:")
        for href, text in project_links[:10]:
            print(f"  {href} - {text}")

        print("\nPress Enter to close browser...")
        input()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
