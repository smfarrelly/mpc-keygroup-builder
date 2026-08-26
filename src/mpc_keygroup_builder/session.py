"""Build one concise report for an MPC hardware-test session."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .candidates import check_candidates
from .rig import load as load_rig
from .rig import validate as validate_rig


def _read_optional(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(
    candidate_manifest: Path,
    ledger: Path,
    rig_profile: Path,
    *,
    sd_root: Path | None = None,
    routing_report: Path | None = None,
    deployment_report: Path | None = None,
) -> dict[str, Any]:
    rig_document = load_rig(rig_profile)
    candidates = check_candidates(candidate_manifest, ledger, sd_root)
    routing = _read_optional(routing_report)
    deployment = _read_optional(deployment_report)
    next_actions = list(candidates["issues"])
    rig_result = validate_rig(rig_document)
    next_actions.extend(rig_result["errors"])
    next_actions.extend(rig_result["warnings"])
    if routing_report is not None and routing is None:
        next_actions.append("controlled routing capture is not available")
    if deployment_report is not None and deployment is None:
        next_actions.append("SD deployment report is not available")
    return {
        "format": 1,
        "rig": {"path": str(rig_profile.resolve()), "name": rig_document["name"], **rig_result},
        "candidates": candidates,
        "routing_capture": routing,
        "deployment": deployment,
        "next_actions": next_actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_manifest", type=Path)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--rig", type=Path, required=True)
    parser.add_argument("--sd-root", type=Path)
    parser.add_argument("--routing-report", type=Path)
    parser.add_argument("--deployment-report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(
        args.candidate_manifest,
        args.ledger,
        args.rig,
        sd_root=args.sd_root,
        routing_report=args.routing_report,
        deployment_report=args.deployment_report,
    )
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 2 if report["rig"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
