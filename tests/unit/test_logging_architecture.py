import ast
import json
import logging
from pathlib import Path

from fraudguard.core.logging import JsonFormatter, request_id_context


def test_logging_allowlist():
    token = request_id_context.set("correlation-test")
    try:
        record = logging.LogRecord(
            "fraudguard", logging.INFO, "test", 1, "transaction_scored", (), None
        )
        record.user_id = "secret-user"
        record.password = "secret-password"
        record.model_version = "mock-v1"
        result = JsonFormatter().format(record)
        assert "secret" not in result
        assert json.loads(result)["request_id"] == "correlation-test"
        assert json.loads(result)["model_version"] == "mock-v1"
    finally:
        request_id_context.reset(token)


def test_domain_does_not_import_adapters_or_frameworks():
    root = Path(__file__).parents[2] / "src/fraudguard/domain"
    allowed_roots = {"collections", "dataclasses", "datetime", "decimal", "enum", "typing"}
    for file in root.glob("*.py"):
        for node in ast.walk(ast.parse(file.read_text())):
            modules = []
            if isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            elif isinstance(node, ast.Import):
                modules = [item.name for item in node.names]
            for module in modules:
                assert module.split(".")[0] in allowed_roots or module.startswith(
                    "fraudguard.domain"
                )
