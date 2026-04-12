# task1_fetch_data — Odaily 快讯爬虫

## 数据源

目标页面：`https://www.odaily.news/zh-CN/newsflash`

`flash_sources/` 目录下保存了一份完整的页面 HTML 快照，用于离线分析 DOM 结构。

## 页面 DOM 结构

页面中每条快讯是一个 `div.newsflash-item`，关键属性和子元素：

```
div.newsflash-item [data-publish-timestamp="1776004416000"]
  └─ div.data-list [data-id="476412"]
       ├─ span                    → 时间 "22:33"
       ├─ a[href*="newsflash"]    → 标题 + Odaily 快讯链接
       │    └─ span               → 标题文本
       ├─ div.whitespace-pre-line → 正文内容
       └─ a:text("原文链接")      → 原文外链（可选）
```

## 字段提取策略

| 字段 | 来源 |
|------|------|
| published_at | `data-publish-timestamp`（毫秒时间戳 → datetime） |
| source_id | `div.data-list` 的 `data-id` |
| title | `a[href*="newsflash"] > span` 文本 |
| content | `div.whitespace-pre-line` 文本 |
| page_url | `a[href*="newsflash"]` 的 href（Odaily 快讯页链接） |
| external_url | `a:text("原文链接")` 的 href（原文外链，可选） |

## 运行

```bash
python odaily_scraper.py
```

依赖 Playwright，首次需 `playwright install chromium`。
