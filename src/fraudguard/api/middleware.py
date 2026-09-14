import logging
import re
from time import perf_counter
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fraudguard.core.logging import request_id_context
from fraudguard.monitoring.metrics import Metrics

logger = logging.getLogger(__name__)


class RequestMiddleware:
    def __init__(self, app: ASGIApp, metrics: Metrics, max_request_bytes: int) -> None:
        self.app = app
        self.metrics = metrics
        self.max_request_bytes = max_request_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = perf_counter()
        headers = dict(scope["headers"])
        supplied = headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = supplied if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", supplied) else uuid4().hex
        token = request_id_context.set(request_id)
        status = 500
        response_started = False

        async def observed_send(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (b"x-request-id", request_id.encode("ascii")),
                ]
            await send(message)

        async def error(code: int, name: str) -> None:
            await JSONResponse({"error": name, "request_id": request_id}, status_code=code)(
                scope, receive, observed_send
            )

        try:
            length = headers.get(b"content-length")
            if length is not None:
                try:
                    declared = int(length)
                except ValueError:
                    await error(400, "invalid_content_length")
                    return
                if declared < 0:
                    await error(400, "invalid_content_length")
                    return
                if declared > self.max_request_bytes:
                    await error(413, "request_too_large")
                    return
            # Bound streamed bodies too; Content-Length alone is not a size limit.
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > self.max_request_bytes:
                    await error(413, "request_too_large")
                    return
                if not message.get("more_body", False):
                    break
            consumed = False

            async def replay() -> Message:
                nonlocal consumed
                if not consumed:
                    consumed = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            try:
                await self.app(scope, replay, observed_send)
            except Exception:
                logger.error("unhandled_request_error")
                if response_started:
                    raise
                await error(500, "internal_server_error")
        finally:
            route_obj = scope.get("route")
            route = getattr(route_obj, "path", "unmatched")
            method = scope["method"]
            if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
                method = "OTHER"
            elapsed = perf_counter() - started
            self.metrics.http_requests.labels(method, route, str(status)).inc()
            self.metrics.http_duration.labels(method, route).observe(elapsed)
            logger.info(
                "http_request",
                extra={
                    "method": method,
                    "route": route,
                    "status": status,
                    "latency_ms": round(elapsed * 1000, 3),
                },
            )
            request_id_context.reset(token)
