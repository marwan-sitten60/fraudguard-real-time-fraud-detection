"""Offline-only baseline training. It does not integrate with API model loading."""

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import Any

import joblib
import mlflow
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from fraudguard.data.storage import read_canonical_parquet
from fraudguard.features.offline.contract import FEATURE_CONTRACT_VERSION, FEATURE_NAMES
from fraudguard.features.offline.historical import build_point_in_time_features
from fraudguard.training.evaluation import Evaluation, evaluate, select_threshold
from fraudguard.training.quality_gate import QualityGate, compare_to_baseline

DATASET_VERSION = "fraudguard-handbook-baseline-v1"


@dataclass(frozen=True, slots=True)
class TrainingResult:
    model_type: str
    validation: Evaluation
    test: Evaluation
    threshold: float
    inference_p50_ms: float
    inference_p95_ms: float
    inference_p99_ms: float
    gate: QualityGate | None
    run_id: str


def _split(frame: pd.DataFrame, ids: set[str]) -> tuple[np.ndarray, np.ndarray]:
    selected = frame[frame["transaction_id"].isin(ids)]
    return selected[list(FEATURE_NAMES)].to_numpy(dtype=float), selected["fraud_label"].to_numpy(
        dtype=int
    )


def _model(model_type: str, scale_pos_weight: float, seed: int) -> Any:
    if model_type == "logistic":
        return Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(max_iter=500, class_weight="balanced", random_state=seed),
                ),
            ]
        )
    if model_type == "xgboost":
        return XGBClassifier(
            n_estimators=180,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            random_state=seed,
            n_jobs=4,
            eval_metric="logloss",
        )
    raise ValueError("model_type must be logistic or xgboost")


def train_baseline(
    *,
    data_directory: Path,
    model_type: str,
    seed: int,
    tracking_uri: str,
    output_directory: Path,
    logistic_baseline: Evaluation | None = None,
) -> TrainingResult:
    rows_by_split = {
        name: read_canonical_parquet(data_directory / f"{name}.parquet")
        for name in ("train", "validation", "test")
    }
    all_rows = [row for name in ("train", "validation", "test") for row in rows_by_split[name]]
    features = build_point_in_time_features(all_rows)
    ids = {name: {row.transaction_id for row in rows} for name, rows in rows_by_split.items()}
    x_train, y_train = _split(features, ids["train"])
    x_validation, y_validation = _split(features, ids["validation"])
    x_test, y_test = _split(features, ids["test"])
    weight = float((y_train == 0).sum() / max(1, (y_train == 1).sum()))
    model = _model(model_type, weight, seed)
    model.fit(x_train, y_train)
    validation_scores = model.predict_proba(x_validation)[:, 1]
    threshold = select_threshold(y_validation, validation_scores)
    validation = evaluate(y_validation, validation_scores, threshold)
    test_scores = model.predict_proba(x_test)[:, 1]
    test = evaluate(y_test, test_scores, threshold)
    timings = []
    for row in x_test[:1000]:
        start = perf_counter_ns()
        model.predict_proba(row.reshape(1, -1))
        timings.append((perf_counter_ns() - start) / 1_000_000)
    gate = None if logistic_baseline is None else compare_to_baseline(validation, logistic_baseline)
    output_directory.mkdir(parents=True, exist_ok=True)
    artifact = output_directory / f"{model_type}-candidate.joblib"
    joblib.dump(model, artifact)
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("FraudGuard-Baseline")
    with mlflow.start_run() as run:
        mlflow.log_params(
            {
                "model_type": model_type,
                "dataset_version": DATASET_VERSION,
                "feature_contract_version": FEATURE_CONTRACT_VERSION,
                "random_seed": seed,
                "imbalance_strategy": "balanced/logistic or scale_pos_weight/xgboost",
                "scale_pos_weight": weight,
            }
        )
        mlflow.log_metrics(
            {
                f"validation_{key}": value
                for key, value in validation.as_dict().items()
                if isinstance(value, (int, float))
            }
        )
        mlflow.log_metrics(
            {
                f"test_{key}": value
                for key, value in test.as_dict().items()
                if isinstance(value, (int, float))
            }
        )
        mlflow.log_artifact(str(artifact))
        mlflow.log_dict(
            {
                "features": list(FEATURE_NAMES),
                "feature_contract_version": FEATURE_CONTRACT_VERSION,
                "validation": validation.as_dict(),
                "test": test.as_dict(),
                "threshold": threshold,
            },
            "evaluation.json",
        )
        run_id = run.info.run_id
    p50, p95, p99 = (float(np.percentile(timings, quantile)) for quantile in (50, 95, 99))
    return TrainingResult(model_type, validation, test, threshold, p50, p95, p99, gate, run_id)
