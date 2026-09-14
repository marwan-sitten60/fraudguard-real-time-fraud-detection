from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

from fraudguard.api.app import create_app
from fraudguard.models.predictor import MockFraudModel
from fraudguard.schemas.scoring import ScoringResponse


def test_health_ready_metrics(client):
    assert client.get("/health").json()["status"] == "healthy"
    assert client.get("/ready").json()["status"] == "ready"
    assert client.get("/metrics").status_code == 200


def test_scoring_contract(client, payload):
    response = client.post(
        "/api/v1/transactions/score", json=payload, headers={"X-Request-ID": "test-request"}
    )
    assert response.status_code == 200
    score = ScoringResponse.model_validate(response.json())
    assert score.model_version == "mock-v1" and score.risk_score == 0.23
    assert response.headers["x-request-id"] == "test-request"
    metrics = client.get("/metrics").text
    assert 'fraudguard_decisions_total{decision="APPROVE"} 1.0' in metrics
    assert "transaction_id=" not in metrics and "user_id=" not in metrics


def test_invalid_is_sanitized(client, payload):
    payload["amount"] = "sensitive-invalid-value"
    response = client.post("/api/v1/transactions/score", json=payload)
    assert response.status_code == 422
    assert "sensitive-invalid-value" not in response.text
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_body_limit(client):
    response = client.post("/api/v1/transactions/score", content=b"x" * 17000)
    assert response.status_code == 413


def test_bad_request_id_replaced(client):
    assert (
        client.get("/health", headers={"X-Request-ID": "bad id"}).headers["x-request-id"]
        != "bad id"
    )


def test_model_loaded_once(settings, monkeypatch, payload):
    loader = Mock(return_value=MockFraudModel())
    monkeypatch.setattr("fraudguard.api.app.load_model", loader)
    with TestClient(create_app(settings)) as client:
        for _ in range(3):
            assert client.post("/api/v1/transactions/score", json=payload).status_code == 200
    loader.assert_called_once()


def test_serving_failure(client, payload):
    client.app.state.scoring_service.model.ready = False
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 503
    response = client.post("/api/v1/transactions/score", json=payload)
    assert response.status_code == 503
    assert response.json()["error"] == "serving_unavailable"


def test_feature_failure(client, payload):
    client.app.state.scoring_service.features.get_features = AsyncMock(
        side_effect=OSError("password")
    )
    response = client.post("/api/v1/transactions/score", json=payload)
    assert response.status_code == 503 and "password" not in response.text


def test_internal_errors_sanitized(client, payload):
    client.app.state.scoring_service.rules.evaluate = Mock(side_effect=RuntimeError("secret"))
    response = client.post("/api/v1/transactions/score", json=payload)
    assert response.status_code == 500 and "secret" not in response.text


def test_unknown_routes_have_bounded_labels(client):
    client.get("/arbitrary-user-secret")
    metrics = client.get("/metrics").text
    assert 'route="unmatched"' in metrics and "arbitrary-user-secret" not in metrics


def test_cors(settings):
    settings.cors_origins = ["http://localhost:3000"]
    with TestClient(create_app(settings)) as client:
        response = client.options(
            "/api/v1/transactions/score",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
        )
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
