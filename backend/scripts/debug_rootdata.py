#!/usr/bin/env python3
"""调试 Rootdata 页面结构。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """调试 Rootdata 页面。"""
    print("=" * 60)
    print("正在调试 Rootdata 页面结构")
    print("=" * 60)
    print()

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 显示浏览器以便调试
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        print("正在导航到 Rootdata 项目页面...")
        await page.goto("https://www.rootdata.com/projects", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # 保存截图
        screenshot_path = Path(__file__).parent.parent / "data" / "kb_docs" / "rootdata_debug.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path))
        print(f"截图已保存: {screenshot_path}")

        # 获取页面标题
        title = await page.title()
        print(f"页面标题: {title}")

        # 尝试查找项目链接
        print("\n正在搜索项目链接...")

        # 尝试不同的选择器模式
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
                    print(f"\n✅ 模式 '{pattern}' 找到 {len(elements)} 个元素")
                    # 显示前几个
                    for i, el in enumerate(elements[:3]):
                        href = await el.get_attribute("href")
                        text = await el.inner_text()
                        print(f"  [{i+1}] href={href}, text={text[:50]}")
            except Exception as e:
                print(f"  Pattern '{pattern}': {e}")

        # 获取所有链接
        print("\n\n页面上的所有链接:")
        links = await page.query_selector_all("a")
        project_links = []
        for link in links:
            href = await link.get_attribute("href")
            if href and ("project" in href.lower() or "detail" in href.lower()):
                text = await link.inner_text()
                project_links.append((href, text.strip()[:50]))

        print(f"找到 {len(project_links)} 个项目相关链接:")
        for href, text in project_links[:10]:
            print(f"  {href} - {text}")

        print("\n按回车键关闭浏览器...")
        input()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
