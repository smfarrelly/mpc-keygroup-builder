"""Borrow the timing or touch of a performed guide track within one clip lane."""

from bisect import bisect_left
from collections import defaultdict

GUIDED_STYLES = ("lock", "accent", "duck")


def bounds(clip):
    start, end = clip["startPulses"], clip["endPulses"]
    if clip.get("loop"):
        start = max(start, clip["loopStartPulses"])
        end = min(end, clip["loopEndPulses"])
    return start, end


def note_groups(clip):
    groups = defaultdict(list)
    for event in clip["eventList"]["events"]:
        if event["type"] == 3:
            groups[event["time"]].append(event)
    return groups


def transfer(target, guide, style, amount):
    if not amount:
        return 0
    meter = target.get("timeSignatureList", {}).get("timeSignatures", [])
    if len(meter) != 1 or meter[0]["barStart"] != 0 or target["timeSignatureList"] != guide.get("timeSignatureList"):
        raise ValueError("Groove transfer requires matching single-meter clips")
    if bounds(target) != bounds(guide) or target["startPulses"] != guide["startPulses"]:
        raise ValueError("Groove transfer requires matching clip starts and playback ranges")
    start, end = bounds(target)
    beat = meter[0]["beatLength"]
    bar = beat * meter[0]["beatsPerBar"]
    if beat < 4 or bar <= 0:
        raise ValueError("Invalid clip meter")
    guide_levels = {}
    for tick, events in note_groups(guide).items():
        levels = [e["note"]["velocity"] for e in events if not e.get("muted")]
        if start <= tick < end and levels:
            guide_levels[tick] = max(levels)
    guide_ticks = sorted(guide_levels)
    groups = note_groups(target)
    ticks = sorted(groups)
    # A timing move must leave room for the next attack of each pitch.
    upcoming = {}
    next_attack = {}
    if style == "lock":
        for tick in reversed(ticks):
            pitches = {(e.get("channel", 0), e["note"]["note"]) for e in groups[tick]}
            for pitch in pitches:
                next_attack[tick, pitch] = upcoming.get(pitch, end)
                upcoming[pitch] = tick
    releases = {}
    changed = 0
    for index, tick in enumerate(ticks):
        events = groups[tick]
        position = bisect_left(guide_ticks, tick)
        nearby = [g for g in guide_ticks[max(0, position - 1):position + 1]
                  if g // bar == tick // bar and abs(g - tick) <= beat // 4]
        playable = start <= tick < end and not any(e.get("muted") for e in events)
        at = tick
        if nearby and playable:
            match = min(nearby, key=lambda g: (abs(g - tick), g))
            if style == "lock":
                at = tick + round((match - tick) * amount / 100)
                # Midpoints keep independently moved chords ordered and distinct.
                low = max(start, tick // bar * bar)
                high = min(end - 1, (tick // bar + 1) * bar - 1)
                if index:
                    low = max(low, (ticks[index - 1] + tick) // 2 + 1)
                if index + 1 < len(ticks):
                    high = min(high, (ticks[index + 1] + tick - 1) // 2)
                for e in events:
                    pitch = (e.get("channel", 0), e["note"]["note"])
                    low = max(low, min(tick, releases.get(pitch, start)))
                    high = min(high, max(tick, next_attack[tick, pitch] - e["note"]["length"]))
                at = max(low, min(at, high))
                if at != tick:
                    for e in events:
                        e["time"] = at
                    changed += 1
            else:
                peak = max(e["note"]["velocity"] for e in events)
                level = guide_levels[match]
                goal = level if style == "accent" else peak * (1 - 0.75 * level)
                if peak > 0 and goal != peak:
                    scale = 1 + (goal / peak - 1) * amount / 100
                    for e in events:
                        e["note"]["velocity"] = min(1.0, e["note"]["velocity"] * scale)
                    changed += 1
        if style == "lock":
            for e in events:
                pitch = (e.get("channel", 0), e["note"]["note"])
                releases[pitch] = max(releases.get(pitch, at), at + e["note"]["length"])
    if changed and style == "lock":
        target["eventList"]["events"].sort(key=lambda e: e["time"])
    return changed
