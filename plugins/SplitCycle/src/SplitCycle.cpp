// SPDX-License-Identifier: MIT
#include "../../DrumHands/percussion.h"
#include <mutex>

class SplitCycle final : public mpc::Plugin {
    enum { Write, LeftLength, RightLength, Snap, LeftMute, RightMute, Root, Tail };
    static constexpr int PPQ = 96, MaxEvents = 96;
    struct Hit {
        uint16_t tick = 0;
        uint8_t key = 0, vel = 0;
    };
    struct Lane {
        std::array<Hit, MaxEvents> hits{};
        int count = 0;
    };
    using Pattern = std::array<Lane, 2>;
    // A per-hit deadline stops a freshly quantized hit from echoing immediately.
    using Deadlines = std::array<std::array<int64_t, MaxEvents>, 2>;
    Pattern pattern{}, undoPattern{}, published{};
    Deadlines skip{}, undoSkip{};
    bool hasUndo = false, dirty = false, pending = false;
    std::mutex mutex;
    std::array<percussion::Mallet, 10> sounds{};
    std::array<int, 10> soundHands{};
    std::array<bool, 2> muted{};
    int nextSound = 0;
    void applyMutes(double sr) {
        for (int hand = 0; hand < 2; hand++) {
            const bool mute = getBool(hand ? RightMute : LeftMute);
            if (mute && !muted[hand]) {
                for (size_t i = 0; i < sounds.size(); i++)
                    if (soundHands[i] == hand)
                        sounds[i].damp(sr);
            }
            muted[hand] = mute;
        }
    }
    bool playing = false, awake = false;
    int64_t lastTick = -1;
    double freeTick = 0, expected = 0;
    static mpc::PluginInfo metadata() {
        mpc::PluginInfo p;
        p.name = "Split Cycle";
        p.vendor = "FG Scratchpad";
        p.isInstrument = true;
        p.numInputs = 0;
        p.uniqueId = MPC_FOURCC('F', 'g', 'S', 'C');
        p.version = 1000;
        return p;
    }
    void snapshot() {
        undoPattern = pattern;
        undoSkip = skip;
        hasUndo = true;
    }
    int length(int hand) const { return PPQ / 2 * getInt(hand ? RightLength : LeftLength); }
    void strike(int key, int vel, double sr) {
        const int hand = (key - 36) % 2;
        if (getBool(hand ? RightMute : LeftMute))
            return;
        constexpr int semitones[] = {0, 12, 7, 19, 12, 24};
        const int pad = key - 36;
        const double strength = vel / 127.;
        soundHands[nextSound] = hand;
        auto &voice = sounds[nextSound];
        nextSound = (nextSound + 1) % int(sounds.size());
        const double hz = mpc::noteToHz(getInt(Root) + semitones[pad]);
        const double tail = hand ? get(Tail) * .001 : .050 + .024 * (pad / 2);
        voice.strike(getInt(Root) + semitones[pad], .49 * strength, tail, hand ? .9 : .33,
                     hand ? .22 : -.22, sr);
        // Wood speaks with a short, inharmonic knock. Metal retains its high ring.
        voice.modes[1].strike(hz * (hand ? 2.74 : 1.53), tail * (hand ? .68 : .28),
                              strength * (hand ? .21 : .15), sr);
        voice.modes[2].strike(hz * (hand ? 4.17 : 3.42), tail * (hand ? .36 : .09),
                              strength * (hand ? .12 : .31), sr);
    }
    static int phase(int64_t tick, int period) { return int((tick % period + period) % period); }
    void write(int key, int velocity, double position) {
        const int hand = (key - 36) % 2, period = length(hand);
        constexpr int grids[] = {1, PPQ / 4, PPQ / 2, PPQ / 3};
        const int grid = grids[getInt(Snap)];
        const int64_t cycle = int64_t(std::floor(position / period));
        const auto within = position - cycle * period;
        // Allow the next downbeat to win even if a triplet grid does not divide this lane.
        int quantized = std::min(period, int(std::floor(within / grid + .5)) * grid);
        if (period - within < std::abs(quantized - within))
            quantized = period;
        const int tick = quantized % period;
        auto &lane = pattern[hand];
        int slot = 0;
        while (slot < lane.count && (lane.hits[slot].tick != tick || lane.hits[slot].key != key))
            slot++;
        if (slot >= MaxEvents)
            return;
        if (slot == lane.count || lane.hits[slot].vel != velocity) {
            snapshot();
            if (slot == lane.count)
                lane.count++;
            lane.hits[slot] = {uint16_t(tick), uint8_t(key), uint8_t(velocity)};
            dirty = true;
        }
        skip[hand][slot] = cycle * period + quantized + period;
    }
    void input(const mpc::MidiEvent &e, double position, double sr) {
        if (e.isAllNotesOff()) {
            sounds = {};
            return;
        }
        if (!e.isNoteOn())
            return;
        const int key = e.note();
        if (key >= 36 && key <= 41) {
            awake = true;
            strike(key, e.velocity(), sr);
            if (getBool(Write))
                write(key, e.velocity(), position);
        } else if (key == 42 || key == 43) {
            const int param = key == 42 ? LeftMute : RightMute;
            set(param, getBool(param) ? 0 : 1);
            applyMutes(sr);
        } else if (key == 44 && hasUndo) {
            pattern = undoPattern;
            skip = undoSkip;
            hasUndo = false;
            dirty = true;
        } else if (key == 46 || key == 47) {
            const int hand = key - 46;
            if (pattern[hand].count) {
                snapshot();
                pattern[hand].count = 0;
                dirty = true;
            }
        }
    }
    void playTick(int64_t tick, double sr) {
        for (int hand = 0; hand < 2; hand++) {
            const int local = phase(tick, length(hand));
            const Lane &lane = pattern[hand];
            for (int i = 0; i < lane.count; i++) {
                const Hit &h = lane.hits[i];
                if (h.tick == local && tick >= skip[hand][i])
                    strike(h.key, h.vel, sr);
            }
        }
    }
    void sync() {
        std::unique_lock<std::mutex> guard(mutex, std::try_to_lock);
        if (!guard)
            return;
        if (pending) {
            pattern = published;
            dirty = pending = false;
            reset();
        } else if (dirty) {
            published = pattern;
            dirty = false;
        }
    }
    void restartClock() {
        sounds = {};
        nextSound = 0;
        lastTick = INT64_MIN;
        freeTick = 0;
        awake = false;
        for (auto &lane : skip)
            lane.fill(INT64_MIN);
        for (auto &lane : undoSkip)
            lane.fill(INT64_MIN);
    }

  public:
    SplitCycle() : Plugin(metadata()) {
        addParam(mpc::boolParam("write", "Write Hits", true));
        addParam(mpc::intParam("length_l", "Left Eighths", 2, 8, 3));
        addParam(mpc::intParam("length_r", "Right Eighths", 2, 8, 4));
        addParam(mpc::choiceParam("snap", "Snap", {"Feel", "Sixteenth", "Eighth", "Triplet"}, 1));
        addParam(mpc::boolParam("mute_l", "Left Mute", false));
        addParam(mpc::boolParam("mute_r", "Right Mute", false));
        addParam(mpc::intParam("root", "Root", 32, 71, 50, "MIDI"));
        addParam(mpc::logParam("tail", "Metal Tail", 55, 820, 240, "ms", 0));
        addProgram("Three On Four", {1, 3, 4, 1, 0, 0, 50, 240});
        addProgram("Five On Four", {1, 5, 4, 1, 0, 0, 45, 150});
        addProgram("Seven On Six", {1, 7, 6, 3, 0, 0, 55, 320});
        addProgram("Loose Eights", {1, 8, 8, 0, 0, 0, 48, 190});
        restartClock();
    }
    void reset() override {
        restartClock();
        playing = false;
        expected = 0;
        hasUndo = false;
    }
    void process(mpc::ProcessContext &c) override {
        sync();
        const bool now = c.transport.valid && c.transport.playing;
        const bool hasPosition = now && c.transport.ppqValid && std::isfinite(c.transport.ppqPos);
        if (now != playing || (hasPosition && std::abs(c.transport.ppqPos - expected) > .025))
            restartClock();
        playing = now;
        applyMutes(c.sampleRate);
        const double step = PPQ * percussion::tempo(c) / (60 * c.sampleRate);
        const double start = hasPosition ? c.transport.ppqPos * PPQ : freeTick;
        int next = 0;
        for (int i = 0; i < c.numFrames; i++) {
            const double position = hasPosition ? start + i * step : freeTick;
            while (next < c.numMidiEvents && c.midi[next].sampleOffset <= i)
                input(c.midi[next++], position, c.sampleRate);
            if (now || awake) {
                const int64_t tick = int64_t(std::floor(position + 1e-8));
                if (tick != lastTick) {
                    playTick(tick, c.sampleRate);
                    lastTick = tick;
                }
                freeTick = position + step;
            }
            double left = 0, right = 0;
            for (auto &v : sounds)
                v.add(left, right);
            c.outputs[0][i] = std::tanh(left);
            c.outputs[1][i] = std::tanh(right);
        }
        expected = freeTick / PPQ;
        sync();
    }
    void saveExtraState(std::vector<uint8_t> &out) override {
        std::lock_guard<std::mutex> lock(mutex);
        out.push_back(1);
        for (auto &lane : published) {
            out.push_back(uint8_t(lane.count));
            for (int i = 0; i < lane.count; i++) {
                const auto &h = lane.hits[i];
                out.push_back(uint8_t(h.tick));
                out.push_back(uint8_t(h.tick >> 8));
                out.push_back(h.key);
                out.push_back(h.vel);
            }
        }
    }
    void loadExtraState(const uint8_t *data, size_t size) override {
        if (size < 3 || data[0] != 1)
            return;
        size_t cursor = 1;
        Pattern parsed{};
        for (int hand = 0; hand < 2; hand++) {
            if (cursor >= size)
                return;
            auto &lane = parsed[hand];
            lane.count = data[cursor++];
            if (lane.count > MaxEvents || size - cursor < size_t(lane.count * 4))
                return;
            for (int i = 0; i < lane.count; i++) {
                auto &h = lane.hits[i];
                h.tick = data[cursor] + 256 * data[cursor + 1];
                h.key = data[cursor + 2];
                h.vel = data[cursor + 3];
                cursor += 4;
                if (h.tick >= 4 * PPQ || h.key < 36 || h.key > 41 || (h.key - 36) % 2 != hand ||
                    !h.vel || h.vel > 127)
                    return;
                for (int j = 0; j < i; j++)
                    if (lane.hits[j].tick == h.tick && lane.hits[j].key == h.key)
                        return;
            }
        }
        if (cursor != size)
            return;
        std::lock_guard<std::mutex> lock(mutex);
        published = parsed;
        pending = true;
    }
};
MPC_PLUGIN_ENTRY(SplitCycle)
