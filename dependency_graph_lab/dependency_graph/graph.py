from collections.abc import Callable


Graph = dict[str, tuple[str, ...]]


def build_graph(root: str, dependencies: Callable[[str], tuple[str, ...]], max_depth: int) -> Graph:
    graph: Graph = {}
    visited_with_depth: dict[str, int] = {}

    def visit(package: str, remaining: int) -> None:
        # A later, shorter path may leave enough depth to discover additional edges.
        if remaining <= visited_with_depth.get(package, -1):
            return
        visited_with_depth[package] = remaining
        graph.setdefault(package, ())
        if remaining == 0:
            return

        children = dependencies(package)
        graph[package] = children
        for child in children:
            visit(child, remaining - 1)

    visit(root, max_depth)
    return graph


def reverse_edges(graph: Graph) -> Graph:
    parents: dict[str, list[str]] = {package: [] for package in graph}
    for package, dependencies in graph.items():
        for dependency in dependencies:
            parents[dependency].append(package)
    return {package: tuple(names) for package, names in parents.items()}
