"""Initialize and import durable Plugin Mapping Companion result ledgers."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from . import plugin_companion, plugin_map, plugin_params


STATUSES = {"pending", "pass", "warn", "fail"}
LEDGER_FIELDS = (
    "profile", "profile_name", "slot", "channel", "control", "cc", "plugin",
    "target", "ui_parameter", "mpc_parameter", "evidence", "priority", "status",
    "notes", "observed_at", "mapping_fingerprint",
)


def expected_rows(companion: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for page in companion["pages"]:
        for control in page["controls"]:
            rows.append(
                {
                    "profile": page["id"],
                    "profile_name": page["name"],
                    "slot": page["slot"],
                    "channel": page["channel"],
                    "control": control["control"],
                    "cc": control["cc"],
                    "plugin": control["plugin"],
                    "target": control["name"],
                    "ui_parameter": control["ui_parameter"],
                    "mpc_parameter": control["mpc_parameter"],
                    "evidence": control["evidence"],
                    "priority": control["priority"],
                    "status": "pending",
                    "notes": "",
                    "observed_at": "",
                    "mapping_fingerprint": companion["fingerprint"],
                }
            )
    return rows


def apply_results(companion: dict[str, Any], document: dict[str, Any]) -> list[dict[str, Any]]:
    if document.get("schema_version") != 1 or document.get("kind") != "mpc-plugin-mapping-results":
        raise ValueError("result export requires schema_version=1 and kind=mpc-plugin-mapping-results")
    if document.get("fingerprint") != companion["fingerprint"]:
        raise ValueError(
            f"mapping fingerprint mismatch: expected {companion['fingerprint']}, "
            f"got {document.get('fingerprint')!r}"
        )
    exported_at = document.get("exported_at")
    if not isinstance(exported_at, str) or not exported_at:
        raise ValueError("result export requires exported_at")
    pages = document.get("pages")
    if not isinstance(pages, list):
        raise ValueError("result export pages must be a list")
    expected = {(row["profile"], row["control"]): row for row in expected_rows(companion)}
    expected_page_ids = {page["id"] for page in companion["pages"]}
    observed: dict[tuple[str, str], dict[str, Any]] = {}
    page_ids: set[str] = set()
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get("id"), str):
            raise ValueError("each result page requires an id")
        if page["id"] in page_ids:
            raise ValueError(f"duplicate result page: {page['id']}")
        if page["id"] not in expected_page_ids:
            raise ValueError(f"unknown result page: {page['id']}")
        page_ids.add(page["id"])
        controls = page.get("controls")
        if not isinstance(controls, list):
            raise ValueError(f"{page['id']}: controls must be a list")
        for control in controls:
            if not isinstance(control, dict) or not isinstance(control.get("control"), str):
                raise ValueError(f"{page['id']}: each result control requires a control id")
            key = (page["id"], control["control"])
            if key in observed:
                raise ValueError(f"duplicate result control: {key[0]}/{key[1]}")
            reference = expected.get(key)
            if reference is None:
                raise ValueError(f"unknown result control: {key[0]}/{key[1]}")
            if control.get("plugin") != reference["plugin"] or control.get("target") != reference["target"]:
                raise ValueError(f"target mismatch for {key[0]}/{key[1]}")
            status = control.get("status")
            notes = control.get("notes")
            if status not in STATUSES:
                raise ValueError(f"invalid status for {key[0]}/{key[1]}: {status!r}")
            if not isinstance(notes, str):
                raise ValueError(f"notes must be text for {key[0]}/{key[1]}")
            observed[key] = {"status": status, "notes": notes}
    missing = sorted(set(expected) - set(observed))
    if missing:
        preview = ", ".join(f"{profile}/{control}" for profile, control in missing[:5])
        raise ValueError(f"result export is missing {len(missing)} controls: {preview}")
    rows = []
    for key, reference in expected.items():
        rows.append(
            {
                **reference,
                **observed[key],
                "observed_at": exported_at if observed[key]["status"] != "pending" else "",
            }
        )
    return rows


def render_csv(rows: list[dict[str, Any]]) -> str:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=LEDGER_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def render_report(rows: list[dict[str, Any]], fingerprint: str) -> str:
    total = Counter(row["status"] for row in rows)
    lines = [
        "# Plugin mapping hardware results",
        "",
        f"Mapping fingerprint: `{fingerprint}`",
        "",
        f"Overall: {total['pass']} pass, {total['warn']} warn, {total['fail']} fail, "
        f"{total['pending']} pending ({len(rows)} controls).",
        "",
    ]
    for profile in dict.fromkeys(row["profile"] for row in rows):
        selected = [row for row in rows if row["profile"] == profile]
        counts = Counter(row["status"] for row in selected)
        lines.extend(
            (
                f"## {selected[0]['profile_name']}",
                "",
                f"Slot {selected[0]['slot']}; channel {selected[0]['channel']}; "
                f"{counts['pass']} pass, {counts['warn']} warn, {counts['fail']} fail, "
                f"{counts['pending']} pending.",
                "",
            )
        )
        for row in selected:
            if row["status"] in {"warn", "fail"} or row["notes"]:
                note = f" — {row['notes']}" if row["notes"] else ""
                lines.append(
                    f"- **{row['status']}** {row['control']}: {row['plugin']} → "
                    f"{row['target']}{note}"
                )
        if lines[-1] != "":
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write(path: Path, content: str, *, force: bool) -> None:
    path = path.expanduser()
    if path.is_symlink():
        raise ValueError(f"plugin result output may not be a symbolic link: {path}")
    path = path.resolve()
    if path.exists() and not force:
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def _output_paths(ledger: Path, report: Path | None, *, force: bool) -> list[Path]:
    paths = []
    for label, path in (("ledger", ledger), ("report", report)):
        if path is None:
            continue
        path = path.expanduser()
        if path.is_symlink():
            raise ValueError(f"plugin result {label} may not be a symbolic link: {path}")
        resolved = path.resolve()
        if resolved.exists() and not resolved.is_file():
            raise ValueError(f"plugin result {label} must be a regular file: {resolved}")
        paths.append(resolved)
    if len(paths) != len(set(paths)):
        raise ValueError("ledger and report must use different paths")
    if not force:
        existing = [path for path in paths if path.exists()]
        if existing:
            raise FileExistsError(existing[0])
    return paths


def _companion(args: argparse.Namespace) -> dict[str, Any]:
    profiles = sorted(
        (plugin_map.load_profile(path) for path in args.profiles),
        key=lambda item: item["slot"],
    )
    catalog = plugin_params.catalog(args.synth_root.expanduser().resolve(), args.project)
    return plugin_companion.companion_data(profiles, catalog)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "import"):
        command = commands.add_parser(name)
        if name == "import":
            command.add_argument("results", type=Path)
        command.add_argument("profiles", type=Path, nargs="+")
        command.add_argument("--synth-root", type=Path, required=True)
        command.add_argument("--project", type=Path)
        command.add_argument("--ledger", type=Path, required=True)
        command.add_argument("--report", type=Path)
        command.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    targets = _output_paths(args.ledger, args.report, force=args.force)
    companion = _companion(args)
    if args.command == "init":
        rows = expected_rows(companion)
    else:
        document = json.loads(args.results.expanduser().resolve().read_text(encoding="utf-8"))
        rows = apply_results(companion, document)
    _write(targets[0], render_csv(rows), force=args.force)
    if args.report:
        _write(targets[1], render_report(rows, companion["fingerprint"]), force=args.force)
    counts = Counter(row["status"] for row in rows)
    print(
        f"Wrote {len(rows)} controls -> {args.ledger.expanduser().resolve()} "
        f"(pass={counts['pass']}, warn={counts['warn']}, fail={counts['fail']}, "
        f"pending={counts['pending']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
