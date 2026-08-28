"""Load and validate declarative MPC hardware profiles."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DeviceProfile:
    schema_version: int
    id: str
    name: str
    keys: int
    pad_rows: int
    pad_columns: int
    banks: tuple[str, ...]

    @property
    def pads_per_bank(self) -> int:
        return self.pad_rows * self.pad_columns

    @property
    def capacity(self) -> int:
        return self.pads_per_bank * len(self.banks)

    def label(self, slot: int) -> str:
        if not 1 <= slot <= self.capacity:
            raise ValueError(f"slot must be 1..{self.capacity}: {slot}")
        bank = self.banks[(slot - 1) // self.pads_per_bank]
        pad = (slot - 1) % self.pads_per_bank + 1
        return f"{bank}{pad:02d}"

    def validate(self) -> list[str]:
        errors = []
        if self.schema_version != 1:
            errors.append("device profile requires schema_version=1")
        if not self.id or not self.name:
            errors.append("device profile requires id and name")
        if self.keys < 0:
            errors.append("device keys cannot be negative")
        if self.pad_rows < 1 or self.pad_columns < 1:
            errors.append("pad rows and columns must be positive")
        if not self.banks or len(self.banks) != len(set(self.banks)):
            errors.append("device banks must be non-empty and unique")
        if self.capacity > 128:
            errors.append("device pad capacity cannot exceed MPC's 128 slots")
        return errors


BUILTIN_DEVICES = {
    "key37": DeviceProfile(1, "mpc-key-37", "Akai MPC Key 37", 37, 4, 4, tuple("ABCDEFGH")),
    "key61": DeviceProfile(1, "mpc-key-61", "Akai MPC Key 61", 61, 4, 4, tuple("ABCDEFGH")),
}


def resolve_device(value: str | Path) -> DeviceProfile:
    name = str(value).casefold()
    aliases = {"key-37": "key37", "mpc-key-37": "key37", "key-61": "key61", "mpc-key-61": "key61"}
    builtin = BUILTIN_DEVICES.get(aliases.get(name, name))
    return builtin if builtin is not None else load_device(Path(value).expanduser().resolve())


def load_device(path: Path) -> DeviceProfile:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    banks = data.get("banks")
    if not isinstance(banks, list) or not all(isinstance(item, str) and item for item in banks):
        raise ValueError("device banks must be a list of names")
    required = ("schema_version", "id", "name", "keys", "pad_rows", "pad_columns")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"device profile is missing: {', '.join(missing)}")
    profile = DeviceProfile(
        schema_version=data["schema_version"],
        id=data["id"],
        name=data["name"],
        keys=data["keys"],
        pad_rows=data["pad_rows"],
        pad_columns=data["pad_columns"],
        banks=tuple(banks),
    )
    errors = profile.validate()
    if errors:
        raise ValueError("; ".join(errors))
    return profile
