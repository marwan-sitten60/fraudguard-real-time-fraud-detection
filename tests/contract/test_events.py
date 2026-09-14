import asyncio

import pytest
from pydantic import TypeAdapter, ValidationError

from fraudguard.streaming.events import FraudEvent, TransactionCreated
from fraudguard.streaming.producers.memory import InMemoryEventPublisher, NoOpEventPublisher


def test_roundtrip_and_version(payload):
    event = TransactionCreated(correlation_id="test", payload=payload)
    adapter = TypeAdapter(FraudEvent)
    assert adapter.validate_json(event.model_dump_json()) == event
    data = event.model_dump()
    data["event_version"] = 2
    with pytest.raises(ValidationError):
        adapter.validate_python(data)


def test_bounded_development_publisher(payload):
    publisher = InMemoryEventPublisher(capacity=1)
    first = TransactionCreated(correlation_id="first", payload=payload)
    second = TransactionCreated(correlation_id="second", payload=payload)
    asyncio.run(publisher.publish(first))
    asyncio.run(publisher.publish(second))
    assert list(publisher.events) == [second]
    asyncio.run(NoOpEventPublisher().publish(first))
