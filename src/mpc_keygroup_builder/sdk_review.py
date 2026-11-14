"""Run a trusted native plugin through Akai host_sim and save an offline mapping review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from . import plugin_companion, plugin_map, plugin_params, sdk_package, sdk_params
from .bundle_verify import sha256, verify_bundle
from .publication import publish_directory

RESULT = re.compile(r"Result: (PASS(?: with warnings)?|FAIL)\s+\((\d+) passed, (\d+) warnings, (\d+) failures\)")


def run_host(host: Path, native: Path, arguments: list[str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [str(host), str(native), *arguments], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"host_sim {arguments[0]} timed out after {timeout}s on {native.name}") from exc


def simulator_result(run: subprocess.CompletedProcess) -> dict:
    lines = run.stdout.strip().splitlines()
    summary = RESULT.fullmatch(lines[-1]) if lines else None
    if not summary:
        return {"status": "fail", "exit_code": run.returncode, "reason": "no final simulator check counts"}
    label, passes, warnings, failures = summary.groups()
    status = "pass"
    if run.returncode or int(failures) or not int(passes) or label == "FAIL":
        status = "fail"
    elif int(warnings) or label == "PASS with warnings":
        status = "warn"
    return {"status": status, "exit_code": run.returncode,
            "passed": int(passes), "warnings": int(warnings), "failures": int(failures)}


def review(*, host: Path, native: Path, output: Path, profile: Path | None = None,
           baseline: Path | None = None, package: Path | None = None,
           target: str = "arm32", timeout: int = 60, notes: str = "60") -> dict:
    """Publish completed evidence together, including warning/failure results."""
    host, native = (p.expanduser().resolve(strict=True) for p in (host, native))
    if not host.is_file() or not native.is_file():
        raise ValueError("supply a host_sim executable and a native plugin file")
    if not 1 <= timeout <= 3600:
        raise ValueError("timeout must be between 1 and 3600 seconds per simulator call")
    if not re.fullmatch(r"[0-9]{1,3}(,[0-9]{1,3}){0,31}", notes) or any(int(n) > 127 for n in notes.split(",")):
        raise ValueError("notes must be up to 32 comma-separated MIDI note numbers (0..127)")
    if target not in sdk_package.TARGETS:
        raise ValueError(f"unknown target: {target}")
    output = output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"choose a new review folder: {output}")
    if package and output.resolve().is_relative_to(package.expanduser().resolve()):
        raise ValueError("review output must be outside the package being checked")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=output.parent, prefix=f".{output.name}.review-"))
    page = plugin_map.load_profile(profile) if profile else None
    findings = []
    report = {
        "schema_version": 1, "kind": "mpc-sdk-software-review",
        "hardware_status": "untested", "native_sha256": sha256(native), "host_sim_sha256": sha256(host),
        "midi_notes": notes, "findings": findings,
    }
    try:
        dump_path = staging / "params.json"
        dump = run_host(host, native, ["dump"], timeout)
        if dump.returncode:
            detail = (dump.stderr.strip() or dump.stdout.strip())[-1200:]
            raise ValueError(f"host_sim dump failed ({dump.returncode}) for {native.name}: {detail}")
        dump_path.write_text(dump.stdout, encoding="utf-8")
        data = sdk_params.read_dump(dump_path)
        report.update(plugin=data["name"], uid_int=data["uidInt"], parameter_count=len(data["params"]),
                      dump_sha256=sha256(dump_path))
        if baseline:
            previous = sdk_params.read_dump(baseline)
            delta = sdk_params.compare(previous, data)
            if page:
                delta["profile_impact"] = sdk_params.profile_impact(delta, page, baseline, previous)
            report["parameter_comparison"] = delta
            if delta.get("profile_impact", delta)["review_required"]:
                findings.append("Parameter changes need mapping review.")
        simulation = run_host(host, native, ["test", "--playing", "--notes", notes], timeout)
        (staging / "host-sim.log").write_text(simulation.stdout + "\n" + simulation.stderr, encoding="utf-8")
        report["simulator"] = simulator_result(simulation)
        if package:
            try:
                report["package"] = sdk_package.inspect(package, target, dump_path)
            except (ValueError, OSError) as exc:
                findings.append(f"Package check failed: {exc}")
        if page:
            report["profile_sha256"] = sha256(profile)
            catalog = plugin_params.catalog(dump_path)
            locations = report.get("package", {}).get("q_links", {})
            for control in catalog["plugins"][0]["controls"]:
                control["q_links"] = locations.get(control["ui_parameter"], [])
            pages = [page]
            validation = plugin_map.validate_batch(pages, catalog)
            report["worksheet_warnings"] = validation["warnings"]
            findings.extend(validation["errors"])
            if not validation["errors"]:
                plugin_map.compile_batch(pages, catalog, staging / "worksheets")
                html = plugin_companion.render_html(plugin_companion.companion_data(pages, catalog))
                (staging / "companion.html").write_text(html, encoding="utf-8")
        if report["native_sha256"] != sha256(native) or report["host_sim_sha256"] != sha256(host):
            raise ValueError("simulator or native library changed during the review; rebuild and retry")
        status = "fail" if findings else report["simulator"]["status"]
        if status == "pass" and report.get("worksheet_warnings"):
            status = "warn"
        report["software_status"] = status
        (staging / "review.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        checksums = {
            path.relative_to(staging).as_posix(): sha256(path)
            for path in sorted(staging.rglob("*")) if path.is_file()
        }
        (staging / "checksums.json").write_text(json.dumps(checksums, indent=2) + "\n", encoding="utf-8")
        verify_bundle(staging)
        publish_directory(staging, output)
        return report
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native", type=Path, help="trusted desktop library built by the SDK for this computer")
    parser.add_argument("--host-sim", required=True, type=Path, help="trusted local SDK host_sim executable")
    parser.add_argument("--output", required=True, type=Path, help="new directory for this run")
    parser.add_argument("--profile", type=Path, help="compile worksheets and an offline companion for this page")
    parser.add_argument("--baseline", type=Path, help="previous host dump for drift comparison")
    parser.add_argument("--package", type=Path, help="cross-built folder for static inspection")
    parser.add_argument("--target", choices=sdk_package.TARGETS, default="arm32", help="CPU for package inspection")
    parser.add_argument("--timeout", type=int, default=60, metavar="SECONDS", help="limit per simulator call")
    parser.add_argument("--notes", default="60", help="comma-separated MIDI pitches for an instrument")
    args = parser.parse_args(argv)
    result = review(host=args.host_sim, native=args.native, output=args.output, profile=args.profile,
                    baseline=args.baseline, package=args.package, target=args.target, timeout=args.timeout,
                    notes=args.notes)
    print(f"{result['plugin']}: software {result['software_status']} · hardware untested")
    print(f"Review: {args.output.resolve() / 'review.json'}")
    for finding in result["findings"]:
        print(finding)
    return 0 if result["software_status"] == "pass" else 2
