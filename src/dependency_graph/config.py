"""Parse and validate the options for dependency analysis."""

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


DEFAULT_REPOSITORY = "https://pypi.org"
DEFAULT_DEPTH = 2
PYPI_NAME_PATTERN = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
PYPI_NAME = re.compile(PYPI_NAME_PATTERN)
TEST_NAME = re.compile(r"[A-Z]+")


@dataclass(frozen=True)
class Config:
    """Store all validated options for one command."""

    package: str
    repo: str
    test: bool
    ascii: bool
    max_depth: int
    mode: str


def normalize_name(name: str) -> str:
    """Normalize a Python distribution name for use in a repository URL."""
    return re.sub(r"[-_.]+", "-", name).lower()


def nonnegative_depth(value: str) -> int:
    """Parse the maximum depth and reject negative or malformed values."""
    message = "expected a nonnegative integer"
    try:
        depth = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(message) from None
    if depth < 0:
        raise argparse.ArgumentTypeError(message)
    return depth


def validate_test_options(
    parser: argparse.ArgumentParser, package: str, repo: str | None
) -> str:
    """Validate the test package name and return an existing file path."""
    if not TEST_NAME.fullmatch(package):
        parser.error("--package in test mode must use only letters A-Z")
    if not repo:
        parser.error("--repo must specify a JSON file in test mode")
    try:
        is_file = Path(repo).is_file()
    except (OSError, ValueError):
        is_file = False
    if not is_file:
        parser.error(f"--repo is not an existing file: {repo!r}")
    return repo


def is_repository_url(url: str) -> bool:
    """Check the HTTP scheme, host, and optional numeric port."""
    if re.search(r"[\s\x00-\x1f\x7f?#]", url):
        return False
    try:
        parts = urlsplit(url)
        _ = parts.port
        return parts.scheme in {"http", "https"} and bool(parts.hostname)
    except ValueError:
        return False


def validate_args(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> Config:
    """Resolve defaults and reject incompatible options."""
    package = args.package
    if args.test:
        repo = validate_test_options(parser, package, args.repo)
    else:
        if not PYPI_NAME.fullmatch(package):
            parser.error("--package must be a valid Python distribution name")
        repo = DEFAULT_REPOSITORY if args.repo is None else args.repo
        if not is_repository_url(repo):
            parser.error(
                "--repo must be an HTTP(S) URL without query or fragment"
            )
        package = normalize_name(package)

    if args.mode == "reverse" and not args.test:
        parser.error("--reverse requires --test and a complete test repository")
    if args.mode == "direct" and args.ascii:
        parser.error("--ascii cannot be combined with --direct")
    return Config(
        package, repo, args.test, args.ascii, args.max_depth, args.mode
    )


def add_modes(parser: argparse.ArgumentParser) -> None:
    """Add the mutually exclusive display modes."""
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--show-config", dest="mode", action="store_const", const="config",
        help="print CLI settings as key=value",
    )
    modes.add_argument(
        "--direct", dest="mode", action="store_const", const="direct",
        help="print all declared direct requirements",
    )
    modes.add_argument(
        "--graph", dest="mode", action="store_const", const="graph",
        help="print the graph as an adjacency list",
    )
    modes.add_argument(
        "--reverse", dest="mode", action="store_const", const="reverse",
        help="print packages that depend on the root (test mode)",
    )
    parser.set_defaults(mode="plantuml")


def make_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for all analysis modes."""
    parser = argparse.ArgumentParser(
        description="Analyze declared Python package dependencies.",
        epilog="PyPI graphs include optional and conditional requirements.",
        allow_abbrev=False,
    )
    parser.add_argument("-p", "--package", required=True, help="package name")
    parser.add_argument(
        "-r", "--repo",
        help=f"PyPI URL (default: {DEFAULT_REPOSITORY}) or a test JSON file",
    )
    parser.add_argument(
        "--test", action="store_true", help="read a test repository"
    )
    parser.add_argument(
        "--ascii", action="store_true", help="include an ASCII dependency tree"
    )
    parser.add_argument(
        "-d", "--max-depth", type=nonnegative_depth, default=DEFAULT_DEPTH,
        help=f"maximum edges from the root (default: {DEFAULT_DEPTH})",
    )
    add_modes(parser)
    return parser


def print_config(config: Config) -> None:
    """Print the five settings required by the configuration prototype."""
    print(f"package={config.package}")
    print(f"repo={config.repo}")
    print(f"test={str(config.test).lower()}")
    print(f"ascii={str(config.ascii).lower()}")
    print(f"max_depth={config.max_depth}")
