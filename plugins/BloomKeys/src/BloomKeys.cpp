// SPDX-License-Identifier: MIT
#include "mpc_plugin.h"
#include <array>
#include <cmath>

class BloomKeys final : public mpc::Plugin {
  public:
    enum { Bloom, Time, Glide, Bright };
    BloomKeys() : Plugin(metadata()) {
        addParam(mpc::floatParam("bloom", "Bloom", 0, 100, 68, "%", 0));
        addParam(mpc::logParam("time", "Bloom Time", 60, 3000, 800, "ms", 0));
        addParam(mpc::floatParam("glide", "Glide", 0, 500, 85, "ms", 0));
        addParam(mpc::floatParam("bright", "Brightness", 0, 100, 52, "%", 0));
    }
    void prepare(double sampleRate, int) override { rate = sampleRate; }
    void reset() override {
        count = 0;
        phase = motion = pluck = body = level = 0;
        pitch = target = 48;
    }
    void process(mpc::ProcessContext &c) override {
        const double glideMs = get(Glide);
        const double glide = glideMs > 0 ? -std::expm1(-1000 / (rate * glideMs)) : 1;
        const double bloom = -std::expm1(-1000 / (rate * get(Time)));
        const double attack = -std::expm1(-1 / (rate * .003));
        const double release = -std::expm1(-1 / (rate * .12));
        const double decay = std::exp(-1 / (rate * .18));
        const double depth = get(Bloom) * .01, color = get(Bright) * .01;
        int event = 0;
        for (int i = 0; i < c.numFrames; ++i) {
            while (event < c.numMidiEvents && c.midi[event].sampleOffset <= i)
                handle(c.midi[event++]);
            pitch += (target - pitch) * glide;
            const double hz = mpc::noteToHz(static_cast<float>(pitch));
            const double step = std::min(.47, hz / rate);
            phase += step;
            phase -= std::floor(phase);
            motion += .32 / rate;
            motion -= std::floor(motion);
            pluck *= decay;
            body += ((count ? 1.0 : 0.0) - body) * bloom;
            level += ((count ? velocity : 0) - level) * (count ? attack : release);
            const double a = 6.283185307179586 * phase;
            const double warmth = body * depth;
            double voice = (.45 + .3 * pluck) * std::sin(a);
            if (step * 2 < .49)
                voice += (.20 * pluck * color + .16 * warmth) * std::sin(2 * a);
            if (step * 3 < .49)
                voice += (.20 * pluck * color + .19 * warmth) *
                         std::sin(3 * a + .25 * std::sin(6.283185307179586 * motion));
            const float sample = static_cast<float>(voice * level * .65);
            c.outputs[0][i] = c.outputs[1][i] = sample;
        }
    }

  private:
    static mpc::PluginInfo metadata() {
        mpc::PluginInfo p;
        p.name = "Bloom Keys";
        p.vendor = "FG Scratchpad";
        p.uniqueId = MPC_FOURCC('F', 'g', 'B', 'K');
        p.version = 1000;
        p.isInstrument = true;
        p.numInputs = 0;
        return p;
    }
    void remove(int note) {
        for (int i = 0; i < count; ++i)
            if (held[i] == note) {
                for (int j = i + 1; j < count; ++j) {
                    held[j - 1] = held[j];
                    strengths[j - 1] = strengths[j];
                }
                --count;
                break;
            }
    }
    void handle(const mpc::MidiEvent &e) {
        if (e.isAllNotesOff()) {
            count = 0;
            return;
        }
        if (!e.isNoteOn() && !e.isNoteOff())
            return;
        bool legato = count > 0;
        remove(e.note());
        if (e.isNoteOn()) {
            held[count] = e.note();
            strengths[count] = e.velocity() / 127.;
            ++count;
            if (!legato) {
                pitch = e.note() - 12;
                pluck = 1;
                body = 0;
            }
        }
        if (count) {
            target = held[count - 1] - 12;
            velocity = strengths[count - 1];
        }
    }
    std::array<int, 128> held{};
    std::array<double, 128> strengths{};
    int count = 0;
    double rate = 44100, pitch = 48, target = 48, phase = 0, motion = 0, pluck = 0, body = 0, level = 0,
           velocity = 0;
};
MPC_PLUGIN_ENTRY(BloomKeys)
