import json
import random
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from fraudguard.data.labels import FraudLabel
from fraudguard.domain.enums import PaymentChannel
from fraudguard.schemas.transaction import TransactionRequest
from fraudguard.simulation.config import SimulationConfig
from fraudguard.simulation.models import CustomerProfile, MerchantProfile, SimulatedTransaction
from fraudguard.simulation.profiles import COUNTRIES, generate_profiles
from fraudguard.simulation.scenarios import SimulationScenario


class TransactionSimulator:
    """Seeded simulator. It generates synthetic operational traffic only."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.rng = random.Random(config.seed)
        self.customers, self.merchants = generate_profiles(
            self.rng,
            customer_count=config.number_of_customers,
            merchant_count=config.number_of_merchants,
        )
        self._sequence = 0

    def generate(
        self, scenario: SimulationScenario, transactions: int
    ) -> tuple[SimulatedTransaction, ...]:
        if transactions < 1:
            raise ValueError("transactions must be positive")
        if scenario is SimulationScenario.NORMAL:
            return tuple(self._normal(index) for index in range(transactions))
        generators = {
            SimulationScenario.CARD_TESTING: self._card_testing,
            SimulationScenario.HIGH_VELOCITY: self._high_velocity,
            SimulationScenario.ACCOUNT_TAKEOVER: self._account_takeover,
            SimulationScenario.IMPOSSIBLE_TRAVEL: self._impossible_travel,
            SimulationScenario.NEW_DEVICE_HIGH_VALUE: self._new_device_high_value,
            SimulationScenario.SHARED_DEVICE_FRAUD: self._shared_device_fraud,
            SimulationScenario.FRAUD_RING: self._fraud_ring,
        }
        return tuple(generators[scenario](index, transactions) for index in range(transactions))

    def _amount(
        self, minimum: Decimal, maximum: Decimal, multiplier: Decimal = Decimal("1")
    ) -> Decimal:
        value = minimum + (maximum - minimum) * Decimal(str(self.rng.random())) * multiplier
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _event_time(self, offset_seconds: int) -> datetime:
        return self.config.start_event_time + timedelta(seconds=offset_seconds)

    def _build(
        self,
        *,
        customer: CustomerProfile,
        merchant: MerchantProfile,
        device_id: str,
        amount: Decimal,
        offset_seconds: int,
        country: str,
        ip_country: str,
        label: FraudLabel,
        scenario: SimulationScenario,
    ) -> SimulatedTransaction:
        self._sequence += 1
        request = TransactionRequest(
            transaction_id=f"sim_tx_{self.config.seed}_{self._sequence:08d}",
            user_id=customer.customer_id,
            merchant_id=merchant.merchant_id,
            device_id=device_id,
            timestamp=self._event_time(offset_seconds),
            amount=amount,
            currency=self.config.currency,
            merchant_category=merchant.merchant_category,
            payment_channel=PaymentChannel.ONLINE,
            country=country,
            ip_country=ip_country,
        )
        return SimulatedTransaction(request, label, scenario.value, request.timestamp)

    def _normal(self, index: int) -> SimulatedTransaction:
        customer = self.customers[index % len(self.customers)]
        merchant = next(
            merchant
            for merchant in self.merchants
            if merchant.merchant_category in customer.usual_merchant_categories
        )
        return self._build(
            customer=customer,
            merchant=merchant,
            device_id=customer.known_device_ids[index % len(customer.known_device_ids)],
            amount=self._amount(customer.typical_amount_min, customer.typical_amount_max),
            offset_seconds=index * 3600,
            country=customer.home_country,
            ip_country=customer.home_country,
            label=FraudLabel.LEGITIMATE,
            scenario=SimulationScenario.NORMAL,
        )

    def _card_testing(self, index: int, total: int) -> SimulatedTransaction:
        customer, merchant = self.customers[0], self.merchants[0]
        final_attempt = index == total - 1
        amount = Decimal("250.00") if final_attempt else Decimal("1.00") + Decimal(index) / 10
        return self._build(
            customer=customer,
            merchant=merchant,
            device_id="sim_card_testing_device",
            amount=amount,
            offset_seconds=index * 20,
            country=customer.home_country,
            ip_country=customer.home_country,
            label=FraudLabel.FRAUD,
            scenario=SimulationScenario.CARD_TESTING,
        )

    def _high_velocity(self, index: int, total: int) -> SimulatedTransaction:
        customer, merchant = self.customers[1], self.merchants[1]
        return self._build(
            customer=customer,
            merchant=merchant,
            device_id="sim_velocity_device",
            amount=Decimal("25.00"),
            offset_seconds=index * 5,
            country=customer.home_country,
            ip_country=customer.home_country,
            label=FraudLabel.FRAUD,
            scenario=SimulationScenario.HIGH_VELOCITY,
        )

    def _account_takeover(self, index: int, total: int) -> SimulatedTransaction:
        customer, merchant = self.customers[2], self.merchants[2]
        foreign = next(country for country in COUNTRIES if country != customer.home_country)
        return self._build(
            customer=customer,
            merchant=merchant,
            device_id="sim_ato_new_device",
            amount=self._amount(
                customer.typical_amount_max, customer.typical_amount_max * Decimal("3")
            ),
            offset_seconds=index * 120,
            country=foreign,
            ip_country=foreign,
            label=FraudLabel.FRAUD,
            scenario=SimulationScenario.ACCOUNT_TAKEOVER,
        )

    def _impossible_travel(self, index: int, total: int) -> SimulatedTransaction:
        customer, merchant = self.customers[3], self.merchants[3]
        country = (
            customer.home_country
            if index % 2 == 0
            else next(item for item in COUNTRIES if item != customer.home_country)
        )
        return self._build(
            customer=customer,
            merchant=merchant,
            device_id="sim_travel_device",
            amount=Decimal("80.00"),
            offset_seconds=index * 300,
            country=country,
            ip_country=country,
            label=FraudLabel.FRAUD,
            scenario=SimulationScenario.IMPOSSIBLE_TRAVEL,
        )

    def _new_device_high_value(self, index: int, total: int) -> SimulatedTransaction:
        customer, merchant = self.customers[4], self.merchants[4]
        return self._build(
            customer=customer,
            merchant=merchant,
            device_id="sim_new_high_value_device",
            amount=customer.typical_amount_max * Decimal("4"),
            offset_seconds=index * 600,
            country=customer.home_country,
            ip_country=customer.home_country,
            label=FraudLabel.FRAUD,
            scenario=SimulationScenario.NEW_DEVICE_HIGH_VALUE,
        )

    def _shared_device_fraud(self, index: int, total: int) -> SimulatedTransaction:
        customer = self.customers[index % len(self.customers)]
        merchant = self.merchants[index % len(self.merchants)]
        return self._build(
            customer=customer,
            merchant=merchant,
            device_id="sim_shared_fraud_device",
            amount=Decimal("125.00"),
            offset_seconds=index * 90,
            country=customer.home_country,
            ip_country=customer.home_country,
            label=FraudLabel.FRAUD,
            scenario=SimulationScenario.SHARED_DEVICE_FRAUD,
        )

    def _fraud_ring(self, index: int, total: int) -> SimulatedTransaction:
        customer = self.customers[index % 3]
        merchant = self.merchants[index % 3]
        return self._build(
            customer=customer,
            merchant=merchant,
            device_id=f"sim_ring_device_{index % 2}",
            amount=Decimal("300.00"),
            offset_seconds=index * 60,
            country=merchant.country,
            ip_country=merchant.country,
            label=FraudLabel.FRAUD,
            scenario=SimulationScenario.FRAUD_RING,
        )


def write_transactions_jsonl(rows: tuple[SimulatedTransaction, ...], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as destination:
        for row in rows:
            payload = row.request.model_dump(mode="json") | {
                "fraud_label": int(row.fraud_label),
                "scenario": row.scenario,
            }
            destination.write(json.dumps(payload, sort_keys=True) + "\n")
