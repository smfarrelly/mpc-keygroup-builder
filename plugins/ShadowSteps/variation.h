// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>

namespace shadow {
using Groove = std::array<std::array<uint8_t, 4>, 16>;
enum Scene { Original, Offbeat, Holes, Canon };
struct Note {
    int lane, pitch, velocity;
    bool melody;
};

// Both the instrument and the MIDI printer play this score one sixteenth at a time.
template <class Play> void step(const Groove &groove, int cell, int scene, int root, Play play) {
    constexpr int intervals[] = {0, 3, 7, 10};
    bool occupied = false;
    for (int lane = 0; lane < 4; lane++) {
        // Preserve the low pulse and backbeat. Carry the two higher voices an eighth later.
        const int source = scene == Offbeat && lane >= 2 ? (cell + 14) % 16 : cell;
        const int vel = groove[source][lane];
        if (vel) {
            occupied = true;
            play(Note{lane, root + intervals[lane], vel, false});
        }
    }
    if (scene != Canon && (scene != Holes || occupied))
        return;
    const auto &source = groove[(cell + (scene == Canon ? 13 : 15)) % 16];
    // An accented stroke wins the reply. Ties belong to the lower drum.
    int lane = int(std::max_element(source.begin(), source.end()) - source.begin());
    const int strength = source[lane];
    if (!strength)
        return;
    const int pitch =
        root + 12 + (scene == Canon ? 7 : 0) + intervals[lane] + (strength >= 105 ? 12 : 0);
    play(Note{lane, pitch, std::max(1, strength * 3 / 4), true});
}
} // namespace shadow
