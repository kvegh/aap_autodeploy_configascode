#!/usr/bin/env python3
"""Increment the project version once per commit after the initial baseline."""

import argparse
from pathlib import Path
import re


def next_version(value: str, feature: bool = False) -> str:
    """Increment patch, or increment minor and reset patch for a feature."""
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value) is None:
        raise ValueError("VERSION must contain major.minor.patch")
    major, minor, patch = map(int, value.split("."))
    if feature:
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feature",
        action="store_true",
        help="increment minor and reset patch instead of incrementing patch",
    )
    args = parser.parse_args()
    version_file = Path(__file__).resolve().parents[1] / "VERSION"
    try:
        version = next_version(version_file.read_text().strip(), args.feature)
        version_file.write_text(version + "\n")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(version)


if __name__ == "__main__":
    main()
