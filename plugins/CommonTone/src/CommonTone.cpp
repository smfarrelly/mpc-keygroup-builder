// SPDX-License-Identifier: MIT
#include "../../DrumHands/percussion.h"
#include <atomic>

class CommonTone final : public mpc::Plugin {
    enum { Lead, Bed, Pulse, Release };
    struct Chord {
        int anchor = 0, shape = 0;
        std::array<int, 4> pitches() const {
            constexpr int intervals[][4] = {{-12, -9, -2, 0}, {-16, -9, -5, 0}, {-14, -10, -4, 0}};
            std::array<int, 4> result{};
            for (int i = 0; i < 4; i++)
                result[i] = anchor + intervals[shape][i];
            return result;
        }
        unsigned pack() const { return unsigned(anchor | (shape << 7)); }
        static Chord unpack(unsigned value) { return {int(value & 127), int(value >> 7)}; }
    };
    // A single publication includes both harmonic memories for project serialization.
    std::atomic<uint32_t> slots{0};
    struct Osc {
        int key = 0;
        double x = 0, y = 0, co = 0, si = 0, amp = 0, target = 0, pan = 0;
    };
    std::array<Osc, 12> bed{};
    struct Tap {
        percussion::Mallet mallet;
        int key = 0;
        bool pulse = false;
    };
    std::array<Tap, 16> taps{};
    std::array<bool, 128> down{};
    std::array<Chord, 3> preview{};
    std::array<int, 3> held{};
    int heldCount = 0, melody = 67, next = 0;
    Chord pinned{};
    bool pedal = false, wasPlaying = false;
    double expected = 0;
    static mpc::PluginInfo metadata() {
        mpc::PluginInfo p;
        p.name = "Common Tone";
        p.vendor = "FG Scratchpad";
        p.isInstrument = true;
        p.numInputs = 0;
        p.uniqueId = MPC_FOURCC('F', 'g', 'C', 't');
        p.version = 1000;
        return p;
    }
    Chord current() const { return heldCount ? preview[held[heldCount - 1]] : pinned; }
    void voiceChord(double sr) {
        for (auto &v : bed)
            v.target = 0;
        const auto chord = current();
        if (!chord.anchor)
            return;
        auto pitches = chord.pitches();
        // Reserve common tones first, so adding a new note never steals a shared note.
        for (auto &v : bed)
            if (v.key && std::find(pitches.begin(), pitches.end(), v.key) != pitches.end())
                v.target = 1;
        for (int key : pitches) {
            if (std::any_of(bed.begin(), bed.end(), [&](const Osc &v) { return v.key == key; }))
                continue;
            auto slot = std::min_element(bed.begin(), bed.end(), [](const Osc &a, const Osc &b) {
                return a.target + a.amp < b.target + b.amp;
            });
            const double angle = 6.283185307179586 * mpc::noteToHz(key) / sr;
            *slot = {key, 1, 0, std::cos(angle), std::sin(angle), 0, 1, (key % 5 - 2) * .075};
        }
    }
    void tap(int key, int vel, bool pulse, double sr) {
        auto &v = taps[next];
        next = (next + 1) % int(taps.size());
        v.key = key;
        v.pulse = pulse;
        v.mallet.strike(key, (pulse ? .22 : .52) * vel / 127., pulse ? .12 : .48, vel / 127.,
                        (key % 5 - 2) * .07, sr);
    }
    void input(const mpc::MidiEvent &e, double sr) {
        if (e.isAllNotesOff()) {
            quiet();
            return;
        }
        if (e.isController() && e.controller() == 64) {
            pedal = e.controllerValue() >= 64;
            if (!pedal)
                for (auto &v : taps)
                    if (!v.pulse && !down[v.key])
                        v.mallet.damp(sr);
            return;
        }
        const int key = e.note();
        if (key > 127)
            return;
        if (e.isNoteOff()) {
            if (key >= 48) {
                down[key] = false;
                if (!pedal)
                    for (auto &v : taps)
                        if (!v.pulse && v.key == key)
                            v.mallet.damp(sr);
            } else if (key >= 36 && key <= 38) {
                auto it = std::find(held.begin(), held.begin() + heldCount, key - 36);
                if (it != held.begin() + heldCount) {
                    std::move(it + 1, held.begin() + heldCount, it);
                    --heldCount;
                    voiceChord(sr);
                }
            }
            return;
        }
        if (!e.isNoteOn())
            return;
        if (key >= 48) {
            melody = key;
            down[key] = true;
            tap(key, e.velocity(), false, sr);
            return;
        }
        if (key >= 36 && key <= 38) {
            const int shape = key - 36;
            preview[shape] = {melody, shape};
            auto it = std::find(held.begin(), held.begin() + heldCount, shape);
            if (it != held.begin() + heldCount) {
                std::move(it + 1, held.begin() + heldCount, it);
                --heldCount;
            }
            held[heldCount++] = shape;
            voiceChord(sr);
        } else if (key == 39) {
            const auto chord = current();
            if (chord.anchor)
                for (int n : chord.pitches())
                    tap(n, e.velocity(), true, sr);
        } else if (key == 40 || key == 41) {
            auto chord = Chord::unpack((slots.load() >> (16 * (key - 40))) & 65535);
            if (chord.anchor) {
                pinned = chord;
                heldCount = 0;
                voiceChord(sr);
            }
        } else if (key == 42 || key == 43) {
            auto chord = current();
            if (!chord.anchor)
                return;
            unsigned shift = 16 * (key - 42);
            auto value = slots.load();
            slots.store((value & ~(0xffffu << shift)) | (chord.pack() << shift));
        } else if (key == 44) {
            pinned = {};
            heldCount = 0;
            voiceChord(sr);
        }
    }
    void quiet() {
        pinned = {};
        heldCount = 0;
        bed = {};
        taps = {};
        down = {};
        pedal = false;
        next = 0;
    }

  public:
    CommonTone() : Plugin(metadata()) {
        addParam(mpc::floatParam("lead", "Lead Level", 0, 100, 72, "%", 0));
        addParam(mpc::floatParam("bed", "Chord Level", 0, 100, 65, "%", 0));
        addParam(mpc::floatParam("pulse", "Pulse Level", 0, 100, 80, "%", 0));
        addParam(mpc::logParam("release", "Release", 30, 1200, 240, "ms", 0));
        addProgram("Under the melody", {72, 65, 80, 240});
        addProgram("Rhythm chords", {65, 0, 95, 85});
        addProgram("Slow harmony", {52, 76, 46, 750});
    }
    void reset() override {
        quiet();
        melody = 67;
        wasPlaying = false;
        expected = 0;
    }
    void process(mpc::ProcessContext &c) override {
        const bool playing = c.transport.valid && c.transport.playing;
        if (wasPlaying &&
            (!playing || (c.transport.ppqValid && std::abs(expected - c.transport.ppqPos) > .025)))
            quiet();
        wasPlaying = playing;
        expected = c.transport.ppqPos + c.numFrames * percussion::tempo(c) / (60 * c.sampleRate);
        int event = 0;
        const double attack = -std::expm1(-1 / (.022 * c.sampleRate)),
                     release = -std::expm1(-1 / (.001 * get(Release) * c.sampleRate));
        const double lead = .01 * get(Lead), pulse = .01 * get(Pulse), pad = .115 * .01 * get(Bed);
        for (int i = 0; i < c.numFrames; i++) {
            while (event < c.numMidiEvents && c.midi[event].sampleOffset <= i)
                input(c.midi[event++], c.sampleRate);
            double l = 0, r = 0;
            for (auto &v : bed) {
                if (!v.key)
                    continue;
                v.amp += (v.target - v.amp) * (v.target ? attack : release);
                if (!v.target && v.amp < .00003) {
                    v = {};
                    continue;
                }
                const double x = v.co * v.x - v.si * v.y;
                v.y = v.si * v.x + v.co * v.y;
                v.x = x;
                const double value = pad * v.amp * v.y * (1 + .32 * v.x);
                l += value * (1 - v.pan);
                r += value * (1 + v.pan);
            }
            for (auto &v : taps) {
                double a = 0, b = 0;
                v.mallet.add(a, b);
                const double g = v.pulse ? pulse : lead;
                l += g * a;
                r += g * b;
            }
            c.outputs[0][i] = std::tanh(l);
            c.outputs[1][i] = std::tanh(r);
        }
    }
    void saveExtraState(std::vector<uint8_t> &out) override {
        auto value = slots.load();
        out.push_back(1);
        for (int k = 0; k < 4; k++)
            out.push_back(uint8_t(value >> (8 * k)));
    }
    void loadExtraState(const uint8_t *data, size_t n) override {
        if (n != 5 || data[0] != 1)
            return;
        uint32_t result = 0;
        for (int k = 0; k < 2; k++) {
            unsigned word = data[1 + 2 * k] | (unsigned(data[2 + 2 * k]) << 8);
            Chord chord = Chord::unpack(word);
            if (word && (chord.anchor < 48 || chord.shape > 2))
                return;
            result |= word << (16 * k);
        }
        slots.store(result);
    }
};
MPC_PLUGIN_ENTRY(CommonTone)
