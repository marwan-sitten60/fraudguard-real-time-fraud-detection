from prometheus_client import CollectorRegistry, Counter, Histogram, Info


class Metrics:
    """Per-app registry avoids duplicate registration in tests; one worker per container."""

    def __init__(self, version: str) -> None:
        self.registry = CollectorRegistry()
        info = Info("fraudguard_build", "Application build", registry=self.registry)
        info.info({"version": version})
        self.http_requests = Counter(
            "fraudguard_http_requests_total",
            "HTTP requests",
            ["method", "route", "status"],
            registry=self.registry,
        )
        self.http_duration = Histogram(
            "fraudguard_http_request_duration_seconds",
            "Full ASGI response duration",
            ["method", "route"],
            buckets=(0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.25, 0.5, 1),
            registry=self.registry,
        )
        self.scoring_requests = Counter(
            "fraudguard_scoring_requests_total", "Scoring attempts", registry=self.registry
        )
        self.scoring_duration = Histogram(
            "fraudguard_scoring_duration_seconds",
            "Application scoring duration",
            buckets=(0.001, 0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.25, 1),
            registry=self.registry,
        )
        self.decisions = Counter(
            "fraudguard_decisions_total",
            "Successful decisions",
            ["decision"],
            registry=self.registry,
        )
        self.model_errors = Counter(
            "fraudguard_model_errors_total", "Model failures", registry=self.registry
        )
        self.feature_errors = Counter(
            "fraudguard_feature_errors_total", "Feature failures", registry=self.registry
        )
        self.feature_fetch_duration = Histogram(
            "fraudguard_feature_fetch_duration_seconds",
            "Redis feature fetch duration",
            registry=self.registry,
        )
        self.feature_fetch_errors = Counter(
            "fraudguard_feature_fetch_errors_total",
            "Redis feature fetch failures",
            registry=self.registry,
        )
        self.feature_snapshot_stale = Counter(
            "fraudguard_feature_snapshot_stale_total",
            "Stale Redis snapshots",
            registry=self.registry,
        )
        self.feature_missing = Counter(
            "fraudguard_feature_missing_total",
            "Missing Redis snapshots",
            registry=self.registry,
        )
