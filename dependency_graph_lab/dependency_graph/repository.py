import json
import re
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .config import PYPI_NAME_PATTERN, TEST_NAME, normalize_name


REQUIREMENT_NAME = re.compile(rf"\s*({PYPI_NAME_PATTERN})(?=\s|[\[(@<>=!~;]|$)")


class RepositoryError(Exception):
    pass


class PyPIRepository:
    def __init__(self, base_url: str) -> None:
        parts = urlsplit(base_url)
        path = parts.path.rstrip("/").removesuffix("/simple")
        if not path.endswith("/pypi"):
            path += "/pypi"
        self.base_url = parts._replace(path=path).geturl()
        self._requirements: dict[str, tuple[str, ...]] = {}
        self._dependencies: dict[str, tuple[str, ...]] = {}

    def requirements(self, package: str) -> tuple[str, ...]:
        if package in self._requirements:
            return self._requirements[package]

        url = f"{self.base_url}/{package}/json"
        request = Request(url, headers={"Accept": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                data = json.load(response)
        except HTTPError as error:
            if error.code == 404:
                raise RepositoryError(f"package {package!r} was not found at {url}") from error
            raise RepositoryError(f"could not fetch {url}: HTTP {error.code}") from error
        except (OSError, HTTPException) as error:
            raise RepositoryError(f"could not fetch {url}: {error}") from error
        except (ValueError, RecursionError) as error:
            raise RepositoryError(f"invalid JSON response from {url}: {error}") from error

        info = data.get("info") if isinstance(data, dict) else None
        if not isinstance(info, dict) or "requires_dist" not in info:
            raise RepositoryError(f"response from {url} is missing info.requires_dist")
        requirements = info["requires_dist"]
        if requirements is None:
            requirements = []
        if not isinstance(requirements, list):
            raise RepositoryError(f"invalid info.requires_dist in the response from {url}")

        names = []
        for requirement in requirements:
            match = REQUIREMENT_NAME.match(requirement) if isinstance(requirement, str) else None
            if match is None:
                raise RepositoryError(f"invalid requirement in info.requires_dist from {url}")
            names.append(normalize_name(match[1]))

        self._requirements[package] = tuple(requirements)
        self._dependencies[package] = tuple(dict.fromkeys(names))
        return self._requirements[package]

    def dependencies(self, package: str) -> tuple[str, ...]:
        self.requirements(package)
        return self._dependencies[package]


class TestRepository:
    def __init__(self, path: str) -> None:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError, RecursionError) as error:
            raise RepositoryError(f"could not read test repository {path!r}: {error}") from error

        if not isinstance(data, dict):
            raise RepositoryError("test repository must be a JSON object of packages and dependency lists")

        self.graph: dict[str, tuple[str, ...]] = {}
        for package, dependencies in data.items():
            if not TEST_NAME.fullmatch(package):
                raise RepositoryError(f"invalid test package name: {package!r}")
            if not isinstance(dependencies, list) or not all(
                isinstance(name, str) and TEST_NAME.fullmatch(name) for name in dependencies
            ):
                raise RepositoryError(f"dependencies of {package!r} must be a list of uppercase package names")
            self.graph[package] = tuple(dict.fromkeys(dependencies))

        for package, dependencies in self.graph.items():
            for dependency in dependencies:
                if dependency not in self.graph:
                    raise RepositoryError(f"dependency {dependency!r} of {package!r} has no entry in the test repository")

    def requirements(self, package: str) -> tuple[str, ...]:
        if package not in self.graph:
            raise RepositoryError(f"package {package!r} was not found in the test repository")
        return self.graph[package]

    dependencies = requirements
