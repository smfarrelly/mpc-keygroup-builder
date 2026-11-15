// SPDX-License-Identifier: MIT
#include "mpc_plugin.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <mutex>

class ChordRelay final : public mpc::Plugin {
    using Chord = std::array<unsigned char, 6>;
    using Bank = std::array<Chord, 2>;
    Bank bank{{Chord{60, 63, 67, 70}, Chord{56, 60, 63, 67}}}, saved = bank;
    std::mutex mutex;
    bool pending = false, dirty = false, wasTeaching = false;
    std::array<bool, 128> keys{};
    struct Voice {
        int delay = 0, gate = 0;
        double phase = 0, step = 0, level = 0, attack = 0;
    };
    std::array<Voice, 128> voices{};
    std::array<int, 2> inner{};
    int previous = -1;
    static mpc::PluginInfo metadata() {
        mpc::PluginInfo p;
        p.name = "Chord Relay";
        p.vendor = "FG Scratchpad";
        p.isInstrument = true;
        p.numInputs = 0;
        p.uniqueId = MPC_FOURCC('F', 'g', 'C', 'R');
        p.version = 1000;
        return p;
    }
    void strike(int note, int velocity, int delay, double rate, bool legato) {
        auto &v = voices[note];
        const int gate = int(rate * .20);
        if (legato && v.level > 0 && v.delay == 0 && v.gate > 0) {
            v.gate = gate;
            return;
        }
        v = {delay, gate, 0, 6.283185307179586 * mpc::noteToHz(note) / rate, velocity / 127., 0};
    }
    void trigger(const mpc::MidiEvent &e, bool teach, double sr) {
        if (e.isAllNotesOff()) {
            reset();
            return;
        }
        const int note = e.note();
        if (note > 127)
            return;
        if (teach && note >= 48) {
            if (e.isNoteOn()) {
                keys[note] = true;
                strike(note, e.velocity(), 0, sr, false);
            }
            if (e.isNoteOff()) {
                keys[note] = false;
                voices[note].gate = 0;
            }
            return;
        }
        if (!e.isNoteOn() || note < 36 || note > 42 || note == 39)
            return;
        const int slot = (note - 36) / 4, gesture = (note - 36) % 4;
        auto &chord = bank[slot];
        if (teach) {
            Chord next{};
            int count = 0;
            for (int n = 48; n < 128 && count < 6; n++)
                if (keys[n])
                    next[count++] = n;
            if (count) {
                chord = next;
                dirty = true;
            }
            return;
        }
        const int count = std::find(chord.begin(), chord.end(), 0) - chord.begin();
        int index = -1;
        if (e.velocity() < 50) {
            index = count - 1;
        } else if (gesture == 1) {
            const int choices = std::max(1, count - 2);
            index = count < 3 ? 0 : 1 + inner[slot] % choices;
            inner[slot] = (inner[slot] + 1) % choices;
        }
        const bool moving = previous >= 0 && previous != slot;
        for (int n = 0; n < 128; n++) {
            auto &v = voices[n];
            if (v.delay > 0)
                v = {};
            if (moving && std::find(chord.begin(), chord.end(), n) == chord.end())
                v.gate = 0;
        }
        for (int i = 0; i < count; i++)
            if (index < 0 || i == index)
                strike(chord[i], e.velocity(),
                       gesture == 2 && index < 0 ? int(sr * .001 * get(1) * i / std::max(1, count - 1))
                                                 : 0,
                       sr, moving);
        previous = slot;
    }
    void sync() {
        std::unique_lock<std::mutex> lock(mutex, std::try_to_lock);
        if (!lock)
            return;
        if (pending) {
            bank = saved;
            pending = false;
            dirty = false;
            reset();
        } else if (dirty) {
            saved = bank;
            dirty = false;
        }
    }

  public:
    ChordRelay() : Plugin(metadata()) {
        addParam(mpc::boolParam("teach", "Teach", false));
        addParam(mpc::floatParam("spread", "Spread", 0, 240, 90, "ms", 0));
        addParam(mpc::logParam("release", "Release", 40, 1800, 350, "ms", 0));
        addParam(mpc::floatParam("brightness", "Brightness", 0, 100, 45, "%", 0));
    }
    void reset() override {
        voices = {};
        keys = {};
        inner = {};
        previous = -1;
    }
    void process(mpc::ProcessContext &c) override {
        sync();
        const bool teach = getBool(0);
        if (teach != wasTeaching)
            reset();
        wasTeaching = teach;
        const double decay = std::exp(-1 / (c.sampleRate * get(2) * .001)), bright = .003 * get(3),
                     attack = 1. / (.004 * c.sampleRate);
        int event = 0;
        for (int i = 0; i < c.numFrames; i++) {
            while (event < c.numMidiEvents && c.midi[event].sampleOffset <= i)
                trigger(c.midi[event++], teach, c.sampleRate);
            double sum = 0;
            for (auto &v : voices) {
                if (v.level == 0)
                    continue;
                if (v.delay) {
                    v.delay--;
                    continue;
                }
                if (v.gate > 0)
                    v.gate--;
                else
                    v.level *= decay;
                if (v.level < .00005) {
                    v = {};
                    continue;
                }
                v.attack = std::min(1., v.attack + attack);
                sum += v.attack * v.level *
                       (std::sin(v.phase) + (v.step < 1.04 ? bright * std::sin(3 * v.phase) : 0));
                v.phase = std::fmod(v.phase + v.step, 6.283185307179586);
            }
            c.outputs[0][i] = c.outputs[1][i] = std::tanh(.21 * sum);
        }
        sync();
    }
    void saveExtraState(std::vector<uint8_t> &out) override {
        std::lock_guard<std::mutex> lock(mutex);
        out.push_back(1);
        for (auto &chord : saved)
            out.insert(out.end(), chord.begin(), chord.end());
    }
    void loadExtraState(const uint8_t *data, size_t size) override {
        if (size != 13 || data[0] != 1)
            return;
        Bank next{};
        for (auto &chord : next) {
            bool done = false;
            int last = 0;
            for (auto &n : chord) {
                n = *++data;
                if (!n) {
                    done = true;
                    continue;
                }
                if (done || n < 48 || n > 127 || n <= last)
                    return;
                last = n;
            }
            if (!last)
                return;
        }
        std::lock_guard<std::mutex> lock(mutex);
        saved = next;
        pending = true;
    }
};
MPC_PLUGIN_ENTRY(ChordRelay)
