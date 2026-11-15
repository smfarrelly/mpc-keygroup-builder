// SPDX-License-Identifier: MIT
#pragma once
#include "mpc_plugin.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace percussion {
// An exponentially damped sinusoid. Complex rotation avoids per-sample trig.
struct Partial {
    double x = 0, y = 0, cosine = 0, sine = 0;
    void strike(double hz, double seconds, double level, double sampleRate) {
        const double angle = 6.283185307179586 * std::min(hz, .45 * sampleRate) / sampleRate;
        const double radius = std::exp(-1 / (sampleRate * seconds));
        cosine = radius * std::cos(angle);
        sine = radius * std::sin(angle);
        x = level;
        y = 0;
    }
    double tick() {
        const double next = cosine * x - sine * y;
        y = sine * x + cosine * y;
        x = next;
        return y;
    }
};

// A swung stick excites a fundamental, a bar mode and a short attack mode.
struct Mallet {
    std::array<Partial, 3> modes{};
    double pan = 0, gain = 0, fade = 1;
    int remaining = 0;
    void strike(int note, double strength, double tail, double hardness, double position, double sr) {
        const double hz = mpc::noteToHz(note);
        modes[0].strike(hz, tail, strength, sr);
        modes[1].strike(2.013 * hz, .42 * tail, strength * (.07 + .4 * hardness), sr);
        modes[2].strike(3.97 * hz, .12 * tail, strength * (.04 + .36 * hardness), sr);
        remaining = int(8 * tail * sr);
        pan = position;
        gain = 1;
        fade = 1;
    }
    void damp(double sr) { fade = std::exp(-1 / (.004 * sr)); }
    void add(double &left, double &right) {
        if (remaining <= 0)
            return;
        double value = 0;
        for (auto &mode : modes)
            value += mode.tick();
        gain *= fade;
        value *= gain;
        left += value * (1 - pan);
        right += value * (1 + pan);
        if (--remaining == 0 || gain < .00002)
            remaining = 0;
    }
};
inline double tempo(const mpc::ProcessContext &c) {
    return c.transport.tempoValid && std::isfinite(c.transport.bpm)
               ? std::clamp(c.transport.bpm, 20., 300.)
               : 120.;
}
} // namespace percussion
