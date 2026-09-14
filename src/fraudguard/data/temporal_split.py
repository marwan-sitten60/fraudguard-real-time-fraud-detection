from dataclasses import dataclass
from datetime import datetime

from fraudguard.data.manifest import DatasetManifest, build_manifest
from fraudguard.data.schemas import HistoricalTransaction
from fraudguard.data.validation import DataValidationError, validate_historical_transactions


@dataclass(frozen=True, slots=True)
class TemporalSplitConfig:
    """Rows before train_end are train; [train_end, validation_end) are validation."""

    train_end: datetime
    validation_end: datetime

    def __post_init__(self) -> None:
        if self.train_end.tzinfo is None or self.validation_end.tzinfo is None:
            raise ValueError("split boundaries must be timezone-aware")
        if self.train_end >= self.validation_end:
            raise ValueError("train_end must be before validation_end")


@dataclass(frozen=True, slots=True)
class TemporalSplits:
    train: list[HistoricalTransaction]
    validation: list[HistoricalTransaction]
    test: list[HistoricalTransaction]


def temporal_split(
    rows: list[HistoricalTransaction], config: TemporalSplitConfig
) -> TemporalSplits:
    validate_historical_transactions(rows)
    train = [row for row in rows if row.event_time < config.train_end]
    validation = [row for row in rows if config.train_end <= row.event_time < config.validation_end]
    test = [row for row in rows if row.event_time >= config.validation_end]
    splits = TemporalSplits(train=train, validation=validation, test=test)
    validate_temporal_splits(splits)
    return splits


def validate_temporal_splits(splits: TemporalSplits) -> None:
    groups = (splits.train, splits.validation, splits.test)
    if any(not group for group in groups):
        raise DataValidationError(["train, validation, and test splits must all be non-empty"])
    all_ids = [row.transaction_id for group in groups for row in group]
    if len(all_ids) != len(set(all_ids)):
        raise DataValidationError(["transaction IDs overlap across temporal splits"])
    if max(row.event_time for row in splits.train) >= min(
        row.event_time for row in splits.validation
    ):
        raise DataValidationError(["train and validation event times overlap"])
    if max(row.event_time for row in splits.validation) >= min(
        row.event_time for row in splits.test
    ):
        raise DataValidationError(["validation and test event times overlap"])


def split_manifests(splits: TemporalSplits, dataset_version: str) -> dict[str, DatasetManifest]:
    return {
        name: build_manifest(
            rows, dataset_name=f"fraudguard-{name}", dataset_version=dataset_version
        )
        for name, rows in (
            ("train", splits.train),
            ("validation", splits.validation),
            ("test", splits.test),
        )
    }
