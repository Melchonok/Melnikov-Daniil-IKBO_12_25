"""Read package metadata from PyPI or a local test graph."""

import json
import re
from http import HTTPStatus
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .config import PYPI_NAME_PATTERN, TEST_NAME, normalize_name
from .graph import Graph


REQUEST_TIMEOUT = 10
REQUIREMENT_NAME = re.compile(
    rf"\s*({PYPI_NAME_PATTERN})(?=\s|[\[(@<>=!~;]|$)"
)


class RepositoryError(Exception):
    """Report an unavailable repository or invalid package metadata."""


def fetch_metadata(package: str, url: str) -> object:
    """Read JSON from the package endpoint and report HTTP failures."""
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return json.load(response)
    except HTTPError as error:
        if error.code == HTTPStatus.NOT_FOUND:
            message = f"package {package!r} was not found at {url}"
        else:
            message = f"could not fetch {url}: HTTP {error.code}"
        raise RepositoryError(message) from error
    except (OSError, HTTPException) as error:
        raise RepositoryError(f"could not fetch {url}: {error}") from error
    except (ValueError, RecursionError) as error:
        message = f"invalid JSON response from {url}: {error}"
        raise RepositoryError(message) from error


def parse_requirements(
    data: object, url: str
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return the declared requirements and deduplicated package names."""
    info = data.get("info") if isinstance(data, dict) else None
    if not isinstance(info, dict) or "requires_dist" not in info:
        raise RepositoryError(f"missing info.requires_dist from {url}")
    requirements = info["requires_dist"]
    if requirements is None:
        return (), ()
    if not isinstance(requirements, list):
        raise RepositoryError(f"invalid info.requires_dist from {url}")

    names: list[str] = []
    for requirement in requirements:
        if not isinstance(requirement, str):
            raise RepositoryError(f"invalid requirement from {url}")
        match = REQUIREMENT_NAME.match(requirement)
        if match is None:
            raise RepositoryError(f"invalid requirement from {url}")
        names.append(normalize_name(match[1]))

    return tuple(requirements), tuple(dict.fromkeys(names))


class PyPIRepository:
    """Load and cache release metadata from a PyPI-compatible JSON API."""

    def __init__(self, base_url: str) -> None:
        """Normalize the repository base and initialize the package cache."""
        parts = urlsplit(base_url)
        path = parts.path.rstrip("/").removesuffix("/simple")
        if not path.endswith("/pypi"):
            path += "/pypi"
        self.base_url = parts._replace(path=path).geturl()
        self._requirements: dict[str, tuple[str, ...]] = {}
        self._dependencies: dict[str, tuple[str, ...]] = {}

    def requirements(self, package: str) -> tuple[str, ...]:
        """Fetch the original requirement strings for a package."""
        if package not in self._requirements:
            url = f"{self.base_url}/{package}/json"
            data = fetch_metadata(package, url)
            requirements, dependencies = parse_requirements(data, url)
            self._requirements[package] = requirements
            self._dependencies[package] = dependencies
        return self._requirements[package]

    def dependencies(self, package: str) -> tuple[str, ...]:
        """Return the normalized dependency names for graph traversal."""
        self.requirements(package)
        return self._dependencies[package]


def read_test_json(path: str) -> object:
    """Read the UTF-8 test repository and report errors with its path."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, RecursionError) as error:
        message = f"could not read test repository {path!r}: {error}"
        raise RepositoryError(message) from error


def parse_test_graph(data: object) -> Graph:
    """Validate package names, dependency lists, and their targets."""
    if not isinstance(data, dict):
        raise RepositoryError("test repository must be a JSON object")

    graph: Graph = {}
    for package, dependencies in data.items():
        if not TEST_NAME.fullmatch(package):
            raise RepositoryError(f"invalid test package name: {package!r}")
        if not isinstance(dependencies, list) or not all(
            isinstance(name, str) and TEST_NAME.fullmatch(name)
            for name in dependencies
        ):
            message = f"dependencies of {package!r} must use names A-Z"
            raise RepositoryError(message)
        graph[package] = tuple(dict.fromkeys(dependencies))

    validate_test_links(graph)
    return graph


def validate_test_links(graph: Graph) -> None:
    """Check that each dependency points to a declared package."""
    for package, dependencies in graph.items():
        for dependency in dependencies:
            if dependency not in graph:
                message = (
                    f"dependency {dependency!r} of {package!r} "
                    "has no entry in the test repository"
                )
                raise RepositoryError(message)


class TestRepository:
    """Load the complete graph from a local test JSON file."""

    def __init__(self, path: str) -> None:
        """Read and validate the test file before any traversal."""
        self.graph = parse_test_graph(read_test_json(path))

    def requirements(self, package: str) -> tuple[str, ...]:
        """Return the direct dependencies of a test package."""
        if package not in self.graph:
            message = (
                f"package {package!r} was not found in the test repository"
            )
            raise RepositoryError(message)
        return self.graph[package]

    dependencies = requirements
