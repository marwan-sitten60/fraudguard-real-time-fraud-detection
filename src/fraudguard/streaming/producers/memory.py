from collections import deque

from fraudguard.streaming.events import FraudEvent


class InMemoryEventPublisher:
    """Bounded development recorder; oldest entries discarded. NOT durable delivery."""

    def __init__(self, capacity: int = 100) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.events: deque[FraudEvent] = deque(maxlen=capacity)

    async def publish(self, event: FraudEvent) -> None:
        self.events.append(event)


class NoOpEventPublisher:
    async def publish(self, event: FraudEvent) -> None:
        return None
