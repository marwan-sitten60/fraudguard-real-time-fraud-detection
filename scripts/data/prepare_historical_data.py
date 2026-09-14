"""Canonicalize one handbook input and create its dataset manifest."""

import argparse
from pathlib import Path

from fraudguard.data.pipeline import prepare_historical_dataset


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare one Fraud Detection Handbook CSV or pickle."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--interim", type=Path, default=Path("data/interim/handbook.parquet"))
    parser.add_argument(
        "--manifest", type=Path, default=Path("data/interim/handbook.manifest.json")
    )
    parser.add_argument("--dataset-version", default="phase2-v1")
    parser.add_argument("--source-revision", default="main")
    args = parser.parse_args()
    manifest = prepare_historical_dataset(
        args.input,
        interim_path=args.interim,
        manifest_path=args.manifest,
        dataset_version=args.dataset_version,
        source_version=args.source_revision,
    )
    print(manifest.to_json(), end="")


if __name__ == "__main__":
    main()
