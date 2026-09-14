import csv
from collections.abc import Iterable
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]

from fraudguard.data.adapters.fraud_handbook import (
    HandbookSchemaError,
    handbook_row_to_canonical,
    validate_handbook_columns,
)
from fraudguard.data.manifest import DatasetManifest, build_manifest, write_manifest
from fraudguard.data.schemas import HistoricalTransaction
from fraudguard.data.storage import write_canonical_parquet
from fraudguard.data.temporal_split import (
    TemporalSplitConfig,
    TemporalSplits,
    split_manifests,
    temporal_split,
)


def load_handbook_rows(path: Path) -> list[HistoricalTransaction]:
    """Read trusted handbook CSV/pickle data into canonical records.

    A directory is read as sorted daily pickle files. Pickle input must come
    from the trusted Fraud Detection Handbook source because pickle is unsafe
    for untrusted content.
    """
    paths = sorted(path.glob("*.pkl")) if path.is_dir() else [path]
    if not paths:
        raise HandbookSchemaError("input directory does not contain handbook pickle files")

    rows: list[HistoricalTransaction] = []
    errors: list[str] = []
    for source_path in paths:
        if source_path.suffix == ".csv":
            with source_path.open(newline="", encoding="utf-8") as source:
                reader = csv.DictReader(source)
                validate_handbook_columns(reader.fieldnames or [])
                raw_rows: Iterable[dict[str, object]] = list(reader)
        elif source_path.suffix in {".pkl", ".pickle"}:
            dataframe = pd.read_pickle(source_path)
            validate_handbook_columns(list(dataframe.columns))
            raw_rows = dataframe.to_dict(orient="records")
        else:
            raise HandbookSchemaError("supported handbook inputs are .csv and .pkl")

        for index, row in enumerate(raw_rows):
            try:
                rows.append(handbook_row_to_canonical(row))
            except HandbookSchemaError as exc:
                errors.append(f"{source_path.name} row {index}: {exc}")
    if errors:
        raise HandbookSchemaError("; ".join(errors))
    return rows


def prepare_historical_dataset(
    raw_path: Path,
    *,
    interim_path: Path,
    manifest_path: Path,
    dataset_version: str,
    source_version: str = "unspecified",
) -> DatasetManifest:
    rows = load_handbook_rows(raw_path)
    manifest = build_manifest(
        rows,
        dataset_name="fraud-detection-handbook",
        dataset_version=dataset_version,
        source_version=source_version,
    )
    write_canonical_parquet(rows, interim_path)
    write_manifest(manifest, manifest_path)
    return manifest


def create_temporal_splits(
    rows: list[HistoricalTransaction],
    *,
    config: TemporalSplitConfig,
    output_directory: Path,
    dataset_version: str,
) -> TemporalSplits:
    splits = temporal_split(rows, config)
    manifests = split_manifests(splits, dataset_version)
    for name, subset in (
        ("train", splits.train),
        ("validation", splits.validation),
        ("test", splits.test),
    ):
        write_canonical_parquet(subset, output_directory / f"{name}.parquet")
        write_manifest(manifests[name], output_directory / f"{name}.manifest.json")
    return splits
