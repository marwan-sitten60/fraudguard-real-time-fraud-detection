from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    seed: int = 42
    number_of_customers: int = 20
    number_of_merchants: int = 12
    start_event_time: datetime = datetime(2026, 1, 1, 9, tzinfo=UTC)
    currency: str = "USD"
    transactions_per_second: int = 1
    scenario_weights: dict[str, int] = field(
        default_factory=lambda: {
            "NORMAL": 70,
            "CARD_TESTING": 10,
            "HIGH_VELOCITY": 10,
            "ACCOUNT_TAKEOVER": 10,
        }
    )

    def __post_init__(self) -> None:
        if self.number_of_customers < 3 or self.number_of_merchants < 3:
            raise ValueError("simulation requires at least three customers and merchants")
        if self.transactions_per_second < 1:
            raise ValueError("transactions_per_second must be positive")
        if self.start_event_time.tzinfo is None or self.start_event_time.utcoffset() is None:
            raise ValueError("start_event_time must be timezone-aware")
