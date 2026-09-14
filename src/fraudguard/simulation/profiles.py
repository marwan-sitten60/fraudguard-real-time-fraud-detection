import random
from decimal import Decimal

from fraudguard.simulation.models import CustomerProfile, MerchantProfile

COUNTRIES = ("US", "GB", "DE", "JP", "AU")
MCCS = ("5411", "5812", "4111", "5732", "5999")


def generate_profiles(
    rng: random.Random, *, customer_count: int, merchant_count: int
) -> tuple[tuple[CustomerProfile, ...], tuple[MerchantProfile, ...]]:
    customers = tuple(
        CustomerProfile(
            customer_id=f"sim_customer_{index:04d}",
            home_country=COUNTRIES[index % len(COUNTRIES)],
            typical_amount_min=Decimal("5.00"),
            typical_amount_max=Decimal(str(50 + rng.randrange(50, 251))),
            usual_merchant_categories=(MCCS[index % len(MCCS)], MCCS[(index + 1) % len(MCCS)]),
            usual_active_hours=(7, 22),
            known_device_ids=(f"sim_device_{index:04d}_a", f"sim_device_{index:04d}_b"),
        )
        for index in range(customer_count)
    )
    merchants = tuple(
        MerchantProfile(
            merchant_id=f"sim_merchant_{index:04d}",
            merchant_category=MCCS[index % len(MCCS)],
            country=COUNTRIES[index % len(COUNTRIES)],
            typical_amount_min=Decimal("2.00"),
            typical_amount_max=Decimal(str(100 + rng.randrange(100, 501))),
            base_risk_level=Decimal(str(rng.randrange(1, 10) / 10)),
        )
        for index in range(merchant_count)
    )
    return customers, merchants
