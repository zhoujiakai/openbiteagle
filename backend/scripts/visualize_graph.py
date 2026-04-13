#!/usr/bin/env python
"""Visualize the news analysis graph structure."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tasks.task2_analyze_flow.graph import visualize_graph


if __name__ == "__main__":
    visualize_graph()
