"""Explainable octave placement for sampled Keygroup roots."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class RootPlacement:
    source_low: int
    source_high: int
    target_low: int
    target_high: int
    shift: int
    result_low: int
    result_high: int
    roots_in_target: int
    total_roots: int
    octave_only: bool = True

    @property
    def complete(self) -> bool:
        return self.roots_in_target == self.total_roots

    def to_dict(self) -> dict[str, int | bool]:
        return asdict(self) | {"complete": self.complete}


def validate_target(low: int, high: int) -> tuple[int, int]:
    if isinstance(low, bool) or isinstance(high, bool):
        raise TypeError("root target notes must be integers")
    if not isinstance(low, int) or not isinstance(high, int):
        raise TypeError("root target notes must be integers")
    if not 0 <= low <= high <= 127:
        raise ValueError("root target must satisfy 0 <= low <= high <= 127")
    return low, high


def parse_target(value: str) -> tuple[int, int]:
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError("root target must use LOW:HIGH")
    try:
        low, high = (int(part) for part in parts)
    except ValueError as error:
        raise ValueError("root target must use integer MIDI notes LOW:HIGH") from error
    return validate_target(low, high)


def infer_octave_shift(
    roots: Iterable[int], target_low: int, target_high: int
) -> RootPlacement:
    """Place roots in a target range without changing their pitch classes.

    Candidate shifts are whole octaves and must keep every root within MIDI
    0..127. The winner contains the most roots in the target, then uses the
    smallest absolute shift. Remaining ties prefer the closest target center
    and finally the lower signed shift for deterministic output.
    """

    target_low, target_high = validate_target(target_low, target_high)
    notes = sorted(set(roots))
    if not notes:
        raise ValueError("root inference requires at least one MIDI note")
    if any(isinstance(note, bool) or not isinstance(note, int) for note in notes):
        raise TypeError("sample roots must be integers")
    if not all(0 <= note <= 127 for note in notes):
        raise ValueError("sample roots must be within MIDI 0..127")
    source_low, source_high = notes[0], notes[-1]
    target_center_twice = target_low + target_high
    candidates: list[tuple[tuple[int, int, int, int], int, int]] = []
    for shift in range(-120, 121, 12):
        result_low = source_low + shift
        result_high = source_high + shift
        if result_low < 0 or result_high > 127:
            continue
        inside = sum(target_low <= note + shift <= target_high for note in notes)
        result_center_twice = result_low + result_high
        score = (
            inside,
            -abs(shift),
            -abs(result_center_twice - target_center_twice),
            -shift,
        )
        candidates.append((score, shift, inside))
    if not candidates:
        raise ValueError("no octave shift keeps all sample roots within MIDI 0..127")
    _, shift, inside = max(candidates)
    return RootPlacement(
        source_low,
        source_high,
        target_low,
        target_high,
        shift,
        source_low + shift,
        source_high + shift,
        inside,
        len(notes),
    )
