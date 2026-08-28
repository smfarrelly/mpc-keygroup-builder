"""Generate a standalone Program Designer demo with synthetic metadata."""

from __future__ import annotations

import argparse
from pathlib import Path

from .designer import build_view_bundle, render_html
from .device import DeviceProfile
from .layout import LayoutPreset
from .model import ProgramModel, SampleLayer, Zone
from .programs import load_palette
from .roles import infer_role


SAMPLES = (
    "BD Synthetic Deep.wav", "BD Synthetic Tight.wav", "SD Synthetic Snap.wav",
    "SD Synthetic Body.wav", "Clap Synthetic Wide.wav", "Rim Synthetic Wood.wav",
    "CH Synthetic Crisp.wav", "OH Synthetic Air.wav", "Tom Synthetic Low.wav",
    "Tom Synthetic High.wav", "Cymbal Synthetic Wash.wav", "Perc Synthetic Click.wav",
    "Perc Synthetic Shaker.wav", "FX Synthetic Noise.wav", "Vocal Synthetic Chop.wav",
    "Texture Synthetic Dust.wav",
)
NOTES = (37, 36, 42, 82, 40, 38, 46, 44, 48, 47, 45, 43, 49, 55, 51, 53)


def _program(name: str, rotate: int = 0) -> ProgramModel:
    palette = load_palette()
    samples = SAMPLES[rotate:] + SAMPLES[:rotate]
    zones = []
    for pad, (sample, note) in enumerate(zip(samples, NOTES), 1):
        role = infer_role(sample)
        category = role.split(".")[0]
        color_key = {
            "hihat": "closed_hat" if role == "hihat.closed" else "open_hat",
            "percussion": "percussion",
            "vocal": "fx",
            "texture": "fx",
        }.get(category, category)
        zones.append(
            Zone(
                pad,
                role,
                (SampleLayer(sample),),
                pad=pad,
                midi_note=note,
                color=palette.get(color_key, palette["unknown"]),
                playback_mode="one-shot",
                mute_group=1 if role in {"hihat.closed", "hihat.open"} else 0,
                monophonic=True,
            )
        )
    return ProgramModel(
        1,
        name,
        "drum",
        tuple(zones),
        "synthetic-browser-fixture",
        provenance={"license": "CC0-1.0", "audio": "metadata-only browser demo"},
        pad_note_map={pad: note for pad, note in enumerate(NOTES, 1)},
    )


def demo_bundle() -> dict:
    key37 = DeviceProfile(1, "mpc-key-37", "Akai MPC Key 37", 37, 4, 4, tuple("ABCDEFGH"))
    layouts = (
        LayoutPreset(1, "classic", "Classic MPC-ish", "role-first", ("kick", "kick", "snare", "snare", "hihat.closed", "hihat.open", "clap", "rim", "tom", "tom", "percussion", "percussion", "cymbal", "fx", "fx", "fx")),
        LayoutPreset(1, "right-handed", "Right-handed", "role-first", ("kick", "snare", "hihat.closed", "hihat.open", "clap", "rim", "percussion", "percussion", "tom", "tom", "cymbal", "fx", "fx", "fx", "fx", "fx")),
        LayoutPreset(1, "left-handed", "Left-handed", "role-first", ("hihat.open", "hihat.closed", "snare", "kick", "percussion", "percussion", "rim", "clap", "cymbal", "tom", "tom", "fx", "fx", "fx", "fx", "fx")),
    )
    return build_view_bundle(
        [(_program("FG Portable Kit"), None), (_program("FG Alternate Kit", 4), None)],
        [key37],
        list(layouts),
    )


def build_web_demo(output: Path, *, force: bool = False) -> Path:
    if output.exists() and not force:
        raise FileExistsError(f"browser demo exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(demo_bundle()), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="standalone HTML file to create")
    parser.add_argument("--force", action="store_true", help="replace an existing HTML file")
    args = parser.parse_args()
    path = build_web_demo(args.output.expanduser().resolve(), force=args.force)
    print(f"Wrote: {path}")
    print("Browser capabilities: inspect, compare, edit layouts, undo/redo, download draft JSON")
    print("Validated XPM export remains a CLI operation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
