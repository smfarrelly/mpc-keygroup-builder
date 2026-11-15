// SPDX-License-Identifier: MIT
#include "../../DrumHands/percussion.h"
#include "../variation.h"
#include <mutex>

class ShadowSteps final : public mpc::Plugin {
    enum { Scene, Root, Kit, Answer };
    shadow::Groove home{}, take{}, published{};
    std::mutex lock;
    bool loaded = false, dirty = false, armed = true, recording = false, awake = false, playing = false;
    double freeStep = 0, expected = 0, remaining = 0;
    int64_t lastStep = INT64_MIN;
    std::array<int, 3> held{};
    int heldCount = 0, voiceIndex = 0;
    struct Voice {
        percussion::Mallet sound;
        bool melody = false;
    };
    std::array<Voice, 16> voices{};
    static mpc::PluginInfo metadata() {
        mpc::PluginInfo p;
        p.name = "Shadow Steps";
        p.vendor = "FG Scratchpad";
        p.isInstrument = true;
        p.numInputs = 0;
        p.uniqueId = MPC_FOURCC('F', 'g', 'S', 'w');
        p.version = 1000;
        return p;
    }
    bool empty() const { return home == shadow::Groove{}; }
    static int cell(int64_t step) { return int((step % 16 + 16) % 16); }
    void sync() {
        std::unique_lock<std::mutex> guard(lock, std::try_to_lock);
        if (!guard)
            return;
        if (loaded) {
            home = published;
            loaded = dirty = false;
            reset();
        } else if (dirty) {
            published = home;
            dirty = false;
        }
    }
    void strike(shadow::Note note, double sr) {
        constexpr double tails[] = {.17, .082, .063, .14};
        auto &voice = voices[voiceIndex];
        voiceIndex = (voiceIndex + 1) % int(voices.size());
        voice.melody = note.melody;
        auto &sound = voice.sound;
        const double strength = note.velocity / 127.;
        sound.strike(note.pitch, strength * (note.melody ? .46 : .57),
                     note.melody ? .23 : tails[note.lane], strength,
                     note.melody ? .22 : (note.lane - 1.5) * .11, sr);
        if (!note.melody) {
            const double hz = mpc::noteToHz(note.pitch);
            constexpr double ratios[] = {1.48, 3.41, 2.73, 5.12};
            sound.modes[1].strike(hz * ratios[note.lane], .024, .4 * strength, sr);
        }
    }
    void beginTake(double pos) {
        take = {};
        remaining = 16 - (pos - std::floor(pos + 1e-8));
        recording = true;
        armed = false;
    }
    void input(const mpc::MidiEvent &e, double pos, double sr) {
        if (e.isAllNotesOff()) {
            heldCount = 0;
            voices = {};
            return;
        }
        int key = e.note();
        if (key >= 40 && key <= 42 && (e.isNoteOn() || e.isNoteOff())) {
            const int scene = key - 39;
            auto it = std::find(held.begin(), held.begin() + heldCount, scene);
            if (it != held.begin() + heldCount) {
                std::move(it + 1, held.begin() + heldCount, it);
                --heldCount;
            }
            if (e.isNoteOn())
                held[heldCount++] = scene;
            return;
        }
        if (!e.isNoteOn())
            return;
        if (key == 44) {
            recording = false;
            armed = true;
            return;
        }
        if (key == 45) {
            recording = false;
            armed = empty();
            return;
        }
        if (key >= 48 && key <= 79) {
            set(Root, key);
            return;
        }
        if (key == 35) {
            awake = true;
            if (!recording)
                beginTake(pos);
            return;
        }
        if ((key < 36 || key > 39) && key != 47)
            return;
        awake = true;
        if (armed)
            beginTake(pos);
        const int v = e.velocity();
        const int lane = key == 47 ? (v >= 105 ? 0 : v >= 80 ? 1 : v >= 48 ? 2 : 3) : key - 36;
        if (recording)
            take[cell(int64_t(std::floor(pos + .5)))][lane] = e.velocity();
        constexpr int pitches[] = {0, 3, 7, 10};
        strike({lane, getInt(Root) + pitches[lane], e.velocity(), false}, sr);
    }
    void clockReset() {
        heldCount = 0;
        recording = false;
        armed = empty();
        awake = false;
        voices = {};
        voiceIndex = 0;
        freeStep = 0;
        lastStep = INT64_MIN;
    }

  public:
    ShadowSteps() : Plugin(metadata()) {
        addParam(mpc::choiceParam("scene", "Scene", {"Original", "Offbeat", "Holes", "Canon"}, 0));
        addParam(mpc::intParam("root", "Root", 30, 79, 43, "MIDI"));
        addParam(mpc::floatParam("kit", "Kit Level", 0, 100, 82, "%", 0));
        addParam(mpc::floatParam("answer", "Answer Level", 0, 100, 74, "%", 0));
    }
    void reset() override {
        clockReset();
        playing = false;
        expected = 0;
    }
    void process(mpc::ProcessContext &c) override {
        sync();
        const bool run = c.transport.valid && c.transport.playing;
        const bool clocked = run && c.transport.ppqValid && std::isfinite(c.transport.ppqPos);
        if (run != playing || (clocked && std::abs(expected - c.transport.ppqPos) > .025)) {
            const auto &t = c.transport;
            const bool wrapped = playing && clocked && t.cycling && t.cycleEndPpq > t.cycleStartPpq &&
                                 std::abs(expected - t.cycleEndPpq) < .025 &&
                                 std::abs(t.ppqPos - t.cycleStartPpq) < .025;
            if (wrapped)
                lastStep = INT64_MIN;
            else
                clockReset();
        }
        playing = run;
        const double delta = 4 * percussion::tempo(c) / (60 * c.sampleRate);
        const double start = clocked ? 4 * c.transport.ppqPos : freeStep;
        const double kit = .01 * get(Kit), answer = .01 * get(Answer);
        const int scene = getInt(Scene);
        int next = 0;
        for (int i = 0; i < c.numFrames; i++) {
            const double pos = clocked ? start + i * delta : freeStep;

            while (next < c.numMidiEvents && c.midi[next].sampleOffset <= i)
                input(c.midi[next++], pos, c.sampleRate);
            if (run || awake) {
                int64_t index = int64_t(std::floor(pos + 1e-8));
                if (index != lastStep && !recording)
                    shadow::step(home, cell(index), heldCount ? held[heldCount - 1] : scene,
                                 getInt(Root), [&](shadow::Note n) { strike(n, c.sampleRate); });
                lastStep = index;
                freeStep = pos + delta;
                if (recording && (remaining -= delta) <= 1e-8) {
                    if (take != shadow::Groove{}) {
                        home = take;
                        dirty = true;
                    }
                    armed = empty();
                    recording = false;
                }
            }
            double l = 0, r = 0;
            for (auto &v : voices) {
                double a = 0, b = 0;
                v.sound.add(a, b);
                const double gain = v.melody ? answer : kit;
                l += gain * a;
                r += gain * b;
            }
            c.outputs[0][i] = std::tanh(l);
            c.outputs[1][i] = std::tanh(r);
        }
        expected = freeStep / 4;
        sync();
    }
    void saveExtraState(std::vector<uint8_t> &out) override {
        std::lock_guard<std::mutex> guard(lock);
        out.push_back(1);
        for (const auto &row : published)
            out.insert(out.end(), row.begin(), row.end());
    }
    void loadExtraState(const uint8_t *data, size_t n) override {
        if (n != 65 || data[0] != 1 ||
            std::any_of(data + 1, data + n, [](uint8_t v) { return v > 127; }))
            return;
        std::lock_guard<std::mutex> guard(lock);
        for (int i = 0; i < 16; i++)
            std::copy_n(data + 1 + i * 4, 4, published[i].begin());
        loaded = true;
    }
};
MPC_PLUGIN_ENTRY(ShadowSteps)
