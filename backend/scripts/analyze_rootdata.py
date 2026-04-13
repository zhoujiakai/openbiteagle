#!/usr/bin/env python3
"""分析 Rootdata 页面结构并修复爬虫。"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """分析 Rootdata 并提取数据。"""
    from playwright.async_api import async_playwright

    print("正在分析 Rootdata...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        # 导航到项目页面
        print("正在加载项目页面...")
        await page.goto("https://www.rootdata.com/projects", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # 获取页面内容并分析
        content = await page.content()

        # 查找 __NUXT__ 数据（Nuxt 应用的常见模式）
        nuxt_data = await page.evaluate("""() => {
            // 尝试查找 window.__NUXT__
            if (window.__NUXT__) {
                return window.__NUXT__;
            }
            // 尝试在 script 标签中查找数据
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
            print(f"\n✅ 找到 __NUXT__ 数据!")
            # 保存以便分析
            output_path = Path(__file__).parent.parent / "data" / "kb_docs" / "nuxt_data.json"
            with open(output_path, "w") as f:
                json.dump(nuxt_data, f, indent=2, default=str)
            print(f"已保存到: {output_path}")

            # 尝试从数据中提取项目
            if "data" in str(nuxt_data):
                print("\n正在搜索项目数据...")

        # 同时检查网络中的 API 调用
        print("\n正在查找项目详情页链接...")
        links = await page.query_selector_all("a")
        project_ids = set()

        for link in links:
            href = await link.get_attribute("href")
            if href:
                # 查找项目详情链接
                if "/project_detail/" in href or "/project/detail/" in href:
                    # 提取 ID
                    import re
                    match = re.search(r'/project[_/]?detail/?/(\d+)', href)
                    if match:
                        project_ids.add(match.group(1))

        print(f"从链接中找到 {len(project_ids)} 个项目 ID:")
        for pid in sorted(project_ids)[:20]:
            print(f"  - {pid}")

        # 尝试获取项目名称
        for pid in list(project_ids)[:5]:
            link = await page.query_selector(f'a[href*="/project_detail/{pid}"], a[href*="/project/detail/{pid}"]')
            if link:
                text = await link.inner_text()
                print(f"  Project {pid}: {text[:50]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
