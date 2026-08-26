"""Export human-readable MPC Drum Program bank maps."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any

from .drum_audit import audit_drum_program
from .xpm import load_semantic


def pad_label(number: int) -> str:
    if not 1 <= number <= 128:
        return f"?{number}"
    bank = chr(ord("A") + (number - 1) // 16)
    return f"{bank}{(number - 1) % 16 + 1:02d}"


def build_map(path: Path) -> dict[str, Any]:
    audit = audit_drum_program(path)
    semantic = load_semantic(path)
    colors = semantic.get("program_pads", {}).get("colors", {})
    pads = []
    for item in audit["pads"]:
        pad = dict(item)
        color = colors.get(f"value{pad['pad'] - 1}")
        pad["label"] = pad_label(pad["pad"])
        pad["bank"] = pad["label"][0]
        pad["color"] = f"#{color & 0xFFFFFF:06X}" if isinstance(color, int) else ""
        pads.append(pad)
    return {
        "program": str(path.resolve()),
        "name": semantic.get("name", path.stem),
        "verdict": audit["verdict"],
        "issues": audit["issues"],
        "pads": pads,
    }


def _selected_pads(report: dict[str, Any], banks: set[str] | None) -> list[dict[str, Any]]:
    return [pad for pad in report["pads"] if banks is None or pad["bank"] in banks]


def render_markdown(report: dict[str, Any], banks: set[str] | None = None) -> str:
    lines = [f"# {report['name']} pad map", ""]
    current = None
    for pad in _selected_pads(report, banks):
        if pad["bank"] != current:
            current = pad["bank"]
            lines.extend(
                [
                    f"## Bank {current}",
                    "",
                    "| Pad | Category | Color | Mute | Poly | Mode | Sample |",
                    "|---|---|---:|---:|---:|---|---|",
                ]
            )
        sample = str(pad["sample"]).replace("|", "\\|")
        lines.append(
            f"| {pad['label']} | {pad['category']} | {pad['color'] or '-'} | "
            f"{pad['mute_group'] or '-'} | {pad['polyphony']} | {pad['playback_mode']} | {sample} |"
        )
    if report["issues"]:
        lines.extend(["", "## Audit warnings", ""])
        lines.extend(f"- {issue}" for issue in report["issues"])
    return "\n".join(lines) + "\n"


def render_csv(report: dict[str, Any], banks: set[str] | None = None) -> str:
    stream = io.StringIO(newline="")
    fields = (
        "label", "bank", "pad", "category", "color", "mute_group", "polyphony",
        "monophonic", "playback_mode", "sample",
    )
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for pad in _selected_pads(report, banks):
        writer.writerow({field: pad[field] for field in fields})
    return stream.getvalue()


def render_text(report: dict[str, Any], banks: set[str] | None = None) -> str:
    lines = [f"{report['name']} ({str(report['verdict']).upper()})"]
    for pad in _selected_pads(report, banks):
        lines.append(
            f"{pad['label']} {pad['category']:<12} {pad['color'] or '-':<7} "
            f"mute={pad['mute_group'] or '-':<2} poly={pad['polyphony']:<2} {pad['sample']}"
        )
    lines.extend(f"WARN: {issue}" for issue in report["issues"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path)
    parser.add_argument("--format", choices=("text", "markdown", "csv", "json"), default="text")
    parser.add_argument("--banks", help="comma-separated bank letters, for example A,B,C,D")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    banks = None
    if args.banks:
        banks = {value.strip().upper() for value in args.banks.split(",") if value.strip()}
        invalid = banks - set("ABCDEFGH")
        if invalid:
            parser.error(f"invalid banks: {', '.join(sorted(invalid))}")
    report = build_map(args.program.expanduser().resolve())
    if args.format == "json":
        rendered = json.dumps(report, indent=2) + "\n"
    elif args.format == "markdown":
        rendered = render_markdown(report, banks)
    elif args.format == "csv":
        rendered = render_csv(report, banks)
    else:
        rendered = render_text(report, banks)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Wrote: {args.output}")
    else:
        print(rendered, end="")
    return 0 if report["verdict"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
