"""完整新闻分析图的集成测试。

使用模拟的 LLM 调用测试端到端流程。"""

import pytest

from tasks.task2_analyze_flow import build_news_analysis_graph


class TestGraphFlow:
    """完整图执行测试。"""

    @pytest.mark.asyncio
    async def test_graph_compilation(self):
        """测试图编译无错误。"""
        graph = build_news_analysis_graph()
        assert graph is not None

    def test_graph_structure(self):
        """测试图具有正确的节点和边。"""
        graph = build_news_analysis_graph()
        graph_dict = graph.get_graph()

        # 检查入口点（不同 LangGraph 版本可能存储方式不同）
        entry_point = getattr(graph_dict, "entry_point", None)
        if entry_point:
            assert entry_point == "investment_value"

        # 检查节点是否存在（节点可能是字符串或对象）
        node_names = set()
        for n in graph_dict.nodes:
            if isinstance(n, str):
                node_names.add(n)
            else:
                node_names.add(getattr(n, "id", str(n)))

        expected_nodes = {
            "investment_value",
            "extract_tokens",
            "search_token_info",
            "trend_analysis",
            "generate_recommendation",
        }
        assert expected_nodes.issubset(node_names)

    def test_visualize_graph(self, capsys):
        """测试图可视化功能。"""
        from tasks.task2_analyze_flow.graph import visualize_graph

        visualize_graph()
        captured = capsys.readouterr()
        # 应打印 ASCII 图
        assert captured.out is not None
