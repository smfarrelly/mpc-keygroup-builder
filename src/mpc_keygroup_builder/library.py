"""Query the MPC program ledger by musical and validation properties."""

from __future__ import annotations

import argparse
import csv
import json
from io import StringIO
from pathlib import Path


def query(
    ledger: Path,
    *,
    program_type: str | None = None,
    hardware: str | None = None,
    favorite: str | None = None,
    role: str | None = None,
    search: str | None = None,
) -> list[dict[str, str]]:
    with ledger.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
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
        rows = [row for row in rows if any(needle in value.casefold() for value in row.values())]
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
    parser.add_argument("--hardware")
    parser.add_argument("--favorite")
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
