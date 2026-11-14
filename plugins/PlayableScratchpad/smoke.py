"""Exercise audible behavior without an MPC or licensed audio."""

import struct
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from audio import RATE, compile_probe, render, values


def check(sdk, scratch):
    probe = compile_probe(sdk, scratch)

    def play(plugin, actions, frames=RATE, **kwargs):
        return values(render(probe, scratch, plugin, frames, actions, **kwargs))[::2]

    def strike(note, velocity=100, settings=()):
        return play("PocketLayers", [*settings, (0, "on", note, velocity)])

    kick = strike(36)
    assert max(kick) > 1000
    # Crossing the accent boundary changes timbre even after gain compensation.
    ghost, accent = strike(38, 95), strike(38, 96)
    assert max(abs(a / 95 - b / 96) for a, b in zip(ghost, accent)) > 25
    repeat = play(
        "PocketLayers", [(0, "on", 36, 100), (2 * RATE, "on", 36, 100)], 3 * RATE
    )
    assert (
        kick[:5000] == repeat[:5000]
        and kick[:5000] != repeat[2 * RATE : 2 * RATE + 5000]
    )
    assert sum(map(abs, strike(36, settings=[(0, "set", 1, 0)])[6000:])) < sum(
        map(abs, kick[6000:])
    )
    open_hat = strike(45)
    assert sum(map(abs, strike(45, settings=[(0, "set", 2, 0)])[8000:])) < sum(
        map(abs, open_hat[8000:])
    )
    # Subtract a solo closed hat to isolate the ring of the choked open hat.
    cut = play("PocketLayers", [(0, "on", 45, 100), (RATE // 4, "on", 44, 100)])
    closed = play("PocketLayers", [(RATE // 4, "on", 44, 100)])
    assert max(abs(a - b) for a, b in zip(cut[RATE // 3 :], closed[RATE // 3 :])) < 3
    assert max(open_hat[RATE // 3 :]) > 100
    keys = [
        (0, "on", 60, 100),
        (RATE, "on", 67, 80),
        (RATE + 200, "off", 60, 0),
        (2 * RATE, "off", 67, 0),
    ]
    bloom = play("BloomKeys", keys, 3 * RATE)
    zero_crossings = sum(
        a <= 0 < b for a, b in zip(bloom[8000:30000], bloom[8001:30001])
    )
    assert abs(zero_crossings * RATE / 22000 - 130.8) < 4
    assert max(bloom[RATE // 2 : RATE]) > 2000 and max(map(abs, bloom[-1000:])) < 10
    glide = play("BloomKeys", [(0, "set", 2, 0), *keys], 3 * RATE)
    assert (
        glide[:RATE] == bloom[:RATE]
        and glide[RATE : RATE + 4400] != bloom[RATE : RATE + 4400]
    )
    beat = RATE // 2
    source = bytearray(beat * 4 * 4)
    for frame, left, right in [(beat - 2000, 13000, -7000), (beat + 100, -3000, 8000)]:
        struct.pack_into("<hh", source, frame * 4, left, right)
    path = scratch / "stereo.pcm"
    path.write_bytes(source)

    def catch(actions):
        return render(
            probe, scratch, "BeatCatch", 4 * beat, actions, source=path, bpm=120
        )

    assert catch([]) == source
    for division in range(4):
        fx = values(
            catch(
                [
                    (beat, "set", 1, division),
                    (beat, "set", 0, 1),
                    (3 * beat, "set", 0, 0),
                ]
            )
        )
        window = beat >> division
        for i in range(1, 3):
            frame = (beat + i * window - 2000) * 2
            assert fx[frame] > 500 and fx[frame + 1] < -250
        assert fx[(beat + 100) * 2 : (beat + 101) * 2].tolist() == [-3000, 8000]
        assert max(map(abs, fx[-2000:])) < 3
    print(
        "Passed drum layers, variation, chokes and decay; key register, sustain, release and glide; "
        "stereo dry path, capture, four divisions, release and parameter recall."
    )


if __name__ == "__main__":
    with TemporaryDirectory() as tmp:
        check(Path(sys.argv[1]).resolve(), Path(tmp))
