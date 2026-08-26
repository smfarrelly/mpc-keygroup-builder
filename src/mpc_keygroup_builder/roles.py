"""Stable semantic sound roles layered on top of broad filename categories."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from .programs import classify_sample


KNOWN_ROLES = {
    "kick.primary",
    "snare.primary",
    "hihat.closed",
    "hihat.open",
    "clap.primary",
    "rim.primary",
    "cymbal.crash",
    "cymbal.ride",
    "cymbal.other",
    "tom.low",
    "tom.mid",
    "tom.high",
    "tom.other",
    "percussion.bongo",
    "percussion.cabasa",
    "percussion.clave",
    "percussion.conga",
    "percussion.cowbell",
    "percussion.maraca",
    "percussion.shaker",
    "percussion.bell",
    "percussion.other",
    "fx.chord",
    "fx.vocal",
    "fx.bass",
    "fx.guitar",
    "fx.transition",
    "fx.texture",
    "fx.other",
    "melodic.instrument",
    "unknown.other",
}


def load_role_overrides(path: Path) -> dict[str, str]:
    """Load exact filename/stem role overrides from a small TOML file."""
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    values = data.get("roles", data.get("overrides"))
    if not isinstance(values, dict) or not values:
        raise ValueError("role override file requires a non-empty [roles] table")
    overrides: dict[str, str] = {}
    for name, role in values.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("role override names must be non-empty strings")
        if not isinstance(role, str) or role not in KNOWN_ROLES:
            raise ValueError(f"unknown semantic role override: {role!r}")
        overrides[name.casefold()] = role
    return overrides


def role_family(role: str) -> str:
    return role.split(".", 1)[0]


def _override(name: str, overrides: dict[str, str] | None) -> str | None:
    if not overrides:
        return None
    exact = overrides.get(Path(name).name.casefold())
    stem = overrides.get(Path(name).stem.casefold())
    role = exact or stem
    if role is not None and role not in KNOWN_ROLES:
        raise ValueError(f"unknown semantic role override: {role!r}")
    return role


def infer_role(name: str, overrides: dict[str, str] | None = None) -> str:
    overridden = _override(name, overrides)
    if overridden:
        return overridden
    value = Path(name).stem.casefold()
    category = classify_sample(name)
    if category == "kick":
        return "kick.primary"
    if category == "snare":
        return "snare.primary"
    if category == "closed_hat":
        return "hihat.closed"
    if category == "open_hat":
        return "hihat.open"
    if category == "clap":
        return "clap.primary"
    if category == "rim":
        return "rim.primary"
    if category == "cymbal":
        if re.search(r"(?:^|[ _-])ride(?:[ _-]|$)", value):
            return "cymbal.ride"
        if re.search(r"(?:^|[ _-])crash(?:[ _-]|$)", value):
            return "cymbal.crash"
        return "cymbal.other"
    if category == "tom":
        if re.search(r"(?:^|[ _-])(?:low|lo)(?:[ _-]|$)", value):
            return "tom.low"
        if re.search(r"(?:^|[ _-])mid(?:[ _-]|$)", value):
            return "tom.mid"
        if re.search(r"(?:^|[ _-])(?:high|hi)(?:[ _-]|$)", value):
            return "tom.high"
        return "tom.other"
    if category == "percussion":
        for token in ("bongo", "cabasa", "clave", "conga", "cowbell", "maraca", "shaker"):
            if re.search(rf"(?:^|[ _-]){token}(?:[ _-]|$)", value):
                return f"percussion.{token}"
        if re.search(r"(?:^|[ _-])bell(?:[ _-]|$)", value):
            return "percussion.bell"
        return "percussion.other"
    if category == "fx":
        if re.search(r"(?:^|[ _-])(?:vox|vocal|voice)(?:[ _-]|$)", value):
            return "fx.vocal"
        if re.search(r"(?:^|[ _-])chord(?:[ _-]|$)", value):
            return "fx.chord"
        if re.search(r"(?:^|[ _-])bass(?:[ _-]|$)", value):
            return "fx.bass"
        if re.search(r"(?:^|[ _-])guit(?:ar)?(?:[ _-]|$)", value):
            return "fx.guitar"
        if re.search(r"(?:^|[ _-])(?:reverse|riser|impact|boom|transition)(?:[ _-]|$)", value):
            return "fx.transition"
        if re.search(r"(?:^|[ _-])(?:grain|howl|noise|texture|static|crackle)(?:[ _-]|$)", value):
            return "fx.texture"
        return "fx.other"
    return "unknown.other"


def role_matches(actual: str, requested: str) -> bool:
    """Match an exact role or a family request such as ``percussion``."""
    return actual == requested or ("." not in requested and role_family(actual) == requested)
