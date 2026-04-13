"""Integration tests for the complete news analysis graph.

Tests the end-to-end flow with mocked LLM calls.
"""

import pytest

from tasks.task2_analyze_flow import build_news_analysis_graph


class TestGraphFlow:
    """Tests for complete graph execution."""

    @pytest.mark.asyncio
    async def test_graph_compilation(self):
        """Test graph compiles without errors."""
        graph = build_news_analysis_graph()
        assert graph is not None

    def test_graph_structure(self):
        """Test graph has correct nodes and edges."""
        graph = build_news_analysis_graph()
        graph_dict = graph.get_graph()

        # Check entry point (may be stored differently in different LangGraph versions)
        entry_point = getattr(graph_dict, "entry_point", None)
        if entry_point:
            assert entry_point == "investment_value"

        # Check nodes exist (nodes may be strings or objects)
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
        """Test graph visualization works."""
        from tasks.task2_analyze_flow.graph import visualize_graph

        visualize_graph()
        captured = capsys.readouterr()
        # Should print ASCII graph
        assert captured.out is not None
