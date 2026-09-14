import argparse
from pathlib import Path

from fraudguard.simulation.config import SimulationConfig
from fraudguard.simulation.generator import TransactionSimulator, write_transactions_jsonl
from fraudguard.simulation.scenarios import SimulationScenario


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic FraudGuard operational traffic."
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--transactions", type=int, default=20)
    parser.add_argument(
        "--scenario", choices=[item.value for item in SimulationScenario], default="NORMAL"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = TransactionSimulator(SimulationConfig(seed=args.seed)).generate(
        SimulationScenario(args.scenario), args.transactions
    )
    write_transactions_jsonl(rows, args.output)
    print(f"wrote {len(rows)} synthetic {args.scenario} events to {args.output}")


if __name__ == "__main__":
    main()
