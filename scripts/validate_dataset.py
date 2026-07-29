"""Validate normalized Uzbek–Karakalpak parallel corpus CSV files."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "data" / "csv"
FILES = ["geografiya_darslik.csv", "xabarlar.csv"]


def validate_file(path: Path) -> tuple[int, list[str]]:
    errors: list[str] = []
    count = 0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {"id", "uzbek", "karakalpak", "domain"}
        if set(reader.fieldnames or []) != expected:
            errors.append(f"Unexpected columns: {reader.fieldnames}")
        for line_number, row in enumerate(reader, start=2):
            count += 1
            if not row.get("uzbek", "").strip():
                errors.append(f"Line {line_number}: missing Uzbek text")
            if not row.get("karakalpak", "").strip():
                errors.append(f"Line {line_number}: missing Karakalpak text")
    return count, errors


def main() -> None:
    total = 0
    all_errors: list[str] = []
    for filename in FILES:
        path = CSV_DIR / filename
        count, errors = validate_file(path)
        total += count
        print(f"{filename}: {count} complete pairs")
        all_errors.extend(f"{filename}: {error}" for error in errors)

    print(f"Total: {total} complete pairs")
    if all_errors:
        print("\nValidation errors:")
        for error in all_errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("Validation passed.")


if __name__ == "__main__":
    main()
