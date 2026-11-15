"""Make playable alternatives from the notes and gestures in a saved MPC 3 sequence."""

import argparse
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

from . import xpj
from .sequence_morph import publish_project

# CLI names are stable so a favorite set can be recreated in a shell script.
MODES = {
    "hands": "Melody in your hands",
    "ghost": "Ghost choir",
    "reply": "Wait for the rest",
    "outline": "Hook silhouette",
    "resolve": "New destination",
    "fourth": "Fourth time around",
    "trade": "Trade rhythms",
    "negative": "Play the gaps",
    "mirror": "Mirror the hook",
    "fold": "Outside in",
    "phase": "Slipping gears",
    "hocket": "Pass the phrase",
    "pressure": "Touch becomes pitch",
    "stretch": "Half speed memory",
}
GUIDED = {"hands", "ghost", "pressure"}
PAIRED = {"trade", "hocket"}


def groups(clip):
    found = defaultdict(list)
    for event in clip["eventList"]["events"]:
        if event["type"] == 3 and not event.get("muted"):
            found[event["time"]].append(event)
    return sorted(found.items())


def write_notes(clip, notes):
    kept = [e for e in clip["eventList"]["events"] if e["type"] != 3 or e.get("muted")]
    clip["eventList"]["events"] = sorted(kept + notes, key=lambda e: e["time"])


def peak(chord):
    return max(e["note"]["velocity"] for e in chord)


def gate(chord):
    return max(e["note"]["length"] for e in chord)


def voice(chord, tick, room, *, level=None, shift=0, duration_scale=1):
    """Place the original voicing as a unit; retain its intervals at MIDI limits."""
    out = deepcopy(chord)
    pitches = [e["note"]["note"] for e in chord]
    shift = max(-min(pitches), min(127 - max(pitches), shift))
    gain = level / peak(chord) if level is not None and peak(chord) else 1
    for event in out:
        event["time"] = tick
        n = event["note"]
        n["note"] += shift
        n["length"] = max(1, min(room, round(n["length"] * duration_scale)))
        n["velocity"] = min(1.0, n["velocity"] * gain)
    return out


def rhythm(palette, clock, end):
    out = []
    for i, (tick, hits) in enumerate(clock):
        stop = clock[i + 1][0] if i + 1 < len(clock) else end
        out.extend(
            voice(palette[i % len(palette)][1], tick, stop - tick, level=peak(hits))
        )
    return out


def gaps(pattern, end):
    release = 0
    for i, (tick, chord) in enumerate(pattern):
        release = max(release, tick + gate(chord))
        stop = pattern[i + 1][0] if i + 1 < len(pattern) else end
        if release < stop:
            yield i, release, stop


def root(chord):
    return min(e["note"]["note"] for e in chord)


def solo(mode, pattern, end, beat, bar, destination):
    result = []
    if mode in ("negative", "reply"):
        if mode == "reply":
            result = [e for _, chord in pattern for e in chord]
        for i, release, stop in gaps(pattern, end):
            if mode == "negative":
                result.extend(voice(pattern[i][1], release, stop - release))
            elif stop - release >= beat // 2 and i >= 1:
                width = min(beat // 2, (stop - release) // 3)
                for k, source in enumerate((i, i - 1)):
                    result.extend(
                        voice(
                            pattern[source][1],
                            release + width * (k + 1),
                            width,
                            level=peak(pattern[source][1]) * 0.65,
                        )
                    )
        return result
    longest = sorted(gate(c) for _, c in pattern)[3 * len(pattern) // 4]
    phrase_start = 0
    for i, (tick, chord) in enumerate(pattern):
        stop = pattern[i + 1][0] if i + 1 < len(pattern) else end
        if mode == "outline":
            if (
                i == phrase_start
                or i + 1 == len(pattern)
                or stop - tick - gate(chord) >= beat
                or gate(chord) >= max(beat, longest)
            ):
                result.extend(chord)
            if stop - tick - gate(chord) >= beat:
                phrase_start = i + 1
        elif mode == "resolve":
            tail = min(3, len(pattern))
            weight = max(0, (i - (len(pattern) - tail) + 1) / tail)
            shift = round(weight * (destination - root(pattern[-1][1])))
            result.extend(
                chord if not shift else voice(chord, tick, end - tick, shift=shift)
            )
        elif mode == "mirror":
            pivot = root(pattern[0][1])
            result.extend(
                voice(chord, tick, end - tick, shift=2 * (pivot - root(chord)))
            )
        elif mode in ("fold", "phase"):
            if mode == "fold":
                index = i // 2 if i % 2 == 0 else len(pattern) - 1 - i // 2
            else:
                index = (i + tick // bar) % len(pattern)
            result.extend(
                voice(pattern[index][1], tick, stop - tick, level=peak(chord))
            )
        elif mode == "stretch" and tick * 2 < end:
            result.extend(voice(chord, tick * 2, end - tick * 2, duration_scale=2))
    return result


def full_clip(clip, end):
    if (
        clip["startPulses"] != 0
        or clip["endPulses"] != end
        or (
            clip.get("loop")
            and (clip["loopStartPulses"], clip["loopEndPulses"]) != (0, end)
        )
    ):
        raise ValueError("Phrase Lab needs full-sequence clips starting at zero")
    if any(t < 0 or t >= end for t, _ in groups(clip)):
        raise ValueError(
            "Move out-of-range note starts inside the clip before building"
        )


def fourth_pass(seq, target, end, beat):
    if (seq["loopStartPulses"], seq["loopEndPulses"]) != (0, end):
        raise ValueError("Fourth time around needs a full-sequence playback range")

    def repeat(event_list):
        events = event_list["events"]
        if any(
            "time" not in e or not 0 <= e["time"] < end or "audio" in e for e in events
        ):
            raise ValueError("Fourth time around cannot repeat this event format")
        event_list["events"] = [
            dict(deepcopy(e), time=e["time"] + n * end)
            for n in range(4)
            for e in events
        ]
        if event_list.get("length") == end:
            event_list["length"] = 4 * end

    for lane in seq["trackClipMaps"]:
        for row in lane:
            clip = row["value"]
            full_clip(clip, end)
            pattern = groups(clip)
            repeat(clip["eventList"])
            clip["endPulses"] = clip["loopEndPulses"] = 4 * end
            if row["key"] == target and pattern:
                # Cut the last beat and let the final played voicing anticipate the return.
                cut = 4 * end - beat
                notes = [e for t, c in groups(clip) if t < cut for e in c]
                for e in notes:
                    if e["time"] >= 3 * end:
                        e["note"]["length"] = min(e["note"]["length"], cut - e["time"])
                notes += voice(pattern[-1][1], cut + beat // 2, beat // 2)
                write_notes(clip, notes)
    repeat(seq["seqEventList"])
    seq["lengthPulses"] = seq["loopEndPulses"] = 4 * end
    seq["lengthBars"] *= 4
    seq["loopEndBar"] = seq["lengthBars"]


def transform(seq, mode, target, guide, partner, destination):
    meter = seq["timeSignatureTrack"]["timeSignatures"]
    if len(meter) != 1 or meter[0]["barStart"] != 0:
        raise ValueError("Select a sequence with a single meter")
    beat = meter[0]["beatLength"]
    end = seq["lengthPulses"]
    bar = beat * meter[0]["beatsPerBar"]
    if beat < 4 or end < beat or bar < beat:
        raise ValueError("Invalid sequence length or meter")
    if mode == "fourth":
        fourth_pass(seq, target, end, beat)
        return
    for lane in seq["trackClipMaps"]:
        clips = {row["key"]: row["value"] for row in lane}
        if target not in clips or not (pattern := groups(clips[target])):
            continue
        main = clips[target]
        full_clip(main, end)
        other = guide if mode in GUIDED else partner if mode in PAIRED else None
        if other is not None:
            if other not in clips or not (clock := groups(clips[other])):
                raise ValueError(
                    f"{mode} needs played notes on {other!r} in the target lane"
                )
            full_clip(clips[other], end)
        if mode == "hands":
            result = rhythm(pattern, clock, end)
        elif mode == "ghost":
            levels = sorted(peak(c) for _, c in clock)
            soft = [
                row
                for row in clock
                if peak(row[1]) <= levels[(len(levels) - 1) // 3]
                and peak(row[1]) < levels[-1]
            ]
            if not soft:
                print(
                    "Ghost choir: the guide has one attack level, so there are no ghost notes"
                )
            # Hold the opening voicing under the ghosts. A single-note opening
            # supplies its first three distinct melody pitches as a broken chord.
            tones = pattern[0][1]
            if len(tones) == 1:
                tones = []
                heard = set()
                for _, chord in pattern:
                    for event in chord:
                        pitch = event["note"]["note"]
                        if pitch not in heard:
                            heard.add(pitch)
                            tones.append(event)
                            if len(tones) == 3:
                                break
                    if len(tones) == 3:
                        break
            result = rhythm([(0, [note]) for note in tones], soft, end)
        elif mode == "pressure":
            palette = sorted(pattern, key=lambda row: root(row[1]))
            levels = [peak(c) for _, c in clock]
            lo, hi = min(levels), max(levels)
            if hi == lo:
                print(
                    "Touch becomes pitch: the guide has one velocity; using the middle voicing"
                )
                ordered = [palette[len(palette) // 2]] * len(clock)
            else:
                ordered = [
                    palette[round((v - lo) / (hi - lo) * (len(palette) - 1))]
                    for v in levels
                ]
            result = rhythm(ordered, clock, end)
        elif mode == "trade":
            result = rhythm(pattern, clock, end)
            write_notes(clips[other], rhythm(clock, pattern, end))
        elif mode == "hocket":
            attacks = sorted({t for t, _ in pattern + clock})
            # Both instruments inherit the motif, in registers drawn from their own takes.
            offset = root(clock[0][1]) - root(pattern[0][1])
            voices = [[], []]
            for i, tick in enumerate(attacks):
                room = (attacks[i + 1] if i + 1 < len(attacks) else end) - tick
                side = i % 2
                voices[side].extend(
                    voice(
                        pattern[i % len(pattern)][1],
                        tick,
                        room,
                        shift=offset if side else 0,
                    )
                )
            result = voices[0]
            write_notes(clips[other], voices[1])
        else:
            result = solo(mode, pattern, end, beat, bar, destination)
        write_notes(main, result)


def hands_midi(sequence, target, guide, bpm):
    """Teach a live Phrase Hands instance, then replay the guide in four orders."""
    from .midi_writer import MidiNote, MidiTrack, render_standard_midi

    meter = sequence["timeSignatureTrack"]["timeSignatures"]
    if len(meter) != 1 or meter[0]["beatsPerBar"] != 4 or meter[0]["beatLength"] != 960:
        raise ValueError("The Phrase Hands performance MIDI currently uses 4/4")
    end = sequence["lengthPulses"]
    lanes = []
    for lane in sequence["trackClipMaps"]:
        clips = {row["key"]: row["value"] for row in lane}
        if all(t in clips and groups(clips[t]) for t in (target, guide)):
            lanes.append(clips)
    if len(lanes) != 1:
        raise ValueError("Choose one played lane shared by the melody and rhythm guide")
    clips = lanes[0]
    for name in (target, guide):
        full_clip(clips[name], end)
    phrase = [
        max(e["note"]["note"] for e in chord) for _, chord in groups(clips[target])[:8]
    ]
    lift = 12 * max(0, (48 - min(phrase) + 11) // 12)
    if max(phrase) + lift > 127:
        raise ValueError("Phrase spans more notes than the playable learning register")
    bar = 3840
    notes = [MidiNote(0, bar - 120, 40, 100, 1)]
    for i, key in enumerate(phrase):
        notes.append(MidiNote(120 + i * 420, 240, key + lift, 90, 1))
    clock = groups(clips[guide])
    for i, pad in enumerate((36, 37, 38, 39)):
        start = bar + i * end
        notes.append(MidiNote(start - 2, 1, 41, 100, 1))
        for j, (tick, chord) in enumerate(clock):
            stop = clock[j + 1][0] if j + 1 < len(clock) else end
            notes.append(
                MidiNote(
                    start + tick,
                    min(100, stop - tick),
                    pad,
                    max(1, round(peak(chord) * 127)),
                    1,
                )
            )
    return render_standard_midi(
        (MidiTrack("Phrase Hands", tuple(notes)),),
        tempo=bpm,
        ppq=960,
        end_tick=bar + 4 * end,
        midi_format=0,
    )


def create(
    project,
    output,
    target,
    guide,
    partner,
    modes,
    sequence,
    destination,
    print_hands=False,
):
    p = xpj.load(project)
    data = p.data
    seqs = data["sequences"]
    matches = [
        s["value"]
        for s in seqs
        if (
            s["key"] == data["currentSequence"]
            if sequence is None
            else s["value"]["name"] == sequence
        )
    ]
    if len(matches) != 1:
        raise ValueError("Select a unique source with --sequence")
    source = matches[0]
    types = {t["name"]: t["program"]["type"] for t in data["tracks"]}
    played = {
        r["key"] for lane in source["trackClipMaps"] for r in lane if groups(r["value"])
    }

    def require(name, kinds, role):
        if name not in played or types.get(name) not in kinds:
            raise ValueError(
                f"Choose a played {role} track. Use mpc-sequence-morph PROJECT --list for names"
            )

    require(target, (1, 3, 4), "pitched --track")
    if print_hands or GUIDED.intersection(modes):
        require(guide, (0, 1, 3, 4), "--guide")
        if guide == target:
            raise ValueError("Choose a guide different from the target")
    if PAIRED.intersection(modes):
        require(partner, (1, 3, 4), "pitched --partner")
        if partner == target:
            raise ValueError("Choose a partner different from the target")
    if "fourth" in modes and any(
        types.get(row["key"]) == 6 and row["value"]["eventList"]["events"]
        for lane in source["trackClipMaps"]
        for row in lane
    ):
        raise ValueError(
            "Fourth time around supports note projects; select other modes for recorded audio"
        )
    if not 0 <= destination <= 127 or len(set(modes)) != len(modes):
        raise ValueError("Use a MIDI destination from 0 to 127 and distinct modes")
    slots = [i for i in range(128) if i not in {s["key"] for s in seqs}]
    if len(slots) < len(modes):
        raise ValueError("Too few available sequence slots")
    names = {s["value"]["name"] for s in seqs}
    for slot, mode in zip(slots, modes):
        variant = deepcopy(source)
        transform(variant, mode, target, guide, partner, destination)
        if variant == source:
            print(
                f"{MODES[mode]}: this performance already matches the rule; unchanged variation"
            )
        name = MODES[mode]
        suffix = 2
        while name in names:
            name = f"{MODES[mode]} {suffix}"
            suffix += 1
        names.add(name)
        variant["name"] = name
        seqs.append({"key": slot, "value": variant})
    extras = {}
    if print_hands:
        bpm = data["masterTempo"] if data.get("masterTempoEnabled") else source["bpm"]
        extras["Play this hook on Phrase Hands.mid"] = hands_midi(
            source, target, guide, bpm
        )
    publish_project(p, output, extras)
    return output / project.name


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="List recorded track names with mpc-sequence-morph PROJECT --list.",
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="new project folder")
    parser.add_argument(
        "--track", required=True, help="pitched source and destination track"
    )
    parser.add_argument("--guide", help="performed rhythm or dynamics track")
    parser.add_argument("--partner", help="second pitched track for trade and hocket")
    parser.add_argument(
        "--sequence", help="source sequence name (default: selected sequence)"
    )
    parser.add_argument(
        "--destination",
        type=int,
        default=60,
        help="landing MIDI note for resolve (default: 60)",
    )
    parser.add_argument(
        "--mode",
        action="append",
        choices=MODES,
        help="repeat to choose variations (default: all 14)",
    )
    parser.add_argument(
        "--hands-midi",
        action="store_true",
        help="include a MIDI performance that teaches the hook to Phrase Hands",
    )
    a = parser.parse_args()
    print(
        create(
            a.project,
            a.output,
            a.track,
            a.guide,
            a.partner,
            a.mode or list(MODES),
            a.sequence,
            a.destination,
            a.hands_midi,
        )
    )
