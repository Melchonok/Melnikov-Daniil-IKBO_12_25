"""Run the CLI and display the selected result."""

import sys

from .config import Config, make_parser, print_config, validate_args
from .graph import Graph, build_graph, reverse_edges
from .render import ascii_tree, plantuml
from .repository import PyPIRepository, RepositoryError, TestRepository


def print_graph(config: Config, graph: Graph) -> None:
    """Print the graph, adjacency list, or list of reverse dependencies."""
    if config.mode == "graph":
        for name, children in graph.items():
            print(f"{name} -> {', '.join(children) or '-'}")
    elif config.mode == "reverse":
        packages = [name for name in graph if name != config.package]
        print("\n".join(packages) if packages else "No reverse dependencies.")
    else:
        print(plantuml(graph))


def analyze(config: Config) -> None:
    """Validate the root even at depth zero, then render the selected result."""
    if config.test:
        repository = TestRepository(config.repo)
    else:
        repository = PyPIRepository(config.repo)

    requirements = repository.requirements(config.package)
    if config.mode == "direct":
        print("\n".join(requirements) or "No direct dependencies.")
        return

    dependencies = repository.dependencies
    if config.mode == "reverse" and isinstance(repository, TestRepository):
        dependencies = reverse_edges(repository.graph).__getitem__
    graph = build_graph(config.package, dependencies, config.max_depth)
    tree = None
    if config.ascii:
        tree = ascii_tree(graph, config.package, config.max_depth)

    print_graph(config, graph)
    if tree is not None:
        print(f"\n{tree}")


def main(argv: list[str] | None = None) -> int:
    """Run one command and return a process exit status."""
    parser = make_parser()
    config = validate_args(parser, parser.parse_args(argv))
    if config.mode == "config":
        print_config(config)
        return 0

    try:
        analyze(config)
    except RepositoryError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except RecursionError:
        print(
            "error: graph exceeds Python's recursion limit; "
            "use a smaller --max-depth",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
