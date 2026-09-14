"""Print a lightweight manifest-derived profile of canonical historical data."""

import argparse
from pathlib import Path

from fraudguard.data.manifest import build_manifest
from fraudguard.data.storage import read_canonical_parquet


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile canonical FraudGuard historical data.")
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    rows = read_canonical_parquet(args.input)
    print(build_manifest(rows, dataset_name="profile", dataset_version="local").to_json(), end="")


if __name__ == "__main__":
    main()
