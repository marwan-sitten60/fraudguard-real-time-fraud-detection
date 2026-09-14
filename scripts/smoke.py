"""Real HTTP smoke check; run against a separately started API."""

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

base = os.getenv("BASE_URL", "http://localhost:8000")
for route in ("health", "ready"):
    with urlopen(f"{base}/{route}", timeout=5) as response:
        assert response.status == 200
        print(route, response.read().decode())
body = Path(__file__).with_name("sample-transaction.json").read_bytes()
request = Request(
    f"{base}/api/v1/transactions/score",
    data=body,
    headers={"Content-Type": "application/json", "X-Request-ID": "smoke-phase1"},
)
with urlopen(request, timeout=5) as response:
    result = json.load(response)
    assert result["model_version"] == "mock-v1"
    assert result["risk_score"] == 0.23 and result["decision"] == "APPROVE"
    assert response.headers["X-Request-ID"] == "smoke-phase1"
    print("score", json.dumps(result))
with urlopen(f"{base}/metrics", timeout=5) as response:
    metrics = response.read().decode()
    for name in (
        "fraudguard_http_requests_total",
        "fraudguard_scoring_requests_total",
        "fraudguard_decisions_total",
        "fraudguard_scoring_duration_seconds",
    ):
        assert name in metrics
    print("metrics: required metric families present")
