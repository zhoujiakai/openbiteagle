#!/usr/bin/env python
"""可视化新闻分析图谱结构。"""

import sys
from pathlib import Path

# 将项目根目录添加到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tasks.task2_analyze_flow.graph import visualize_graph


if __name__ == "__main__":
    visualize_graph()
