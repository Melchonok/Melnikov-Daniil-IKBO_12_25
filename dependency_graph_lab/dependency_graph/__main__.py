import sys

from .config import make_parser, print_config, validate_args
from .graph import build_graph, reverse_edges
from .render import ascii_tree, plantuml
from .repository import PyPIRepository, RepositoryError, TestRepository


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--show-config", action="store_true", help="print CLI settings as key=value")
    modes.add_argument("--direct", action="store_true", help="print all declared direct requirements")
    modes.add_argument("--graph", action="store_true", help="print the graph as an adjacency list")
    modes.add_argument("--reverse", action="store_true", help="print packages that depend on the root (test mode)")
    args = parser.parse_args(argv)
    config = validate_args(parser, args)

    if args.reverse and not config.test:
        parser.error("--reverse requires --test and a complete test repository")
    if args.direct and config.ascii:
        parser.error("--ascii cannot be combined with --direct")
    if args.show_config:
        print_config(config)
        return 0

    try:
        repository = TestRepository(config.repo) if config.test else PyPIRepository(config.repo)

        # Check that the root exists even when the traversal depth is zero.
        requirements = repository.requirements(config.package)
        if args.direct:
            print("\n".join(requirements) if requirements else "No direct dependencies.")
            return 0

        dependencies = repository.dependencies
        if args.reverse and isinstance(repository, TestRepository):
            dependencies = reverse_edges(repository.graph).__getitem__
        graph = build_graph(config.package, dependencies, config.max_depth)
        tree = ascii_tree(graph, config.package, config.max_depth) if config.ascii else None
    except RepositoryError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except RecursionError:
        print("error: graph exceeds Python's recursion limit; use a smaller --max-depth", file=sys.stderr)
        return 1

    if args.graph:
        for name, children in graph.items():
            print(f"{name} -> {', '.join(children) or '-'}")
    elif args.reverse:
        packages = [name for name in graph if name != config.package]
        print("\n".join(packages) if packages else "No reverse dependencies.")
    else:
        print(plantuml(graph))
    if tree is not None:
        print(f"\n{tree}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
