class ServingUnavailable(Exception):
    """Required serving dependency is unavailable; no implicit approve fallback."""


class FeatureUnavailable(ServingUnavailable):
    pass


class ModelUnavailable(ServingUnavailable):
    pass
