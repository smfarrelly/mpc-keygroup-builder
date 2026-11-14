"""Render the same four-bar performance on three kits at a shared RMS level."""

from array import array
import json
import math
import sys

from mpc_keygroup_builder import audition, pad_recorder, pattern_audio
from audio import RATE, render, values, write_wave

BPM = 96
BEAT = RATE * 60 / BPM
FRAMES = round(16 * BEAT)


def phrase():
    notes = []
    for bar in range(4):
        start = bar * 4
        for beat, role, vel in (
            (0, "kick.primary", 108),
            (1, "snare.primary", 95),
            (2.5, "kick.primary", 84),
            (3, "snare.primary", 107),
            (2.75, "snare.primary", 40),
        ):
            notes.append((start + beat, role, vel))
        for eighth in range(8):
            role = "hihat.open" if eighth == 7 else "hihat.closed"
            notes.append((start + eighth / 2, role, 82 if eighth % 2 == 0 else 58))
    notes.extend(
        (15 + i / 4, "snare.primary", vel)
        for i, vel in enumerate((0, 52, 80, 118))
        if i
    )
    return sorted(notes)


def rms(samples):
    return math.sqrt(sum(v * v for v in samples) / len(samples))


def previews(probe, scratch, content, vinyl, layered, output):
    folder = output / "Listen"
    folder.mkdir()
    sounds = {}
    for source, label in ((vinyl, "Vinyl SP"), (layered, "Vinyl Layered")):
        layout, _ = pad_recorder.bank_data(source, "A", include_audio=False)
        by_role = {}
        for pad in layout["pads"]:
            by_role.setdefault(pad["role"], pad)
        events, actions = [], []
        for beat, role, vel in phrase():
            pad = by_role[role]
            events.append(
                dict(
                    tick=round(beat * 480),
                    pad=pad["pad"],
                    midi_note=pad["note"],
                    velocity=vel,
                    duration_ticks=120,
                    sample=pad["layers"][0]["sample"],
                )
            )
            actions.append((round(beat * BEAT), "on", 35 + pad["pad"], vel))
        idea = dict(
            schema_version=1,
            ppq=480,
            bars=4,
            tempo=BPM,
            program=layout["program"],
            events=events,
        )
        path = folder / (label + " phrase.json")
        path.write_text(json.dumps(idea, indent=2) + "\n")
        wav = scratch / (label + ".wav")
        pattern_audio.render_pattern(source, path, wav)
        sounds[label], _ = audition.read_pcm_mono(wav)
    raw = render(probe, scratch, "PocketLayers", FRAMES, actions, content=content)
    sounds["Pocket Layers"] = [v / 32768 for v in values(raw)[::2]]
    levels = {name: rms(s) for name, s in sounds.items()}
    target = min(
        0.12, *(0.88 * levels[n] / max(map(abs, s)) for n, s in sounds.items())
    )
    report = {}
    for name, s in sounds.items():
        pcm = array("h")
        for v in s:
            sample = round(v * target / levels[name] * 32767)
            pcm.extend((sample, sample))
        report[name] = dict(
            frames=len(s), rms_dbfs=round(20 * math.log10(rms(pcm) / 32768), 3)
        )
        if sys.byteorder != "little":
            pcm.byteswap()
        write_wave(folder / (name + ".wav"), pcm.tobytes())
    keys = [
        (0, "on", 60, 95),
        (6000, "off", 60, 0),
        (22050, "on", 63, 80),
        (30000, "off", 63, 0),
        (44100, "on", 60, 105),
        (115000, "on", 67, 94),
        (120000, "off", 60, 0),
        (165000, "off", 67, 0),
    ]
    write_wave(
        folder / "Bloom Keys.wav", render(probe, scratch, "BloomKeys", RATE * 5, keys)
    )
    # Tail of bar four repeats while the player continues with bar one.
    source = scratch / "input.pcm"
    source.write_bytes(raw + raw[: round(4 * BEAT) * 4])
    frames = source.stat().st_size // 4
    caught = render(
        probe,
        scratch,
        "BeatCatch",
        frames,
        [
            (FRAMES, "set", 1, 1),
            (FRAMES, "set", 0, 1),
            (FRAMES + round(2 * BEAT), "set", 0, 0),
        ],
        source=source,
    )
    write_wave(folder / "Beat Catch.wav", caught)
    write_wave(folder / "Beat Catch dry.wav", source.read_bytes())
    return report
