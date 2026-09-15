from dataclasses import dataclass

from fraudguard.training.evaluation import Evaluation


@dataclass(frozen=True, slots=True)
class QualityGate:
    passed: bool
    reasons: tuple[str, ...]


def compare_to_baseline(candidate: Evaluation, baseline: Evaluation) -> QualityGate:
    reasons: list[str] = []
    if candidate.pr_auc < baseline.pr_auc:
        reasons.append("PR-AUC did not meet logistic baseline")
    if candidate.recall_at_1pct_fpr < baseline.recall_at_1pct_fpr:
        reasons.append("recall at 1% FPR did not meet logistic baseline")
    return QualityGate(not reasons, tuple(reasons))
