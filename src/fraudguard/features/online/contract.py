"""Production-safe online feature contract; intentionally excludes labels."""

ONLINE_FEATURE_CONTRACT_VERSION = "fraud-online-features-v1"
CUSTOMER_FEATURES = (
    "customer_prior_transaction_count",
    "customer_prior_average_amount",
    "customer_prior_std_amount",
    "customer_prior_max_amount",
    "seconds_since_previous_transaction",
)
MERCHANT_FEATURES = ("merchant_prior_transaction_count", "merchant_prior_average_amount")
TRANSACTION_FEATURES = ("amount", "hour_of_day", "day_of_week", "weekend_indicator")
DERIVED_FEATURES = ("amount_to_customer_prior_average",)
ONLINE_FEATURE_NAMES = (
    TRANSACTION_FEATURES + CUSTOMER_FEATURES + MERCHANT_FEATURES + DERIVED_FEATURES
)
