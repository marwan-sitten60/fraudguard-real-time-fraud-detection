from enum import IntEnum


class FraudLabel(IntEnum):
    """Ground-truth outcome, never a feature available at authorization time."""

    LEGITIMATE = 0
    FRAUD = 1
