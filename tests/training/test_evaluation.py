import numpy as np

from fraudguard.training.evaluation import select_threshold
from fraudguard.training.quality_gate import compare_to_baseline


def test_threshold_does_not_exceed_validation_fpr_limit() -> None:
    labels = np.array([0, 0, 0, 1, 1])
    scores = np.array([0.1, 0.2, 0.8, 0.9, 1.0])
    assert select_threshold(labels, scores, maximum_fpr=0.34) >= 0.8


def test_quality_gate_rejects_weaker_candidate() -> None:
    from fraudguard.training.evaluation import Evaluation

    baseline = Evaluation(0.5, 0.8, 0.4, 0.5, 0.4, 0.4, 0.5, 0.5, 0.01, 1, 2)
    candidate = Evaluation(0.4, 0.9, 0.5, 0.6, 0.5, 0.5, 0.4, 0.5, 0.01, 1, 2)
    assert not compare_to_baseline(candidate, baseline).passed
