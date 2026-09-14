from decimal import Decimal

from fraudguard.data.labels import FraudLabel
from fraudguard.simulation.config import SimulationConfig
from fraudguard.simulation.generator import TransactionSimulator
from fraudguard.simulation.scenarios import SimulationScenario


def generate(scenario: SimulationScenario, count: int = 6, seed: int = 42):
    return TransactionSimulator(SimulationConfig(seed=seed)).generate(scenario, count)


def test_same_seed_is_reproducible_and_different_seed_changes_output():
    assert generate(SimulationScenario.NORMAL) == generate(SimulationScenario.NORMAL)
    assert generate(SimulationScenario.NORMAL, seed=43) != generate(SimulationScenario.NORMAL)


def test_normal_follows_customer_profile():
    simulator = TransactionSimulator(SimulationConfig(seed=42))
    rows = simulator.generate(SimulationScenario.NORMAL, 3)
    profile = next(
        item for item in simulator.customers if item.customer_id == rows[0].request.user_id
    )
    assert all(row.fraud_label is FraudLabel.LEGITIMATE for row in rows)
    assert rows[0].request.device_id in profile.known_device_ids
    assert profile.typical_amount_min <= rows[0].request.amount <= profile.typical_amount_max


def test_card_testing_is_rapid_low_value_then_larger_attempt():
    rows = generate(SimulationScenario.CARD_TESTING, 4)
    assert [row.request.amount for row in rows[:-1]] == [
        Decimal("1.00"),
        Decimal("1.10"),
        Decimal("1.20"),
    ]
    assert rows[-1].request.amount == Decimal("250.00")
    assert all(row.fraud_label is FraudLabel.FRAUD for row in rows)


def test_high_velocity_has_dense_event_times():
    rows = generate(SimulationScenario.HIGH_VELOCITY)
    differences = [
        (right.event_time - left.event_time).total_seconds()
        for left, right in zip(rows, rows[1:], strict=False)
    ]
    assert differences == [5.0] * 5


def test_account_takeover_changes_device_location_and_amount():
    simulator = TransactionSimulator(SimulationConfig(seed=42))
    row = simulator.generate(SimulationScenario.ACCOUNT_TAKEOVER, 1)[0]
    profile = simulator.customers[2]
    assert row.request.device_id not in profile.known_device_ids
    assert row.request.country != profile.home_country
    assert row.request.amount >= profile.typical_amount_max


def test_impossible_travel_alternates_country_inside_minutes():
    rows = generate(SimulationScenario.IMPOSSIBLE_TRAVEL, 2)
    assert rows[0].request.country != rows[1].request.country
    assert (rows[1].event_time - rows[0].event_time).total_seconds() == 300


def test_new_device_high_value_is_new_and_large():
    simulator = TransactionSimulator(SimulationConfig(seed=42))
    row = simulator.generate(SimulationScenario.NEW_DEVICE_HIGH_VALUE, 1)[0]
    profile = simulator.customers[4]
    assert row.request.device_id not in profile.known_device_ids
    assert row.request.amount == profile.typical_amount_max * 4


def test_shared_device_links_multiple_customers():
    rows = generate(SimulationScenario.SHARED_DEVICE_FRAUD, 4)
    assert {row.request.device_id for row in rows} == {"sim_shared_fraud_device"}
    assert len({row.request.user_id for row in rows}) > 1


def test_fraud_ring_has_shared_relationships_and_valid_requests():
    rows = generate(SimulationScenario.FRAUD_RING, 6)
    assert len({row.request.user_id for row in rows}) == 3
    assert len({row.request.device_id for row in rows}) == 2
    assert all(row.fraud_label is FraudLabel.FRAUD for row in rows)
    assert all(row.request.transaction_id.startswith("sim_tx_") for row in rows)
