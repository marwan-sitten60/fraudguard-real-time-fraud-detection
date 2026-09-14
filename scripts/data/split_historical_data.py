"""Make strict event-time train/validation/test partitions from canonical Parquet."""

import argparse
from datetime import datetime
from pathlib import Path

from fraudguard.data.pipeline import create_temporal_splits
from fraudguard.data.storage import read_canonical_parquet
from fraudguard.data.temporal_split import TemporalSplitConfig


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError(
            "boundary must include a timezone, e.g. 2018-04-02T00:00:00Z"
        )
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Create strict FraudGuard temporal splits.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--train-end", required=True, type=parse_time)
    parser.add_argument("--validation-end", required=True, type=parse_time)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/handbook"))
    parser.add_argument("--dataset-version", default="phase2-v1")
    args = parser.parse_args()
    rows = read_canonical_parquet(args.input)
    splits = create_temporal_splits(
        rows,
        config=TemporalSplitConfig(args.train_end, args.validation_end),
        output_directory=args.output_dir,
        dataset_version=args.dataset_version,
    )
    print(f"train={len(splits.train)} validation={len(splits.validation)} test={len(splits.test)}")


if __name__ == "__main__":
    main()
