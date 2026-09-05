"""Query the MPC program ledger by musical and validation properties."""

from __future__ import annotations

import argparse
import csv
import json
from io import StringIO
from pathlib import Path


REQUIRED_FIELDS = {
    "path",
    "program_type",
    "hardware_status",
    "favorite",
    "scratchpad_role",
    "notes",
}
ALLOWED_HARDWARE = {"untested", "pass", "warn", "fail"}
ALLOWED_FAVORITES = {"yes", "no", "provisional"}


def _filter_value(value: str | None, allowed: set[str], label: str) -> str | None:
    if value is None:
        return None
    normalized = value.casefold()
    if normalized not in allowed:
        raise ValueError(
            f"invalid {label}: {value!r}; choose from {', '.join(sorted(allowed))}"
        )
    return normalized


def query(
    ledger: Path,
    *,
    program_type: str | None = None,
    hardware: str | None = None,
    favorite: str | None = None,
    role: str | None = None,
    search: str | None = None,
) -> list[dict[str, str]]:
    hardware = _filter_value(hardware, ALLOWED_HARDWARE, "hardware status")
    favorite = _filter_value(favorite, ALLOWED_FAVORITES, "favorite status")
    with ledger.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        missing = REQUIRED_FIELDS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"program ledger is missing fields: {', '.join(sorted(missing))}"
            )
        rows = list(reader)
    for number, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"program ledger row {number} has the wrong number of columns")
    filters = {
        "program_type": program_type,
        "hardware_status": hardware,
        "favorite": favorite,
        "scratchpad_role": role,
    }
    for field, value in filters.items():
        if value is not None:
            rows = [row for row in rows if row.get(field, "").casefold() == value.casefold()]
    if search:
        needle = search.casefold()
        rows = [
            row
            for row in rows
            if any(needle in value.casefold() for value in row.values())
        ]
    return rows


def render(rows: list[dict[str, str]], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(rows, indent=2) + "\n"
    fields = list(rows[0]) if rows else []
    if output_format == "csv":
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()
    return "\n".join(
        f"{row['path']} | {row['program_type']} | hardware={row['hardware_status']} "
        f"favorite={row['favorite'] or '-'} role={row['scratchpad_role'] or '-'}"
        for row in rows
    ) + ("\n" if rows else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--type", dest="program_type")
    parser.add_argument("--hardware", type=str.casefold, choices=sorted(ALLOWED_HARDWARE))
    parser.add_argument("--favorite", type=str.casefold, choices=sorted(ALLOWED_FAVORITES))
    parser.add_argument("--role")
    parser.add_argument("--search")
    parser.add_argument("--format", choices=("text", "json", "csv"), default="text")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = query(
        args.ledger,
        program_type=args.program_type,
        hardware=args.hardware,
        favorite=args.favorite,
        role=args.role,
        search=args.search,
    )
    output = render(rows, args.format)
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
