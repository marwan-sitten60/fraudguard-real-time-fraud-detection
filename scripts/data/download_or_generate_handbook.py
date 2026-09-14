"""Download a bounded number of published Fraud Detection Handbook daily batches.

The upstream source is public simulated benchmark data. It is downloaded unchanged into
data/raw; canonicalization happens only in prepare_historical_data.py.
"""

import argparse
import hashlib
from datetime import date, timedelta
from pathlib import Path
from urllib.request import urlretrieve

DEFAULT_BASE_URL = (
    "https://raw.githubusercontent.com/Fraud-Detection-Handbook/simulated-data-raw/main/data"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download handbook raw daily pickle batches.")
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2018, 4, 1))
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw/fraud-handbook"))
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--source-revision", default="main")
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for offset in range(args.days):
        current = args.start_date + timedelta(days=offset)
        filename = f"{current.isoformat()}.pkl"
        destination = args.output_dir / filename
        url = f"{args.base_url.rstrip('/')}/{filename}"
        urlretrieve(url, destination)  # noqa: S310 - explicit public benchmark URL/override.
        checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
        print(f"downloaded {filename} sha256={checksum}")
    print(f"source revision recorded by caller: {args.source_revision}")


if __name__ == "__main__":
    main()
