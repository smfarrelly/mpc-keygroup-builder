// SPDX-License-Identifier: MIT
#include "mpc_plugin.h"
#include <algorithm>
#include <array>
#include <cmath>

class ResonantKit final : public mpc::Plugin {
    struct Mode {
        double x = 0, y = 0;
    };
    struct Channel {
        double low = 0, previous = 0, energy = 0;
        std::array<Mode, 3> modes{};
    };
    std::array<Channel, 2> lanes{};
    static mpc::PluginInfo infoForHost() {
        mpc::PluginInfo p;
        p.name = "Resonant Kit";
        p.vendor = "FG Scratchpad";
        p.uniqueId = MPC_FOURCC('F', 'g', 'R', 'K');
        p.numInputs = 2;
        p.version = 1000;
        return p;
    }

  public:
    ResonantKit() : Plugin(infoForHost()) {
        addParam(mpc::intParam("root", "Root", 24, 72, 45, "MIDI"));
        addParam(mpc::logParam("decay", "Decay", 70, 3200, 540, "ms", 0));
        addParam(mpc::floatParam("focus", "Kick to Snare", 0, 100, 50, "%", 0));
        addParam(mpc::floatParam("wet", "Wet", 0, 100, 54, "%", 0));
        addParam(mpc::intParam("middle", "Middle Interval", 1, 24, 7, "st"));
        addParam(mpc::intParam("upper", "Upper Interval", 1, 36, 15, "st"));
    }
    void reset() override { lanes = {}; }
    void process(mpc::ProcessContext &c) override {
        const double sr = c.sampleRate, focus = get(2) * .01, wet = get(3) * .01;
        const double lowAlpha = -std::expm1(-6.2831853 * 160 / sr), fall = std::exp(-1 / (sr * .045));
        std::array<double, 3> co{}, si{}, drive{};
        const int intervals[] = {0, getInt(4), getInt(5)};
        for (int j = 0; j < 3; j++) {
            const double hz = std::min(sr * .42, double(mpc::noteToHz(get(0) + intervals[j])));
            const double a = 6.2831853 * hz / sr;
            const double radius = std::exp(-1 / (sr * .001 * get(1) * (1. - .12 * j)));
            co[j] = radius * std::cos(a);
            si[j] = radius * std::sin(a);
            drive[j] = 2.4 * std::sqrt(hz / sr);
        }
        for (int i = 0; i < c.numFrames; i++)
            for (int ch = 0; ch < 2; ch++) {
                const double dry = c.inputs[ch][i];
                auto &l = lanes[ch];
                l.low += lowAlpha * (dry - l.low);
                const double edge = dry - l.previous, high = dry - l.low;
                l.previous = dry;
                l.energy = std::max(std::abs(dry), fall * l.energy);
                const double accent = std::clamp((l.energy - .15) * 2., 0., 1.);
                const double excitation[] = {l.low * (1.3 - focus), high * (.3 + focus),
                                             (.6 * edge + .4 * high) * (.08 + accent) * (.35 + focus)};
                double ring = 0;
                for (int j = 0; j < 3; j++) {
                    auto &m = l.modes[j];
                    const double x = co[j] * m.x - si[j] * m.y + drive[j] * excitation[j];
                    m.y = si[j] * m.x + co[j] * m.y;
                    m.x = x;
                    ring += m.y;
                }
                c.outputs[ch][i] = static_cast<float>(dry + wet * .85 * std::tanh(ring));
            }
    }
};
MPC_PLUGIN_ENTRY(ResonantKit)
