// SPDX-License-Identifier: MIT
#include "mpc_plugin.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <mutex>

// Store decisions (including ghost velocities and generated pickups) in musical time.
class PocketDuo final : public mpc::Plugin {
    static constexpr int PPQ = 960, Capacity = 1024;
    struct Hit {
        uint16_t tick = 0, gate = 0;
        uint8_t key = 0, velocity = 0;
    }; // gate=0 is a drum
    struct Pass {
        std::array<Hit, Capacity> hits{};
        int count = 0, length = 4 * PPQ;
        bool full = false;
        void clear(int ticks) {
            count = 0;
            length = ticks;
            full = false;
        }
        void add(Hit hit) {
            if (count < Capacity)
                hits[count++] = hit;
            else
                full = true;
        }
    };
    struct Memory {
        Pass kept;
        std::array<uint8_t, 8> pitches{36, 43, 39};
        int size = 3;
    };
    struct Voice {
        double phase = 0, level = 0, decay = 0, hz = 0, bend = 0;
        uint32_t noise = 1;
    };
    Memory memory, shared;
    Pass current, previous;
    std::mutex stateMutex;
    bool pendingLoad = false, dirty = false, locked = false, wasKeep = false, learning = false,
         playing = false, awake = false;
    double rate = 44100, phase = 0, expectedPpq = 0, step = 0, bassPhase = 0, bassLevel = 0, bassHz = 0,
           bassGate = 0, pickupIn = -1;
    int reader = 0, pitchStep = 0, kicks = 0, lastBass = 36, learned = 0, pickupKey = 0,
        pickupVelocity = 0;
    std::array<Voice, 16> drums{};
    double attackDecay = 0, releaseDecay = 0;
    enum { Activity, Learn, Keep, Replace, Bars, BassMix, DrumMix };
    static mpc::PluginInfo metadata() {
        mpc::PluginInfo p;
        p.name = "Pocket Duo";
        p.vendor = "FG Scratchpad";
        p.uniqueId = MPC_FOURCC('F', 'g', 'P', 'D');
        p.version = 1000;
        p.isInstrument = true;
        p.numInputs = 0;
        return p;
    }
    int length() const { return 4 * PPQ * (1 << getInt(Bars)); }
    int tick() const { return static_cast<int>(phase); }
    void quiet() {
        drums = {};
        bassLevel = 0;
        bassGate = 0;
        pickupIn = -1;
    }
    void syncState() {
        // Only the UI thread may wait. The audio thread retries at the next block.
        std::unique_lock<std::mutex> guard(stateMutex, std::try_to_lock);
        if (!guard)
            return;
        if (pendingLoad) {
            memory = shared;
            pendingLoad = false;
            dirty = false;
            reset();
        } else if (dirty) {
            shared = memory;
            dirty = false;
        }
    }
    void position(double ticks, int period) {
        phase = std::fmod(ticks, period);
        if (phase < 0)
            phase += period;
        reader = 0;
        while (reader < memory.kept.count && memory.kept.hits[reader].tick < tick())
            ++reader;
    }
    void drum(int key, int vel) {
        int pad = key - 36;
        if (pad == 6 || pad == 7) {
            drums[6].level = 0;
            drums[7].level = 0;
        }
        auto &v = drums[pad];
        const bool kick = pad < 2;
        constexpr double pitch[] = {48, 56,  178, 215, 310, 680,  5700, 5700,
                                    94, 121, 155, 204, 860, 3800, 534,  712};
        constexpr double tails[] = {.15, .21, .085, .125, .11, .042, .033, .23,
                                    .20, .18, .15,  .13,  .07, .42,  .11,  .08};
        v.phase = 0;
        v.level = vel / 127.;
        v.hz = pitch[pad];
        v.bend = kick ? 135 : 18;
        v.noise = uint32_t((pad + 1) * 197 + vel);
        const double tail = tails[pad];
        v.decay = std::exp(-1 / (rate * tail));
    }
    void voice(Hit h) {
        if (h.gate == 0) {
            drum(h.key, h.velocity);
            return;
        }
        bassPhase = 0;
        bassHz = mpc::noteToHz(h.key);
        bassLevel = h.velocity / 127.;
        bassGate = h.gate;
    }
    void remember(int key, int vel, int gate) {
        Hit hit{uint16_t(tick()), uint16_t(gate), uint8_t(key), uint8_t(vel)};
        current.add(hit);
        voice(hit);
    }
    void input(const mpc::MidiEvent &e) {
        if (e.isAllNotesOff()) {
            quiet();
            return;
        }
        if (!e.isNoteOn())
            return;
        const int key = e.note(), vel = e.velocity();
        if (learning) {
            if (learned < 8) {
                memory.pitches[learned++] = key;
                memory.size = learned;
                pitchStep = 0;
                lastBass = memory.pitches[0];
                dirty = true;
            }
            return;
        }
        if (key < 36 || key > 51)
            return;
        if (locked) {
            if (get(Replace) > .5f)
                drum(key, vel);
            return;
        }
        awake = true;
        remember(key, vel, 0);
        if (key > 37)
            return;
        pickupIn = -1;
        const float activity = get(Activity);
        const bool ghost = vel < 50;
        const bool skip = kicks == 1;
        kicks = (kicks + 1) % 2;
        if (skip && activity < 30 && !ghost)
            return;
        if (!ghost) {
            lastBass = memory.pitches[pitchStep % memory.size];
            if (!ghost)
                pitchStep = (pitchStep + 1) % memory.size;
        }
        remember(lastBass, vel, ghost ? 120 : activity < 45 ? 900 : 500);
        if (!ghost && vel >= 100 && activity >= 75) {
            pickupIn = PPQ * .5;
            pickupKey = memory.pitches[pitchStep % memory.size];
            pickupVelocity = vel * 2 / 3;
        }
    }

  public:
    PocketDuo() : Plugin(metadata()) {
        addParam(mpc::intParam("activity", "Bass Activity", 0, 100, 55, "%"));
        addParam(mpc::boolParam("learn", "Learn Pitches", false));
        addParam(mpc::boolParam("keep", "Keep Pass", false));
        addParam(mpc::boolParam("live", "Live Drums", false));
        addParam(mpc::choiceParam("bars", "Pass Length", {"1 bar", "2 bars", "4 bars"}, 0));
        addParam(mpc::floatParam("bass", "Bass Level", 0, 100, 65, "%", 0));
        addParam(mpc::floatParam("drums", "Drum Level", 0, 100, 72, "%", 0));
    }
    void prepare(double sr, int) override {
        rate = sr;
        attackDecay = std::exp(-1 / (rate * .024));
        releaseDecay = std::exp(-1 / (rate * .023));
    }
    void reset() override {
        quiet();
        current.clear(length());
        previous.clear(length());
        phase = 0;
        reader = pitchStep = kicks = learned = 0;
        awake = playing = learning = false;
        wasKeep = get(Keep) > .5f;
        locked = wasKeep && memory.kept.count;
        lastBass = memory.pitches[0];
    }
    void process(mpc::ProcessContext &c) override {
        syncState();
        const bool keep = get(Keep) > .5f, learn = get(Learn) > .5f;
        const bool host = c.transport.valid && c.transport.playing;
        const bool positioned = host && c.transport.ppqValid && std::isfinite(c.transport.ppqPos);
        const double bpm = c.transport.tempoValid && std::isfinite(c.transport.bpm)
                               ? std::clamp(c.transport.bpm, 20., 300.)
                               : 120.;
        step = PPQ * bpm / (60 * rate);
        bool reposition = false;
        if (keep && !wasKeep) {
            // Preserve the completed pass; before its first boundary keep the partial first pass.
            const Pass &chosen = previous.count ? previous : current;
            if (chosen.count && !chosen.full) {
                memory.kept = chosen;
                dirty = true;
            }
            if (!chosen.full && memory.kept.count) {
                locked = true;
                quiet();
                reposition = true;
                awake = true;
            } else
                set(Keep, 0);
        } else if (!keep && locked) {
            locked = false;
            current.clear(length());
            previous.clear(length());
            quiet();
            reposition = true;
            pitchStep = kicks = 0;
        }
        wasKeep = get(Keep) > .5f;
        if (current.length != length() && !locked) {
            current.clear(length());
            previous.clear(length());
            reposition = true;
        }
        if (learn && !learning)
            learned = 0;
        learning = learn;
        const int period = locked ? memory.kept.length : current.length;
        if (host != playing || (positioned && std::abs(c.transport.ppqPos - expectedPpq) > .015)) {
            // Retain the last finished pass across a host loop/seek; do not splice partial takes.
            if (playing && !locked && current.count && !previous.count)
                previous = current;
            if (!locked)
                current.clear(length());
            quiet();
            awake = host;
            reposition = true;
        }
        if (reposition)
            position(positioned ? c.transport.ppqPos * PPQ : 0, period);
        playing = host;
        if (positioned)
            expectedPpq = c.transport.ppqPos + c.numFrames * step / PPQ;
        const double bassMix = get(BassMix) * .0045, drumMix = get(DrumMix) * .005;
        int event = 0;
        for (int i = 0; i < c.numFrames; ++i) {
            while (event < c.numMidiEvents && c.midi[event].sampleOffset <= i)
                input(c.midi[event++]);
            if (locked && (awake || host)) {
                while (reader < memory.kept.count && memory.kept.hits[reader].tick <= tick()) {
                    const auto h = memory.kept.hits[reader++];
                    if (h.gate || get(Replace) < .5f)
                        voice(h);
                }
            } else if (!locked && pickupIn >= 0) {
                if (pickupIn <= step) {
                    remember(pickupKey, pickupVelocity, 180);
                    pickupIn = -1;
                } else
                    pickupIn -= step;
            }
            double mix = 0;
            for (size_t j = 0; j < drums.size(); ++j) {
                auto &v = drums[j];
                if (v.level < .00002)
                    continue;
                v.noise = v.noise * 1664525u + 1013904223u;
                const double noise = v.noise / 2147483648. - 1;
                const double tone = std::sin(v.phase);
                float transient;
                if (j < 2)
                    transient = tone;
                else if (j == 6 || j == 7 || j == 13)
                    transient = noise * .54;
                else if (j >= 8 && j <= 11)
                    transient = tone * .83 + noise * .10;
                else if (j == 5 || j >= 14)
                    transient = tone * .60 + .23 * std::sin(1.61 * v.phase);
                else
                    transient = tone * .37 + noise * .55;
                mix += v.level * transient;
                v.phase += 6.283185307 * (v.hz + v.bend) / rate;
                v.bend *= attackDecay;
                v.level *= v.decay;
            }
            double bass = 0;
            if (bassLevel > .00002) {
                bass = (std::sin(bassPhase) + .20 * std::sin(2 * bassPhase)) * bassLevel;
                bassPhase += 6.283185307 * bassHz / rate;
                bassGate -= step;
                if (bassGate <= 0)
                    bassLevel *= releaseDecay;
            }
            c.outputs[0][i] = c.outputs[1][i] = float(std::tanh(mix * drumMix + bass * bassMix));
            if (awake || host) {
                phase += step;
                if (phase + 1e-8 >= period) {
                    phase = std::max(0., phase - period);
                    reader = 0;
                    if (!locked) {
                        if (current.count)
                            previous = current;
                        current.clear(length());
                    }
                }
            }
        }
        if (dirty)
            syncState();
    }
    void saveExtraState(std::vector<uint8_t> &out) override {
        std::lock_guard<std::mutex> guard(stateMutex);
        auto word = [&](int n) {
            out.push_back(uint8_t(n));
            out.push_back(uint8_t(n >> 8));
        };
        out.push_back(1);
        out.push_back(uint8_t(shared.size));
        for (int i = 0; i < shared.size; i++)
            out.push_back(shared.pitches[i]);
        word(shared.kept.length);
        word(shared.kept.count);
        for (int i = 0; i < shared.kept.count; i++) {
            const auto h = shared.kept.hits[i];
            word(h.tick);
            word(h.gate);
            out.push_back(h.key);
            out.push_back(h.velocity);
        }
    }
    void loadExtraState(const uint8_t *p, size_t n) override {
        if (n < 7 || p[0] != 1 || !p[1] || p[1] > 8 || n < size_t(6 + p[1]))
            return;
        Memory m;
        m.size = p[1];
        size_t at = 2;
        for (int i = 0; i < m.size; i++) {
            if (p[at] > 127)
                return;
            m.pitches[i] = p[at++];
        }
        auto word = [&]() {
            const int value = p[at] + 256 * p[at + 1];
            at += 2;
            return value;
        };
        const int len = word(), count = word();
        if ((len != 3840 && len != 7680 && len != 15360) || count > Capacity ||
            n - at != size_t(count * 6))
            return;
        m.kept.clear(len);
        int prev = 0;
        for (int i = 0; i < count; i++) {
            const int t = word(), g = word(), k = p[at++], v = p[at++];
            if (t < prev || t >= len || g > PPQ || k > 127 || !v || v > 127 ||
                (!g && (k < 36 || k > 51)))
                return;
            m.kept.add({uint16_t(t), uint16_t(g), uint8_t(k), uint8_t(v)});
            prev = t;
        }
        std::lock_guard<std::mutex> guard(stateMutex);
        shared = m;
        pendingLoad = true;
    }
};
MPC_PLUGIN_ENTRY(PocketDuo)
