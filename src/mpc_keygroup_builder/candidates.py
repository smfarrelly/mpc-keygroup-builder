"""Check a reusable MPC candidate set against its ledger and SD deployment."""

from __future__ import annotations

import argparse
import csv
import json
import tomllib
from pathlib import Path
from typing import Any

from .testing import test_program


REQUIREMENTS = ("deployed", "hardware", "core", "final")


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        value = tomllib.load(stream)
    candidates = value.get("candidates")
    if value.get("schema_version") != 1 or not isinstance(candidates, list) or not candidates:
        raise ValueError("candidate manifest requires schema_version=1 and [[candidates]] tables")
    required = {"id", "ledger_path", "sd_path", "role", "selected"}
    required_roles = value.get("required_roles", [])
    if not isinstance(required_roles, list) or not all(
        isinstance(role, str) and role for role in required_roles
    ):
        raise ValueError("required_roles must be a list of nonempty strings")
    if len(required_roles) != len(set(required_roles)):
        raise ValueError("required_roles must not contain duplicates")
    ids = set()
    ledger_paths = set()
    for index, candidate in enumerate(candidates, 1):
        if not isinstance(candidate, dict) or required - set(candidate):
            raise ValueError(f"candidate {index} is missing required fields")
        for field in ("id", "ledger_path", "sd_path", "role"):
            if not isinstance(candidate[field], str) or not candidate[field].strip():
                raise ValueError(
                    f"candidate {index} {field} must be a nonempty string"
                )
        if not isinstance(candidate["selected"], bool):
            raise ValueError(f"candidate {index} selected must be true or false")
        if candidate["id"] in ids or candidate["ledger_path"] in ledger_paths:
            raise ValueError(f"candidate {index} duplicates an id or ledger path")
        ids.add(candidate["id"])
        ledger_paths.add(candidate["ledger_path"])
    return value


def _ledger_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return {row["path"]: row for row in csv.DictReader(stream)}


def check_candidates(
    manifest_path: Path, ledger_path: Path, sd_root: Path | None = None
) -> dict[str, Any]:
    if sd_root is not None and not sd_root.is_dir():
        raise ValueError(f"SD root is not a mounted directory: {sd_root}")
    manifest = load_manifest(manifest_path)
    ledger = _ledger_rows(ledger_path)
    results = []
    issues = []
    for candidate in manifest["candidates"]:
        ledger_row = ledger.get(candidate["ledger_path"])
        if ledger_row is None:
            raise ValueError(f"candidate is missing from ledger: {candidate['ledger_path']}")
        deployed = None
        sd_verdict = None
        if sd_root is not None:
            program = sd_root / candidate["sd_path"]
            deployed = program.is_file()
            if deployed:
                test = test_program(program, sd_root)
                sd_verdict = test.verdict
            else:
                sd_verdict = "missing"
                issues.append(f"{candidate['id']}: missing from SD deployment")
            if sd_verdict == "fail":
                issues.append(f"{candidate['id']}: SD program validation failed")
        status = ledger_row["hardware_status"]
        favorite = ledger_row["favorite"]
        if status == "untested":
            issues.append(f"{candidate['id']}: hardware listening is untested")
        if status == "fail":
            issues.append(f"{candidate['id']}: hardware status is fail")
        if candidate["selected"] and favorite != "yes":
            issues.append(f"{candidate['id']}: selected core favorite is {favorite or 'unset'}")
        results.append(
            {
                **candidate,
                "hardware_status": status,
                "favorite": favorite,
                "notes": ledger_row["notes"],
                "sd_present": deployed,
                "sd_verdict": sd_verdict,
            }
        )
    selected = [item for item in results if item["selected"]]
    selected_roles = [item["role"] for item in selected]
    duplicate_roles = sorted({role for role in selected_roles if selected_roles.count(role) > 1})
    if duplicate_roles:
        issues.append(f"selected core duplicates roles: {', '.join(duplicate_roles)}")
    required_roles = manifest.get("required_roles", [])
    missing_roles = [role for role in required_roles if role not in selected_roles]
    if missing_roles:
        issues.append(f"selected core is missing roles: {', '.join(missing_roles)}")
    deployed_ready = None if sd_root is None else all(
        item["sd_present"] and item["sd_verdict"] in {"pass", "warn"} for item in results
    )
    hardware_ready = all(item["hardware_status"] != "untested" for item in results)
    core_ready = (
        bool(selected)
        and not missing_roles
        and all(item["hardware_status"] in {"pass", "warn"} for item in selected)
    )
    final_ready = core_ready and all(item["favorite"] == "yes" for item in selected)
    return {
        "name": manifest.get("name", manifest_path.stem),
        "manifest": str(manifest_path.resolve()),
        "ledger": str(ledger_path.resolve()),
        "sd_root": str(sd_root.resolve()) if sd_root is not None else None,
        "readiness": {
            "deployed": deployed_ready,
            "hardware": hardware_ready,
            "core": core_ready,
            "final": final_ready,
        },
        "issues": issues,
        "candidates": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--ledger", type=Path, default=Path("inventory/program-status.csv"))
    parser.add_argument("--sd-root", type=Path)
    parser.add_argument("--require", choices=REQUIREMENTS, default="deployed")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = check_candidates(
        args.manifest.expanduser().resolve(),
        args.ledger.expanduser().resolve(),
        args.sd_root.expanduser().resolve() if args.sd_root else None,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(report["name"])
        for key, ready in report["readiness"].items():
            state = "NOT CHECKED" if ready is None else ("READY" if ready else "PENDING")
            print(f"{key}: {state}")
        for item in report["candidates"]:
            print(
                f"{item['id']}: hardware={item['hardware_status']} "
                f"favorite={item['favorite'] or '-'} sd={item['sd_verdict'] or 'not checked'}"
            )
        for issue in report["issues"]:
            print(f"PENDING: {issue}")
    return 0 if report["readiness"][args.require] is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
