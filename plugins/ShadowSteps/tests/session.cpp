// SPDX-License-Identifier: MIT
#include "../../DrumHands/tests/host.h"
#include "../variation.h"
using namespace testhost;
constexpr int beat = 16000, bar = beat * 4, grid = beat / 4;
const std::vector<Event> strokes = {
    {0, 36, 110}, {grid + 600, 38, 60}, {4 * grid, 37, 105}, {7 * grid, 39, 81}, {10 * grid, 36, 74}};
void scenes() {
    shadow::Groove g{};
    g[0][0] = 110;
    g[0][2] = 65;
    g[3][1] = 77;
    g[15][3] = 90;
    std::array<std::vector<std::array<int, 3>>, 4> expected{
        {{{0, 0, 110}, {0, 2, 65}, {3, 1, 77}, {15, 3, 90}},
         {{0, 0, 110}, {1, 3, 90}, {2, 2, 65}, {3, 1, 77}},
         {{0, 0, 110}, {0, 2, 65}, {1, 67, 82}, {3, 1, 77}, {4, 58, 57}, {15, 3, 90}},
         {{0, 0, 110}, {0, 2, 65}, {2, 72, 67}, {3, 1, 77}, {3, 74, 82}, {6, 65, 57}, {15, 3, 90}}}};
    for (int mode = 0; mode < 4; mode++) {
        std::vector<std::array<int, 3>> notes;
        for (int i = 0; i < 16; i++)
            shadow::step(g, i, mode, 43, [&](shadow::Note n) {
                notes.push_back({i, n.melody ? n.pitch : n.lane, n.velocity});
            });
        assert(notes == expected[mode]);
    }
}
int main(int argc, char **argv) {
    if (argc != 2)
        return 2;
    scenes();
    const char *so = argv[1];
    Bytes saved, blank;
    {
        Plugin p(so);
        blank = p.save();
        p.render(bar, strokes);
        saved = p.save();
        assert(saved != blank);
        // The final sample of the capture publishes the bar without requiring another callback.
        auto first = saved.end() - 64;
        assert(first[0] == 110 && first[1 * 4 + 2] == 60 && first[10 * 4] == 74);
        p.render(beat, {{1, 44, 99}, {21, 38, 111}, {beat - 1, 45, 100}});
        assert(saved == p.save());
    }
    auto listen = [&](int mode, std::vector<Event> events = {}, int block = 128) {
        Plugin p(so, 32000, block);
        p.load(saved);
        p.set(0, mode / 3.f);
        return p.render(bar, events);
    };
    auto original = listen(0);
    assert(energy(original, 0, bar) > 10);
    for (int mode = 1; mode <= 3; mode++) {
        assert(listen(mode) != original);
        assert(listen(0, {{0, 39 + mode, 100}}) == listen(mode));
    }
    // Releasing the last-held variation brings back the previous one.
    auto layered = listen(0, {{0, 40, 100}, {1, 42, 90}, {2, 42, 0, 0x80}});
    // First clock tick was Offbeat; the other gestures occur before the next tick.
    assert(layered == listen(1));
    assert(listen(0, {}, 251) == original);
    Plugin p(so);
    p.load(saved);
    p.render(bar, {{0, 41, 100}, {bar - 1, 41, 0, 0x80}});
    assert(p.save() == saved);
    auto returned = p.render(bar);
    auto ref = listen(0);
    for (int ch = 0; ch < 2; ch++)
        assert(std::equal(ref[ch].end() - beat, ref[ch].end(), returned[ch].end() - beat));
    p.render(bar, {{0, 44, 127}, {0, 39, 35}});
    assert(p.save() != saved);
    p.load(saved);
    p.render(beat, {{0, 44, 90}, {500, 38, 50}});
    p.playing = false;
    p.render(beat);
    assert(saved == p.save());
    // Begin halfway through a looping sequence and finish the take across its seam.
    Plugin wrapped(so);
    wrapped.cycleEnd = 4;
    wrapped.render(bar, {{2 * beat, 47, 105}, {2 * beat + grid, 47, 104}, {3 * beat, 47, 79}});
    wrapped.position = 0;
    wrapped.render(2 * beat, {{grid, 47, 47}});
    auto loop = wrapped.save();
    auto rows = loop.end() - 64;
    assert(rows[8 * 4] == 105 && rows[9 * 4 + 1] == 104 && rows[12 * 4 + 2] == 79 && rows[4 + 3] == 47);
    // An armed but silent replacement keeps the old take.
    wrapped.render(bar, {{0, 35, 100}});
    assert(loop == wrapped.save());
    Plugin pickup(so);
    pickup.render(bar, {{0, 35, 100}, {10 * grid, 39, 87}});
    assert((pickup.save().end() - 64)[10 * 4 + 3] == 87);
    Plugin free(so, 48000, 257);
    free.playing = false;
    free.render(96000 + 375, {{375, 36, 99}});
    assert(free.save() != blank);
    std::cout << "Four scene scores, audible variations, hold stack, cancel, replace, free clock and "
                 "project recall passed.\n";
}
