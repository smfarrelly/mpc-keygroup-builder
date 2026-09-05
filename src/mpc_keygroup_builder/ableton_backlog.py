"""Prioritize Ableton source presets for MPC-native implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


GENERIC_COLLECTIONS = {"mpcexpansions", "programs", "samplesfrommars"}
LOOP_WORDS = re.compile(r"(?:^|[\s_/-])(?:loop|loops|break|breaks|groove|grooves)(?:[\s_./-]|$)")
KIT_WORDS = re.compile(r"(?:^|[\s_/-])(?:kit|kits|drum|drums)(?:[\s_./-]|$)")


def normalize(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum()).replace(
        "frommars", ""
    )


def pack_key(path: str) -> str:
    return path.split("/", 1)[0]


def display_pack(key: str) -> str:
    words = re.split(r"[_-]+", key)
    acronyms = {
        "cr78": "CR-78",
        "dmx": "DMX",
        "dx": "DX",
        "dx100": "DX100",
        "lm1": "LM-1",
        "mpc": "MPC",
        "mpc1": "MPC1",
        "mpc60": "MPC60",
        "mpc2000": "MPC2000",
        "mpc3000": "MPC3000",
        "ob": "OB",
        "sds800": "SDS800",
        "sdsv": "SDS-V",
        "sh5": "SH-5",
        "sid": "SID",
        "sp1200": "SP-1200",
        "sys100m": "SYS100M",
        "vp330": "VP-330",
    }
    kept = [word for word in words if word.casefold() not in {"from", "mars"}]
    rendered = [acronyms.get(word.casefold(), word.title()) for word in kept]
    result = " ".join(rendered)
    phrase_replacements = {
        "DX 100": "DX100",
        "Lo Fi": "Lo-Fi",
        "MS10": "MS-10",
        "MR10": "MR-10",
        "SP 909": "SP-909",
        "Vinyl Sp": "Vinyl SP",
    }
    for source, replacement in phrase_replacements.items():
        result = result.replace(source, replacement)
    return result


def _format_counts(values: dict[str, int] | object) -> str:
    if not isinstance(values, dict) or not values:
        return "none"
    return ", ".join(f"{key}={values[key]}" for key in sorted(values))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def catalog_coverage(catalog: dict[str, object] | None) -> dict[str, dict[str, int]]:
    coverage: dict[str, Counter[str]] = defaultdict(Counter)
    if not catalog:
        return {}
    if not isinstance(catalog, dict):
        raise ValueError("catalog must be a JSON object")
    programs = catalog.get("programs", [])
    if not isinstance(programs, list):
        raise ValueError("catalog programs must be a list")
    for program in programs:
        if not isinstance(program, dict):
            continue
        program_type = str(program.get("program_type", "")).casefold()
        if program_type not in {"drum", "keygroup", "clip"}:
            continue
        keys = {
            normalize(str(program.get("collection", ""))),
            normalize(str(program.get("category", ""))),
        }
        for key in keys - {""} - GENERIC_COLLECTIONS:
            coverage[key][program_type] += 1
    return {key: dict(counts) for key, counts in coverage.items()}


def target_for(preset: dict[str, object]) -> str:
    fidelity = preset.get("fidelity", {})
    grade = str(fidelity.get("grade", "D")) if isinstance(fidelity, dict) else "D"
    source_path = str(preset.get("path", ""))
    local_path = source_path.split("/", 1)[-1]
    path = f"{local_path} {preset.get('name', '')}".casefold()
    device_types = preset.get("device_types", {})
    devices = set(device_types) if isinstance(device_types, dict) else set()
    warped = preset.get("warped_zones", {})
    warped_true = int(warped.get("true", 0)) if isinstance(warped, dict) else 0
    kind = str(preset.get("kind", "")).casefold()
    if warped_true:
        return "clip"
    if kind == "als":
        if LOOP_WORDS.search(path):
            return "clip"
        return "reference" if grade == "D" else "project"
    if "DrumGroupDevice" in devices:
        return "drum"
    if LOOP_WORDS.search(path):
        return "clip"
    if grade == "D":
        return "reference"
    if int(preset.get("zones", 0)) > 0:
        return "keygroup"
    return "reference"


def _priority(
    preset: dict[str, object], target: str, existing: dict[str, int]
) -> tuple[int, list[str]]:
    score = 35
    reasons = []
    fidelity = preset.get("fidelity", {})
    grade = str(fidelity.get("grade", "D")) if isinstance(fidelity, dict) else "D"
    fidelity_points = {"A": 25, "B": 18, "C": 8, "D": -20}.get(grade, -20)
    score += fidelity_points
    reasons.append(f"fidelity {grade}")
    target_points = {"drum": 12, "keygroup": 12, "clip": 14, "project": 2, "reference": -15}
    score += target_points[target]
    path = str(preset.get("path", ""))
    name = str(preset.get("name", ""))
    lower = f"{path} {name}".casefold()
    source_kind = str(preset.get("kind", "")).casefold()
    if source_kind == "adg":
        score += 8
    elif source_kind == "als":
        score -= 8
        reasons.append("full Live set; prefer reusable rack when available")
    if "/02. kits/" in lower or "/presets/" in lower and KIT_WORDS.search(lower):
        score += 12
        reasons.append("prepared kit/preset")
    if "individual hits" in lower:
        score -= 8
        reasons.append("catalog-sized individual hits")
    if "demo" in lower:
        score -= 15
        reasons.append("demo/session source")
    zones = int(preset.get("zones", 0))
    if 0 < zones <= 256:
        score += 5
    elif zones > 512:
        score -= 6
        reasons.append("very large source map")
    pack = pack_key(path).casefold()
    if "vinyl" in pack:
        score += 8
        reasons.append("Vinyl Suite focus")
    elif any(token in pack for token in ("mirage", "juno", "emulator", "ob_", "dx_100")):
        score += 4
        reasons.append("known favorite family")
    existing_count = existing.get(target, 0)
    if existing_count:
        penalty = min(20, 6 + round(math.log2(existing_count + 1) * 3))
        score -= penalty
        reasons.append(f"{existing_count} existing {target} program(s)")
    return max(0, min(100, score)), reasons


def priority_label(score: int) -> str:
    if score >= 90:
        return "P0"
    if score >= 75:
        return "P1"
    if score >= 55:
        return "P2"
    return "P3"


def build_backlog(
    ableton_inventory: dict[str, object], catalog: dict[str, object] | None = None
) -> dict[str, object]:
    if not isinstance(ableton_inventory, dict):
        raise ValueError("Ableton inventory must be a JSON object")
    presets = ableton_inventory.get("presets", [])
    if not isinstance(presets, list):
        raise ValueError("Ableton inventory presets must be a list")
    for index, preset in enumerate(presets, 1):
        if not isinstance(preset, dict):
            raise ValueError(f"Ableton inventory preset {index} must be an object")
    coverage = catalog_coverage(catalog)
    source_root = Path(str(ableton_inventory.get("root", "")))
    source_hashes = {}
    hash_paths: dict[str, list[str]] = defaultdict(list)
    if source_root.is_dir():
        for preset in presets:
            if not isinstance(preset, dict):
                continue
            relative = str(preset.get("path", ""))
            source = source_root / relative
            if source.is_file():
                digest = _sha256(source)
                source_hashes[relative] = digest
                hash_paths[digest].append(relative)
    canonical_by_hash = {
        digest: min(paths, key=lambda path: ("(" in pack_key(path), path))
        for digest, paths in hash_paths.items()
    }
    entries = []
    for preset in presets:
        if not isinstance(preset, dict):
            continue
        key = pack_key(str(preset.get("path", "")))
        existing = coverage.get(normalize(key), {})
        target = target_for(preset)
        score, reasons = _priority(preset, target, existing)
        relative = str(preset.get("path", ""))
        source_sha256 = source_hashes.get(relative)
        canonical = canonical_by_hash.get(source_sha256) if source_sha256 else None
        duplicate_of = canonical if canonical and canonical != relative else None
        if duplicate_of:
            score = max(0, score - 35)
            reasons.append("exact duplicate source")
        entries.append(
            {
                "pack": key,
                "path": preset.get("path"),
                "name": preset.get("name"),
                "source_kind": preset.get("kind"),
                "target": target,
                "priority": priority_label(score),
                "score": score,
                "source_sha256": source_sha256,
                "duplicate_of": duplicate_of,
                "fidelity": preset.get("fidelity"),
                "zones": preset.get("zones", 0),
                "unique_samples": preset.get("unique_samples", 0),
                "macros": preset.get("macros", 0),
                "existing_mpc": existing,
                "reasons": reasons,
            }
        )
    entries.sort(key=lambda item: (-int(item["score"]), str(item["pack"]), str(item["path"])))
    pack_entries: dict[str, list[dict[str, object]]] = defaultdict(list)
    for entry in entries:
        pack_entries[str(entry["pack"])].append(entry)
    packs = []
    for key, values in pack_entries.items():
        priorities = Counter(str(item["priority"]) for item in values)
        targets = Counter(str(item["target"]) for item in values)
        grades = Counter(
            str(item["fidelity"].get("grade", "D"))
            for item in values
            if isinstance(item["fidelity"], dict)
        )
        existing = coverage.get(normalize(key), {})
        packs.append(
            {
                "pack": key,
                "name": display_pack(key),
                "score": max(int(item["score"]) for item in values),
                "priority": priority_label(max(int(item["score"]) for item in values)),
                "presets": len(values),
                "priorities": dict(sorted(priorities.items())),
                "targets": dict(sorted(targets.items())),
                "fidelity_grades": dict(sorted(grades.items())),
                "existing_mpc": existing,
                "top_candidates": [
                    {
                        "name": item["name"],
                        "path": item["path"],
                        "target": item["target"],
                        "priority": item["priority"],
                        "score": item["score"],
                    }
                    for item in values[:5]
                ],
            }
        )
    packs.sort(key=lambda item: (-int(item["score"]), str(item["pack"])))
    return {
        "format": 1,
        "source_root": ableton_inventory.get("root"),
        "summary": {
            "presets": len(entries),
            "packs": len(packs),
            "priorities": dict(sorted(Counter(str(item["priority"]) for item in entries).items())),
            "targets": dict(sorted(Counter(str(item["target"]) for item in entries).items())),
            "source_issues": len(ableton_inventory.get("issues", [])),
            "exact_duplicates": sum(1 for item in entries if item["duplicate_of"]),
        },
        "packs": packs,
        "entries": entries,
    }


def render_markdown(backlog: dict[str, object]) -> str:
    summary = backlog["summary"]
    lines = [
        "# Samples From Mars Ableton-to-MPC backlog",
        "",
        "This backlog is generated from readable `.adg`/`.als` metadata and the existing MPC catalog.",
        "It prioritizes new MPC-native musical value rather than literal one-for-one preset conversion.",
        "",
        "## Audit summary",
        "",
        f"- {summary['presets']} Ableton presets across {summary['packs']} packs.",
        f"- Targets: {_format_counts(summary['targets'])}.",
        f"- Priorities: {_format_counts(summary['priorities'])}.",
        f"- Source parse issues retained: {summary['source_issues']}.",
        f"- Exact duplicate sources demoted: {summary['exact_duplicates']}.",
        "",
        "Priority meanings: **P0** current playable product work; **P1** high-value next wave;",
        "**P2** useful coverage/variants; **P3** duplicate, session-sized, or reference-only work.",
        "",
        "## Pack queue",
        "",
    ]
    packs = backlog["packs"]
    for priority in ("P0", "P1", "P2", "P3"):
        selected = [pack for pack in packs if pack["priority"] == priority]
        lines.extend([f"### {priority}", ""])
        if not selected:
            lines.extend(["- None.", ""])
            continue
        for pack in selected:
            coverage = _format_counts(pack["existing_mpc"])
            candidates = "; ".join(
                f"{item['name']} → {item['target']} ({item['score']})"
                for item in pack["top_candidates"][:3]
            )
            lines.append(
                f"- **{pack['name']}** — {pack['presets']} sources; targets "
                f"{_format_counts(pack['targets'])}; "
                f"existing MPC {coverage}. Top: {candidates}."
            )
        lines.append("")
    lines.extend(
        [
            "## Conversion policy",
            "",
            "- Prefer prepared `.adg` instruments and kits over duplicate `.als` sessions.",
            "- Use Drum Programs for prepared Drum Racks, Keygroups for mapped melodic zones,",
            "  Clip Programs for warped/loop sources, and MPC projects only for genuine multi-track intent.",
            "- Treat large Individual Hits racks as catalogs for curated programs, not one giant conversion.",
            "- Keep byte-identical duplicate sources visible for audit provenance but convert only the canonical path.",
            "- Reduce priority when the catalog already has strong MPC coverage unless source metadata adds",
            "  velocity, looping, macro, effect, or routing behavior worth preserving.",
            "- Keep plug-in-dependent or zone-free sources as Reference-only until a defensible MPC-native",
            "  substitution is designed and hardware-tested.",
            "",
            "The complete preset-level queue is written to the ignored JSON backlog by",
            "`mpc-ableton-backlog`; this committed document intentionally stays pack-oriented.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    ableton_inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    catalog = json.loads(args.catalog.read_text(encoding="utf-8")) if args.catalog else None
    backlog = build_backlog(ableton_inventory, catalog)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(backlog, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(backlog), encoding="utf-8")
    print(
        f"presets={backlog['summary']['presets']} packs={backlog['summary']['packs']} "
        f"targets={backlog['summary']['targets']} priorities={backlog['summary']['priorities']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
