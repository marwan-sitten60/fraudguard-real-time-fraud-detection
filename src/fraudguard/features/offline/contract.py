"""Versioned, offline-only feature contract for historical model development."""

from dataclasses import dataclass

FEATURE_CONTRACT_VERSION = "fraud-features-v1"


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    name: str
    dtype: str
    meaning: str
    source: str
    kind: str
    point_in_time_rule: str


PRIOR_ONLY = "Computed before this row is added to event-time ordered state."
FEATURES = (
    FeatureDefinition(
        "amount", "float64", "Transaction amount", "amount", "transaction", "Current row"
    ),
    FeatureDefinition(
        "hour_of_day", "int8", "UTC event hour", "event_time", "transaction", "Current row"
    ),
    FeatureDefinition(
        "day_of_week", "int8", "UTC weekday, Monday=0", "event_time", "transaction", "Current row"
    ),
    FeatureDefinition(
        "is_weekend", "int8", "UTC Saturday/Sunday flag", "event_time", "transaction", "Current row"
    ),
    FeatureDefinition(
        "customer_prior_count",
        "int64",
        "Earlier customer transaction count",
        "customer_id",
        "historical",
        PRIOR_ONLY,
    ),
    FeatureDefinition(
        "customer_prior_avg_amount",
        "float64",
        "Earlier customer mean amount",
        "customer_id, amount",
        "historical",
        PRIOR_ONLY,
    ),
    FeatureDefinition(
        "customer_prior_std_amount",
        "float64",
        "Earlier customer amount standard deviation",
        "customer_id, amount",
        "historical",
        PRIOR_ONLY,
    ),
    FeatureDefinition(
        "customer_prior_max_amount",
        "float64",
        "Earlier customer maximum amount",
        "customer_id, amount",
        "historical",
        PRIOR_ONLY,
    ),
    FeatureDefinition(
        "amount_to_customer_prior_avg",
        "float64",
        "Amount divided by earlier customer mean",
        "amount, customer_id",
        "historical",
        PRIOR_ONLY,
    ),
    FeatureDefinition(
        "seconds_since_customer_prior_tx",
        "float64",
        "Elapsed seconds since earlier customer transaction",
        "customer_id, event_time",
        "historical",
        PRIOR_ONLY,
    ),
    FeatureDefinition(
        "merchant_prior_count",
        "int64",
        "Earlier merchant transaction count",
        "merchant_id",
        "historical",
        PRIOR_ONLY,
    ),
    FeatureDefinition(
        "merchant_prior_avg_amount",
        "float64",
        "Earlier merchant mean amount",
        "merchant_id, amount",
        "historical",
        PRIOR_ONLY,
    ),
    FeatureDefinition(
        "merchant_prior_fraud_count",
        "int64",
        "Earlier merchant known fraud count",
        "merchant_id, fraud_label",
        "historical",
        PRIOR_ONLY,
    ),
    FeatureDefinition(
        "merchant_prior_fraud_rate",
        "float64",
        "Earlier merchant known fraud rate",
        "merchant_id, fraud_label",
        "historical",
        PRIOR_ONLY,
    ),
)

FEATURE_NAMES = tuple(item.name for item in FEATURES)
