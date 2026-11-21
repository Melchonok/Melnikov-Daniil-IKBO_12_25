import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


DEFAULT_REPOSITORY = "https://pypi.org"
PYPI_NAME_PATTERN = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
PYPI_NAME = re.compile(PYPI_NAME_PATTERN)
TEST_NAME = re.compile(r"[A-Z]+")


@dataclass(frozen=True)
class Config:
    package: str
    repo: str
    test: bool
    ascii: bool
    max_depth: int


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def nonnegative_depth(value: str) -> int:
    try:
        depth = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("expected a nonnegative integer") from None
    if depth < 0:
        raise argparse.ArgumentTypeError("expected a nonnegative integer")
    return depth


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> Config:
    if args.test:
        if not TEST_NAME.fullmatch(args.package):
            parser.error("--package in test mode must contain only uppercase Latin letters (A-Z)")
        if not args.repo:
            parser.error("--repo must specify a JSON file in test mode")
        repo = args.repo
        try:
            is_file = Path(repo).is_file()
        except (OSError, ValueError):
            is_file = False
        if not is_file:
            parser.error(f"--repo is not an existing file: {repo!r}")
        package = args.package
    else:
        if not PYPI_NAME.fullmatch(args.package):
            parser.error("--package must be a valid Python distribution name")
        repo = DEFAULT_REPOSITORY if args.repo is None else args.repo
        try:
            parts = urlsplit(repo)
            parts.port  # Validate the port when present.
            valid_url = parts.scheme in {"http", "https"} and bool(parts.hostname)
        except ValueError:
            valid_url = False
        if not valid_url or re.search(r"[\s\x00-\x1f\x7f?#]", repo):
            parser.error("--repo must be an HTTP(S) repository URL without a query or fragment")
        package = normalize_name(args.package)

    return Config(package, repo, args.test, args.ascii, args.max_depth)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze declared Python package dependencies.",
        epilog="PyPI graphs include optional and conditional requirements from release metadata.",
        allow_abbrev=False,
    )
    parser.add_argument("-p", "--package", required=True, help="package name")
    parser.add_argument(
        "-r", "--repo",
        help=f"PyPI JSON API base URL (default: {DEFAULT_REPOSITORY}) or a test JSON file",
    )
    parser.add_argument("--test", action="store_true", help="read the graph from a test repository")
    parser.add_argument("--ascii", action="store_true", help="include an ASCII dependency tree")
    parser.add_argument(
        "-d", "--max-depth", type=nonnegative_depth, default=2,
        help="maximum number of edges from the root (default: 2)",
    )
    return parser


def print_config(config: Config) -> None:
    print(f"package={config.package}")
    print(f"repo={config.repo}")
    print(f"test={str(config.test).lower()}")
    print(f"ascii={str(config.ascii).lower()}")
    print(f"max_depth={config.max_depth}")
