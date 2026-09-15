"""Offline metrics and validation-only threshold selection."""

from dataclasses import asdict, dataclass

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


@dataclass(frozen=True, slots=True)
class Evaluation:
    pr_auc: float
    roc_auc: float
    precision: float
    recall: float
    f1: float
    recall_at_0_5pct_fpr: float
    recall_at_1pct_fpr: float
    threshold: float
    false_positive_rate: float
    fraud_detected: int
    legitimate_flagged: int

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _recall_at_fpr(labels: np.ndarray, scores: np.ndarray, limit: float) -> float:
    order = np.argsort(scores)[::-1]
    ordered = labels[order]
    cumulative_positive = np.cumsum(ordered)
    cumulative_negative = np.cumsum(1 - ordered)
    total_positive, total_negative = ordered.sum(), (1 - ordered).sum()
    valid = np.where(cumulative_negative / total_negative <= limit)[0]
    return float(cumulative_positive[valid[-1]] / total_positive) if len(valid) else 0.0


def evaluate(labels: np.ndarray, scores: np.ndarray, threshold: float) -> Evaluation:
    predicted = scores >= threshold
    tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
    return Evaluation(
        pr_auc=float(average_precision_score(labels, scores)),
        roc_auc=float(roc_auc_score(labels, scores)),
        precision=float(precision_score(labels, predicted, zero_division=0)),
        recall=float(recall_score(labels, predicted, zero_division=0)),
        f1=float(f1_score(labels, predicted, zero_division=0)),
        recall_at_0_5pct_fpr=_recall_at_fpr(labels, scores, 0.005),
        recall_at_1pct_fpr=_recall_at_fpr(labels, scores, 0.01),
        threshold=float(threshold),
        false_positive_rate=float(fp / (fp + tn)),
        fraud_detected=int(tp),
        legitimate_flagged=int(fp),
    )


def select_threshold(labels: np.ndarray, scores: np.ndarray, maximum_fpr: float = 0.01) -> float:
    """Choose the validation threshold with highest recall without exceeding FPR."""
    order = np.argsort(scores)[::-1]
    ordered_scores, ordered_labels = scores[order], labels[order]
    cumulative_negative = np.cumsum(1 - ordered_labels)
    total_negative = (1 - ordered_labels).sum()
    valid = np.where(cumulative_negative / total_negative <= maximum_fpr)[0]
    return float(ordered_scores[valid[-1]]) if len(valid) else float(ordered_scores[0])
