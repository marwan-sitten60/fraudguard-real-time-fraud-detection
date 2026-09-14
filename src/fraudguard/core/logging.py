import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

from fraudguard import __version__

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Allow-list fields; never serialize bodies, identifiers, exception text or secrets.
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            "application_version": __version__,
            "request_id": request_id_context.get(),
        }
        for key in ("method", "route", "status", "latency_ms", "model_version", "decision"):
            if key in record.__dict__:
                payload[key] = record.__dict__[key]
        return json.dumps(payload)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("fraudguard")
    root.handlers = [handler]
    root.setLevel(level)
    root.propagate = False
