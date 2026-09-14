from typing import Protocol

from fraudguard.streaming.events import FraudEvent


class EventPublisher(Protocol):
    async def publish(self, event: FraudEvent) -> None: ...


class EventHandler(Protocol):
    async def handle(self, event: FraudEvent) -> None: ...
