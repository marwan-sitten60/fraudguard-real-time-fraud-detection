import argparse
from pathlib import Path

from fraudguard.training.pipeline import train_baseline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train an offline FraudGuard baseline; API remains mock-v1."
    )
    parser.add_argument("--data-directory", type=Path, required=True)
    parser.add_argument("--model", choices=("logistic", "xgboost"), required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--mlflow-tracking-uri", default="http://127.0.0.1:5000")
    parser.add_argument("--output-directory", type=Path, default=Path("artifacts/training"))
    args = parser.parse_args()
    print(
        train_baseline(
            data_directory=args.data_directory,
            model_type=args.model,
            seed=args.seed,
            tracking_uri=args.mlflow_tracking_uri,
            output_directory=args.output_directory,
        )
    )


if __name__ == "__main__":
    main()
