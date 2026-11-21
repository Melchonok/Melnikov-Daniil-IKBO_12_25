from .graph import Graph


def plantuml(graph: Graph) -> str:
    aliases = {name: f"p{index}" for index, name in enumerate(graph)}
    lines = ["@startuml", "left to right direction"]
    for name, alias in aliases.items():
        lines.append(f'component "{name}" as {alias}')
    for name, dependencies in graph.items():
        for dependency in dependencies:
            lines.append(f"{aliases[name]} --> {aliases[dependency]}")
    lines.append("@enduml")
    return "\n".join(lines)


def ascii_tree(graph: Graph, root: str, max_depth: int) -> str:
    lines = [root]
    path = {root}
    expanded_with_depth = {root: max_depth}

    def render_children(package: str, prefix: str, remaining: int) -> None:
        if remaining == 0:
            return
        children = graph[package]
        child_depth = remaining - 1
        for index, child in enumerate(children):
            last = index == len(children) - 1
            branch = "`-- " if last else "|-- "
            line = f"{prefix}{branch}{child}"
            if child in path:
                lines.append(f"{line} (cycle)")
                continue
            if child_depth <= expanded_with_depth.get(child, -1):
                lines.append(f"{line} (shared)")
                continue

            lines.append(line)
            expanded_with_depth[child] = child_depth
            path.add(child)
            render_children(child, prefix + ("    " if last else "|   "), child_depth)
            path.remove(child)

    render_children(root, "", max_depth)
    return "\n".join(lines)
