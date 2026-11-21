"""Run the visualizer tests from the repository root."""

import subprocess
import sys
import unittest
from pathlib import Path


class VisualizerTests(unittest.TestCase):
    """Expose the visualizer's test suite at the repository root."""

    def test_project_suite(self) -> None:
        """Run the standalone test suite from its own directory."""
        root = Path(__file__).resolve().parents[1]
        project = root / "src" / "dependency_graph_lab"
        subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"],
            cwd=project,
            check=True,
        )
