// SPDX-License-Identifier: MIT
#pragma once
#include "../../DrumHands/percussion.h"
#include <atomic>

class RestReply final : public mpc::Plugin {
  public:
    enum { Gap, Shape, Keep, Level, Root, Sensitivity, Decay };

  private:
    struct Hit {
        double beat = 0, peak = 0;
    };
    struct Answer {
        int count = 0, next = 0;
        std::array<double, 4> due{};
        std::array<int, 4> notes{}, strengths{};
    };
    // One byte per hit: 3-bit velocity and 5-bit interval in 1/16-quarter steps.
    // A single atomic snapshot keeps host saves off the audio thread.
    std::atomic<uint32_t> stored{0};
    std::array<Hit, 4> recent{};
    int count = 0, peakFrames = 0, cooldown = 0, voiceIndex = 0;
    Answer answer;
    std::array<percussion::Mallet, 6> voices{};
    double beat = 0, expected = 0, fast = 0, lastPeak = 0, valley = 0;
    bool ready = true, playing = false;
    static mpc::PluginInfo metadata() {
        mpc::PluginInfo p;
        p.name = "Rest Reply";
        p.vendor = "FG Scratchpad";
        p.numInputs = 2;
        p.uniqueId = MPC_FOURCC('F', 'g', 'R', 'R');
        p.version = 1000;
        return p;
    }
    void onset(double amplitude, double sr) {
        answer = {};
        for (auto &v : voices)
            if (v.remaining)
                v.damp(sr);
        if (count == 4) {
            std::move(recent.begin() + 1, recent.end(), recent.begin());
            count--;
        }
        recent[count++] = {beat, amplitude};
        lastPeak = amplitude;
        peakFrames = int(sr * .009);
        cooldown = int(sr * .035);
        ready = false;
    }
    uint32_t encode() const {
        uint32_t pattern = 0;
        for (int i = 0; i < count; i++) {
            const int ticks =
                i ? std::clamp(int(std::lround(16 * (recent[i].beat - recent[i - 1].beat))), 1, 31) : 0;
            const int velocity =
                std::clamp(int(std::lround(7 * std::sqrt(std::min(1., recent[i].peak)))), 1, 7);
            pattern |= uint32_t((velocity << 5) | ticks) << (8 * i);
        }
        return pattern;
    }
    void startReply(uint32_t pattern) {
        std::array<int, 4> velocity{}, interval{};
        answer = {};
        for (int i = 0; i < 4; i++) {
            const unsigned byte = (pattern >> (i * 8)) & 255;
            if (!byte)
                break;
            velocity[i] = byte >> 5;
            interval[i] = byte & 31;
            answer.count++;
        }
        double due = beat;
        const int shape = getInt(Shape);
        constexpr int scale[] = {0, 2, 5, 7, 9};
        for (int i = 0; i < answer.count; i++) {
            const int source = shape == 1 ? answer.count - 1 - i : i;
            const int strength = velocity[source];
            if (i) {
                const int spacing = shape == 1 ? interval[source + 1] : interval[source];
                due += spacing / (shape == 2 ? 32. : 16.);
            }
            answer.due[i] = due;
            answer.strengths[i] = strength;
            // The contour comes from the accents. Resolve the final hit to the root.
            const int degree = i == answer.count - 1 ? 0 : std::clamp(strength - 2, 0, 4);
            answer.notes[i] = getInt(Root) + scale[degree];
        }
    }
    void speak(int i, double sr) {
        auto &v = voices[voiceIndex];
        voiceIndex = (voiceIndex + 1) % int(voices.size());
        const double strength = answer.strengths[i] / 7.;
        v.strike(answer.notes[i], .49 * strength, .001 * get(Decay), strength * .8, (i % 2 ? .20 : -.20),
                 sr);
    }
    void clearLive() {
        answer = {};
        voices = {};
        count = peakFrames = cooldown = voiceIndex = 0;
        beat = fast = lastPeak = valley = 0;
        ready = true;
    }

  public:
    RestReply() : Plugin(metadata()) {
        addParam(mpc::choiceParam("gap", "Gap", {"Eighth", "Quarter", "Dotted quarter", "Half"}, 1));
        addParam(mpc::choiceParam("shape", "Reply Shape", {"Echo", "Reverse", "Double time"}, 1));
        addParam(mpc::boolParam("keep", "Keep Call", false));
        addParam(mpc::floatParam("level", "Reply Level", 0, 100, 55, "%", 0));
        addParam(mpc::intParam("root", "Root", 30, 79, 55, "MIDI"));
        addParam(mpc::floatParam("sensitivity", "Sensitivity", 0, 100, 58, "%", 0));
        addParam(mpc::logParam("decay", "Decay", 45, 720, 210, "ms", 0));
        addProgram("Reverse Answer", {1, 1, 0, 55, 55, 58, 210});
        addProgram("Short Exchange", {0, 0, 0, 64, 50, 60, 105});
        addProgram("Double Time", {1, 2, 0, 69, 62, 63, 135});
        addProgram("Long Answer", {2, 1, 0, 60, 45, 53, 430});
    }
    void reset() override {
        clearLive();
        playing = false;
        expected = 0;
    }
    void process(mpc::ProcessContext &c) override {
        const bool now = c.transport.valid && c.transport.playing;
        if (now != playing ||
            (now && c.transport.ppqValid && std::abs(expected - c.transport.ppqPos) > .025))
            clearLive();
        playing = now;
        const double step = percussion::tempo(c) / (60 * c.sampleRate);
        expected = c.transport.ppqPos + c.numFrames * step;
        const double threshold = .23 * std::pow(.035, get(Sensitivity) * .01);
        const double fall = std::exp(-1 / (c.sampleRate * .008)), wet = get(Level) * .01;
        constexpr double gaps[] = {.5, 1, 1.5, 2};
        const double gap = gaps[getInt(Gap)];
        for (int i = 0; i < c.numFrames; i++, beat += step) {
            const double dryL = c.inputs[0][i], dryR = c.inputs[1][i];
            const double level = std::max(std::abs(dryL), std::abs(dryR));
            fast = std::max(level, fast * fall);
            if (cooldown > 0)
                --cooldown;
            if (!ready && fast < std::max(threshold * .65, lastPeak * .22)) {
                ready = true;
                valley = fast;
            }
            if (ready)
                valley = std::min(valley, fast);
            // Require a fresh rise. A long decaying drum tail can cross the release
            // threshold while still loud enough to be mistaken for another stroke.
            if (ready && !cooldown && level >= std::max(threshold, valley * 1.65))
                onset(level, c.sampleRate);
            if (peakFrames > 0 && count) {
                --peakFrames;
                recent[count - 1].peak = std::max(recent[count - 1].peak, level);
                lastPeak = recent[count - 1].peak;
            }
            if (count && beat + 1e-10 >= recent[count - 1].beat + gap &&
                fast < std::max(threshold, lastPeak * .20)) {
                const uint32_t kept = getBool(Keep) ? stored.load(std::memory_order_relaxed) : 0;
                if (kept || count >= 2) {
                    const uint32_t pattern = kept ? kept : encode();
                    if (!kept)
                        stored.store(pattern, std::memory_order_relaxed);
                    startReply(pattern);
                }
                count = 0;
            }
            while (answer.next < answer.count && beat + 1e-10 >= answer.due[answer.next]) {
                speak(answer.next++, c.sampleRate);
            }
            double l = 0, r = 0;
            for (auto &voice : voices)
                voice.add(l, r);
            c.outputs[0][i] = dryL + wet * std::tanh(l);
            c.outputs[1][i] = dryR + wet * std::tanh(r);
        }
    }
    void saveExtraState(std::vector<uint8_t> &out) override {
        const auto word = stored.load(std::memory_order_relaxed);
        out.push_back(1);
        for (int i = 0; i < 4; i++)
            out.push_back(uint8_t(word >> (8 * i)));
    }
    void loadExtraState(const uint8_t *p, size_t n) override {
        if (n != 5 || p[0] != 1)
            return;
        uint32_t pattern = 0;
        bool end = false;
        int hits = 0;
        for (int i = 0; i < 4; i++) {
            uint8_t byte = p[i + 1];
            if (!byte) {
                end = true;
                continue;
            }
            if (end || !(byte >> 5) || ((byte & 31) == 0) != (i == 0))
                return;
            pattern |= uint32_t(byte) << (8 * i);
            hits++;
        }
        if (hits != 1)
            stored.store(pattern, std::memory_order_relaxed);
    }
};
