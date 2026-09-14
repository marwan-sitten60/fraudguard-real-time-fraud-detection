from dataclasses import dataclass
from math import isfinite

from fraudguard.domain.entities import Prediction, RuleResult
from fraudguard.domain.enums import Decision


@dataclass(frozen=True)
class ThresholdDecisionPolicy:
    review_threshold: float
    block_threshold: float

    def __post_init__(self) -> None:
        if not 0 <= self.review_threshold < self.block_threshold <= 1:
            raise ValueError("expected 0 <= review < block <= 1")

    def decide(self, prediction: Prediction, rules: RuleResult) -> Decision:
        score = prediction.risk_score
        if not isfinite(score) or not 0 <= score <= 1:
            raise ValueError("invalid model score")
        if score >= self.block_threshold:
            return Decision.BLOCK
        if score >= self.review_threshold:
            return Decision.REVIEW
        return Decision.APPROVE
