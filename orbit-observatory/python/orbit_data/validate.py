"""Validate a collector output directory, including hashes and evidence offsets."""

import argparse
import json

from .validation import validate_dataset


def main():
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    records = json.loads((args.output / "records.json").read_text())
    validate_dataset(records, args.output)
    print(f"Validated {len(records)} records. Empty outputs are not evidence of collection success.")


if __name__ == "__main__":
    main()
