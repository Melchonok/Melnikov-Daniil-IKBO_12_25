"""Verify the CLI, traversal, rendering, and repository parsing."""

import io
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http import HTTPStatus
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

from src.dependency_graph.__main__ import main
from src.dependency_graph.graph import build_graph, reverse_edges
from src.dependency_graph.render import ascii_tree, plantuml
from src.dependency_graph.repository import PyPIRepository, RepositoryError


PROJECT = Path(__file__).resolve().parents[1]
FIXTURE = PROJECT / "example_repository.json"


def invoke(*args: str) -> tuple[int, str, str]:
    """Capture the exit status and streams of one CLI invocation."""
    output = io.StringIO()
    errors = io.StringIO()
    with redirect_stdout(output), redirect_stderr(errors):
        try:
            status = main(list(args))
        except SystemExit as error:
            status = error.code
    return status, output.getvalue(), errors.getvalue()


class GraphTests(unittest.TestCase):
    """Check depth limits, cycles, and edge direction."""

    def test_shorter_path_allows_further_traversal(self):
        """Reach F through C even when E was reached earlier via B."""
        dependencies = {
            "A": ("B", "C"),
            "B": ("D",),
            "C": ("E",),
            "D": ("E",),
            "E": ("F",),
        }
        graph = build_graph("A", dependencies.__getitem__, max_depth=3)
        self.assertEqual(graph["E"], ("F",))
        self.assertEqual(graph["F"], ())

    def test_cycle_is_kept_in_graph_and_marked_in_tree(self):
        """Preserve a back edge without recursively following it forever."""
        dependencies = {"A": ("B",), "B": ("A",)}
        graph = build_graph("A", dependencies.__getitem__, max_depth=5)
        self.assertEqual(graph, dependencies)
        self.assertIn("p1 --> p0", plantuml(graph))
        self.assertIn("A (cycle)", ascii_tree(graph, "A", 5))

    def test_reverse_depth(self):
        """List one or two levels of packages depending on A."""
        graph = {"A": (), "B": ("A",), "C": ("B",)}
        parents = reverse_edges(graph)
        self.assertEqual(
            build_graph("A", parents.__getitem__, max_depth=1),
            {"A": ("B",), "B": ()},
        )
        self.assertEqual(
            build_graph("A", parents.__getitem__, max_depth=2),
            {"A": ("B",), "B": ("C",), "C": ()},
        )


class CliTests(unittest.TestCase):
    """Check that the public command accepts and validates its options."""

    def test_project_launcher(self):
        """Keep the python -m dependency_graph entry point working."""
        command = [
            sys.executable, "-B", "-m", "dependency_graph", "-p", "A",
            "--test", "-r", str(FIXTURE), "--ascii", "-d", "4",
        ]
        result = subprocess.run(
            command, cwd=PROJECT, capture_output=True, text=True, check=True
        )
        self.assertIn("@startuml", result.stdout)
        self.assertIn("A (cycle)", result.stdout)

    def test_config_prints_all_settings(self):
        """Print the five configuration values as key-value pairs."""
        status, output, _ = invoke(
            "-p", "A", "--test", "-r", str(FIXTURE), "--show-config"
        )
        self.assertEqual(status, 0)
        self.assertEqual(output.splitlines(), [
            "package=A", f"repo={FIXTURE}", "test=true", "ascii=false",
            "max_depth=2",
        ])

    def test_invalid_options(self):
        """Reject invalid arguments and accidental mode combinations."""
        cases = (
            (("-p", "bad name"), "--package"),
            (("-p", "a", "--test", "-r", str(FIXTURE)), "--package"),
            (("-p", "A", "--test"), "--repo"),
            (("-p", "A", "-r", "ftp://pypi.org"), "--repo"),
            (("-p", "A", "--test=bad"), "--test"),
            (("-p", "A", "--ascii=bad"), "--ascii"),
            (("-p", "A", "-d", "-1"), "nonnegative integer"),
            (("-p", "A", "--reverse"), "requires --test"),
            (("-p", "A", "--direct", "--graph"), "not allowed"),
        )
        for args, message in cases:
            with self.subTest(args=args):
                status, output, errors = invoke(*args)
                self.assertEqual(status, 2)
                self.assertEqual(output, "")
                self.assertIn(message, errors)

    def test_unknown_package_at_depth_zero(self):
        """Validate the root even when its children are outside the graph."""
        status, output, errors = invoke(
            "-p", "UNKNOWN", "--test", "-r", str(FIXTURE), "-d", "0"
        )
        self.assertEqual(status, 1)
        self.assertEqual(output, "")
        self.assertIn("was not found", errors)

    def test_reverse_output(self):
        """Use the test repository for reverse traversal."""
        status, output, _ = invoke(
            "-p", "C", "--test", "-r", str(FIXTURE), "--reverse", "-d", "1"
        )
        self.assertEqual(status, 0)
        self.assertEqual(output.splitlines(), ["A", "X"])


class PyPIRepositoryTests(unittest.TestCase):
    """Exercise JSON and HTTP handling without network access."""

    @patch("src.dependency_graph.repository.urlopen")
    def test_requirement_parsing_and_cache(self, mock_open):
        """Preserve raw requirements and deduplicate normalized names."""
        requirements = [
            "Some_Package>=2", "other[extra]; extra == 'docs'",
            "some.package<5",
        ]
        data = {"info": {"requires_dist": requirements}}
        mock_open.return_value = io.BytesIO(json.dumps(data).encode())
        repository = PyPIRepository("https://example.com/simple/")
        self.assertEqual(repository.requirements("root"), tuple(requirements))
        self.assertEqual(
            repository.dependencies("root"), ("some-package", "other")
        )
        mock_open.assert_called_once()
        request = mock_open.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.com/pypi/root/json")

    @patch("src.dependency_graph.repository.urlopen")
    def test_http_not_found(self, mock_open):
        """Report a missing package without exposing an HTTP traceback."""
        url = "https://example.com/pypi/missing/json"
        mock_open.side_effect = HTTPError(
            url, HTTPStatus.NOT_FOUND, "Not Found", {}, None
        )
        repository = PyPIRepository("https://example.com")
        with self.assertRaisesRegex(RepositoryError, "was not found"):
            repository.dependencies("missing")


if __name__ == "__main__":
    unittest.main()
