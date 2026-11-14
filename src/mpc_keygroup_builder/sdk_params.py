"""Read parameter evidence exported by the Akai MPC SDK host simulator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _field(obj: dict, key: str, expected: type, where: str) -> Any:
    value = obj.get(key)
    if type(value) is not expected:
        raise ValueError(f"{where}: expected {key} to be {expected.__name__}")
    return value


def read_dump(path: Path) -> dict:
    path = path.expanduser().resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"{path}: invalid SDK parameter JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an Akai SDK host_sim dump object")
    where = str(path)
    for key in ("name", "vendor", "uid"):
        _field(data, key, str, where)
    if not data["name"].strip():
        raise ValueError(f"{path}: missing plugin name")
    # uid is only a printable rendering. uidInt preserves all four bytes.
    uid = _field(data, "uidInt", int, where)
    if not -(2**31) <= uid < 2**31:
        raise ValueError(f"{path}: uidInt must be a signed 32-bit integer")
    _field(data, "version", int, where)
    _field(data, "isInstrument", bool, where)
    for key in ("numInputs", "numOutputs", "numPrograms"):
        if _field(data, key, int, where) < 0:
            raise ValueError(f"{path}: negative {key}")
    params = _field(data, "params", list, where)
    indices = set()
    for position, row in enumerate(params):
        where = f"{path}: params[{position}]"
        if not isinstance(row, dict):
            raise ValueError(f"{where}: expected parameter object")
        index = _field(row, "index", int, where)
        if index < 0 or index in indices:
            raise ValueError(f"{where}: invalid or duplicate parameter index {index}")
        indices.add(index)
        for key in ("name", "kind", "label", "display"):
            _field(row, key, str, where)
        _field(row, "automatable", bool, where)
        choices = _field(row, "choices", list, where)
        if not all(isinstance(choice, str) for choice in choices):
            raise ValueError(f"{where}: choices must contain strings")
        default = row.get("default")
        if type(default) not in (int, float) or not 0 <= default <= 1:
            raise ValueError(f"{where}: default must be normalized between 0 and 1")
    if indices != set(range(len(params))):
        raise ValueError(f"{path}: SDK parameter indices must be contiguous from zero")
    data["params"].sort(key=lambda row: row["index"])
    return data


def inspect(path: Path, *, dump: dict | None = None) -> dict:
    from .plugin_params import _score

    path = path.expanduser().resolve()
    data = read_dump(path) if dump is None else dump
    controls = []
    for param in data["params"]:
        controls.append({
            "ui_parameter": param["index"],
            "mpc_parameter": None,
            "mpc_parameter_basis": "sdk-host-index",
            "name": param["name"],
            "aliases": [],
            "control_type": "switch" if param["kind"] == "bool" else param["kind"],
            "q_links": [],
            "learned": False,
            "learned_cc": [],
            "learned_channel": [],
            "usefulness_score": _score(param["name"], False) if param["automatable"] else 0,
            "sdk": {key: param[key] for key in ("automatable", "kind", "label", "display", "default", "choices")},
        })
    return {
        "schema_version": 1,
        "plugin": data["name"],
        "source": str(path),
        "source_kind": "sdk-host-dump",
        "sdk_identity": {"vendor": data["vendor"], "uid_int": data["uidInt"]},
        "sdk_version": data["version"],
        "plugin_kind": "instrument" if data["isInstrument"] else "effect",
        "preset_count": data["numPrograms"],
        "control_count": len(controls),
        "learned_control_count": 0,
        "controls": controls,
        "boundary": "Parameter indices and automation flags come from host_sim. MPC Learn IDs require a saved hardware mapping.",
    }


def compare(before: dict, after: dict) -> dict:
    """Compare the host-visible contract at each index used by existing mappings."""
    changes = []

    def change(level: str, field: str, old: Any, new: Any, index: int | None = None):
        changes.append({"level": level, "field": field, "before": old, "after": new, "index": index})

    for key in ("name", "vendor", "uidInt", "isInstrument", "numInputs", "numOutputs", "version"):
        if before[key] != after[key]:
            change("info" if key == "version" else "review", key, before[key], after[key])
    old_params = {row["index"]: row for row in before["params"]}
    new_params = {row["index"]: row for row in after["params"]}
    for index in sorted(old_params.keys() | new_params.keys()):
        old = old_params.get(index)
        new = new_params.get(index)
        if old is None:
            change("info", "added", None, new["name"], index)
        elif new is None:
            change("review", "removed", old["name"], None, index)
        else:
            for key in ("name", "label", "kind", "choices", "automatable", "default", "display"):
                if old[key] != new[key]:
                    level = "info" if key in ("default", "display") else "review"
                    change(level, key, old[key], new[key], index)
    return {
        "schema_version": 1,
        "kind": "sdk-parameter-comparison",
        "plugin": after["name"],
        "review_required": any(item["level"] == "review" for item in changes),
        "changes": changes,
    }


def profile_impact(report: dict, profile: dict, baseline_path: Path, baseline: dict) -> dict:
    """Identify exactly which physical encoders/buttons have a changed contract."""
    from .plugin_map import validate_profile

    catalog = {"plugins": [inspect(baseline_path, dump=baseline)]}
    verified = validate_profile(profile, catalog)
    if verified["errors"]:
        raise ValueError("profile does not match the baseline: " + "; ".join(verified["errors"]))
    affected = []
    for control in verified["controls"]:
        changes = [
            change for change in report["changes"]
            if change["level"] == "review" and change["index"] in (None, control["ui_parameter"])
        ]
        if changes:
            affected.append({
                "control": control["control"], "name": control["name"], "index": control["ui_parameter"],
                "channel": control["channel"], "cc": control["cc"], "fields": [c["field"] for c in changes],
            })
    return {"profile": profile["id"], "review_required": bool(affected), "affected_controls": affected}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare two Akai host_sim parameter dumps for mapping drift.")
    parser.add_argument("before", type=Path, help="previous build/params.json")
    parser.add_argument("after", type=Path, help="new build/params.json")
    parser.add_argument("--profile", type=Path, help="identify affected XL3 assignments and scope the exit code to this page")
    parser.add_argument("--json", action="store_true", help="print a machine-readable comparison")
    args = parser.parse_args(argv)
    before = read_dump(args.before)
    report = compare(before, read_dump(args.after))
    needs_review = report["review_required"]
    if args.profile:
        from .plugin_map import load_profile

        impact = profile_impact(report, load_profile(args.profile), args.before, before)
        report["profile_impact"] = impact
        needs_review = impact["review_required"]
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['plugin']} · {len(report['changes'])} changes")
        for item in report["changes"]:
            target = f"parameter {item['index']}" if item["index"] is not None else "plugin"
            print(f"{item['level']} {target} {item['field']}: {item['before']!r} -> {item['after']!r}")
        if args.profile:
            controls = report["profile_impact"]["affected_controls"]
            print(f"{len(controls)} mapped controls need review on {report['profile_impact']['profile']}")
            for control in controls:
                print(f"  {control['control']} · ch{control['channel']}/CC{control['cc']} "
                      f"{control['name']} ({', '.join(control['fields'])})")
    return 2 if needs_review else 0
