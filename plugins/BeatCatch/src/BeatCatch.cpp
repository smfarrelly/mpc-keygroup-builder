#include <algorithm>
// SPDX-License-Identifier: MIT
#include "mpc_plugin.h"
#include <array>
#include <cmath>
#include <vector>

class BeatCatch final : public mpc::Plugin {
  public:
    enum { Catch, Size, Tone, Return };
    BeatCatch() : Plugin(metadata()) {
        addParam(mpc::boolParam("catch", "Catch", false));
        addParam(mpc::choiceParam("size", "Repeat Size",
                                  {"Beat", "Half beat", "Quarter beat", "Eighth beat"}, 0));
        addParam(mpc::logParam("tone", "Tone", 220, 18000, 12000, "Hz", 0));
        addParam(mpc::floatParam("return", "Return", 0, 100, 55, "%", 0));
    }
    void prepare(double rate, int) override {
        capacity = static_cast<int>(std::ceil(rate * 3)) + 1;
        for (auto &b : history)
            b.assign(capacity, 0);
        for (auto &b : frozen)
            b.assign(capacity, 0);
    }
    void reset() override {
        for (auto &b : history)
            std::fill(b.begin(), b.end(), 0);
        write = start = copied = position = length = 0;
        latched = false;
        wet = 0;
        filter = {};
    }
    void process(mpc::ProcessContext &c) override {
        const bool on = get(Catch) > .5f;
        if (on && !latched) {
            const double bpm = c.transport.tempoValid && c.transport.bpm > 0 ? c.transport.bpm : 120;
            length = std::clamp(static_cast<int>(std::lround(c.sampleRate * 60 / std::max(20., bpm))), 1,
                                capacity - 1);
            start = (write + capacity - length) % capacity;
            copied = position = 0;
        }
        latched = on;
        const int window = std::max(1, length >> getInt(Size));
        const int ramp = std::max(1, std::min(window / 4, static_cast<int>(c.sampleRate * .002)));
        const float alpha = -std::expm1(-6.2831853 * get(Tone) / c.sampleRate);
        const float slew = -std::expm1(-1 / (.003 * c.sampleRate));
        for (int i = 0; i < c.numFrames; ++i) {
            // Copy one old frame per incoming frame, keeping callback work bounded on capture.
            position %= window;
            const int read = length - window + position;
            wet += ((on ? get(Return) * .01f : 0.f) - wet) * slew;
            const float edge =
                std::min({1.f, position / float(ramp), (window - 1 - position) / float(ramp)});
            for (int ch = 0; ch < 2; ++ch) {
                const float dry = c.inputs[ch][i];
                float tap = 0;
                if (length) {
                    if (copied < length)
                        frozen[ch][copied] = history[ch][(start + copied) % capacity];
                    tap = read <= copied ? frozen[ch][read] : history[ch][(start + read) % capacity];
                }
                filter[ch] += alpha * (tap * edge - filter[ch]);
                history[ch][write] = dry;
                c.outputs[ch][i] = dry + wet * filter[ch];
            }
            if (copied < length)
                ++copied;
            if (++write == capacity)
                write = 0;
            ++position;
        }
    }

  private:
    static mpc::PluginInfo metadata() {
        mpc::PluginInfo p;
        p.name = "Beat Catch";
        p.vendor = "FG Scratchpad";
        p.uniqueId = MPC_FOURCC('F', 'g', 'B', 'C');
        p.version = 1000;
        p.numInputs = 2;
        return p;
    }
    std::array<std::vector<float>, 2> history, frozen;
    std::array<float, 2> filter{};
    int capacity = 0, write = 0, start = 0, copied = 0, position = 0, length = 0;
    bool latched = false;
    float wet = 0;
};
MPC_PLUGIN_ENTRY(BeatCatch)
