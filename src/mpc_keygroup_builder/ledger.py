"""Shared read-only validation for hardware status ledgers."""

import csv
from pathlib import Path

REQUIRED_FIELDS = {
    "path",
    "hardware_status",
    "favorite",
    "scratchpad_role",
    "notes",
}
ALLOWED_STATUSES = {"untested", "pass", "warn", "fail"}
ALLOWED_FAVORITES = {"", "yes", "no", "provisional"}


def read_ledger(ledger: Path) -> tuple[list[str], list[dict[str, str]]]:
    with ledger.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames or []
        missing = REQUIRED_FIELDS - set(fieldnames)
        if missing:
            raise ValueError(f"ledger is missing fields: {', '.join(sorted(missing))}")
        rows = list(reader)
    seen = set()
    for number, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"ledger row {number} has the wrong number of columns")
        path = row["path"]
        if not path.strip():
            raise ValueError(f"ledger row {number} has an empty program path")
        if path in seen:
            raise ValueError(f"ledger contains a duplicate program path: {path}")
        if row["hardware_status"] not in ALLOWED_STATUSES:
            raise ValueError(f"ledger row {number} has invalid hardware_status: {row['hardware_status']!r}")
        if row["favorite"] not in ALLOWED_FAVORITES:
            raise ValueError(f"ledger row {number} has invalid favorite: {row['favorite']!r}")
        seen.add(path)
    return fieldnames, rows

