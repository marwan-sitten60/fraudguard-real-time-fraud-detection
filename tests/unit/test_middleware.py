import asyncio

import pytest

from fraudguard.api.middleware import RequestMiddleware
from fraudguard.monitoring.metrics import Metrics


@pytest.mark.parametrize(
    "headers,chunks,status",
    [
        ([], [b"x" * 9000, b"x" * 9000], 413),
        ([(b"content-length", b"nope")], [], 400),
        ([(b"content-length", b"-1")], [], 400),
    ],
)
def test_streamed_body_and_bad_lengths(headers, chunks, status):
    async def run():
        async def forbidden_app(scope, receive, send):
            pytest.fail("invalid request must not reach the application")

        messages = []
        iterator = iter(chunks)

        async def receive():
            return {"type": "http.request", "body": next(iterator), "more_body": True}

        async def send(message):
            messages.append(message)

        await RequestMiddleware(forbidden_app, Metrics("test"), 16384)(
            {"type": "http", "headers": headers, "method": "POST"}, receive, send
        )
        assert messages[0]["status"] == status
        assert any(k == b"x-request-id" for k, v in messages[0]["headers"])

    asyncio.run(run())
