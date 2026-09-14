import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fraudguard.api.app import create_app
from fraudguard.core.config import Settings
from fraudguard.schemas.transaction import TransactionRequest


@pytest.fixture
def payload():
    return json.loads((Path(__file__).parents[1] / "scripts/sample-transaction.json").read_text())


@pytest.fixture
def transaction(payload):
    return TransactionRequest.model_validate(payload).to_domain()


@pytest.fixture
def settings(monkeypatch):
    # Ignore developer .env and isolate environment-based serving knobs.
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    return Settings(_env_file=None, app_env="test")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client
