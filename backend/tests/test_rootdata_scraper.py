#!/usr/bin/env python3
"""测试 RootData API 客户端功能。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """测试 RootData API 客户端。"""
    print("=" * 60)
    print("测试 RootData API 客户端")
    print("=" * 60)
    print()

    from app.wrappers.rootdata import RootdataClient, ProjectInfo

    # 测试 1：初始化客户端
    print("测试 1：初始化客户端")
    print("-" * 60)
    try:
        client = RootdataClient()
        print("✅ 客户端创建成功")
    except Exception as e:
        print(f"❌ 客户端创建失败: {e}")
        return
    print()

    # 测试 2：检查 API 余额
    print("测试 2：检查 API 余额")
    print("-" * 60)
    try:
        async with client:
            credits = await client.check_credits()
            print(f"✅ 余额: {credits.get('credits', 'N/A')}/{credits.get('total_credits', 'N/A')}")
    except Exception as e:
        print(f"❌ 查询余额失败: {e}")
    print()

    # 测试 3：获取项目列表
    print("测试 3：获取项目列表（限制: 5）")
    print("-" * 60)
    projects = []
    try:
        async with RootdataClient() as c:
            projects = await c.get_project_list(limit=5)
            print(f"✅ 找到 {len(projects)} 个项目:")
            for p in projects:
                print(f"  - [{p['id']}] {p['name']}")
    except Exception as e:
        print(f"❌ 获取项目列表失败: {e}")
        import traceback
        traceback.print_exc()
    print()

    # 测试 4：获取项目详情
    if projects:
        print("测试 4：获取项目详情")
        print("-" * 60)
        try:
            async with RootdataClient() as c:
                test_project = projects[0]
                detail = await c.get_project_detail(test_project["id"])
                if detail:
                    print(f"✅ 获取项目详情成功:")
                    print(f"  名称: {detail.name}")
                    print(f"  描述: {detail.description[:100] if detail.description else 'N/A'}...")
                    print(f"  分类: {detail.categories}")
                    print(f"  代币: {detail.token.symbol if detail.token else 'N/A'}")
                    print(f"  链: {detail.chains}")
                else:
                    print("❌ 未返回详情")
        except Exception as e:
            print(f"❌ 获取项目详情失败: {e}")
            import traceback
            traceback.print_exc()
    print()

    # 测试 5：转换为知识库文档
    if projects:
        print("测试 5：转换为知识库文档格式")
        print("-" * 60)
        try:
            async with RootdataClient() as c:
                test_project = projects[0]
                detail = await c.get_project_detail(test_project["id"])
                if detail:
                    doc_data = detail.to_kb_document()
                    print(f"✅ 转换为知识库文档成功:")
                    print(f"  标题: {doc_data['title']}")
                    print(f"  内容长度: {len(doc_data['content'])} 字符")
                    print(f"  来源类型: {doc_data['source_type']}")
                    print(f"  代币: {doc_data['metadata'].get('tokens', [])}")
        except Exception as e:
            print(f"❌ 转换失败: {e}")
    print()

    print("=" * 60)
    print("✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
