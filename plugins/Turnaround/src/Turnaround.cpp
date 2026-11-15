// SPDX-License-Identifier: MIT
#include "mpc_plugin.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <mutex>
#include <vector>

class Turnaround final : public mpc::Plugin {
    static constexpr int Rate = 16000, Capacity = Rate * 3;
    using Frame = std::array<int16_t, 2>;
    struct Clip {
        std::vector<Frame> pcm = std::vector<Frame>(Capacity);
        int end = 0, count = 0, onset = -1, mode = 0, span = 2;
        Frame frame(int pos) const {
            return pcm[(end - count + Capacity + std::clamp(pos, 0, count - 1)) % Capacity];
        }
    };
    Clip history, held, loaded;
    std::mutex mutex;
    bool pending = false, armed = false, active = false, wasFill = false, wasPlaying = false;
    double expected = 0, target = 0, playEnd = 0, armedWidth = 1, subsample = 0, env = 0;
    int armedMode = 1, armedSpan = 2;
    bool reuse = false;
    static constexpr double widths[] = {.25, .5, 1., 2., 4.};
    static mpc::PluginInfo metadata() {
        mpc::PluginInfo p;
        p.name = "Turnaround";
        p.vendor = "FG Scratchpad";
        p.uniqueId = MPC_FOURCC('F', 'g', 'T', 'A');
        p.numInputs = 2;
        p.version = 1000;
        return p;
    }
    bool freeze(double bpm) {
        if (reuse && held.count)
            return true;
        std::unique_lock<std::mutex> lock(mutex, std::try_to_lock);
        if (!lock || !history.count)
            return false;
        const int len = std::min(history.count, int(std::round(Rate * 60 / bpm)));
        std::swap(history, held);
        held.count = len;
        const int distance = (held.end - held.onset + Capacity) % Capacity;
        held.onset = held.onset >= 0 && distance && distance <= len ? len - distance : 0;
        held.mode = armedMode;
        held.span = armedSpan;
        history.end = history.count = 0;
        history.onset = -1;
        return true;
    }

  public:
    Turnaround() : Plugin(metadata()) {
        addParam(mpc::boolParam("fill", "Fill", false));
        addParam(mpc::choiceParam("gesture", "Gesture", {"Break", "Roll", "Answer"}, 1));
        addParam(
            mpc::choiceParam("span", "Span", {"Sixteenth", "Eighth", "Beat", "Half bar", "Bar"}, 2));
        addParam(mpc::boolParam("keep", "Keep", false));
    }
    void reset() override {
        armed = active = wasFill = wasPlaying = false;
        expected = target = subsample = env = 0;
        history.count = history.end = 0;
        history.onset = -1;
    }
    void process(mpc::ProcessContext &c) override {
        {
            std::unique_lock<std::mutex> lock(mutex, std::try_to_lock);
            if (lock && pending) {
                std::swap(loaded, held);
                pending = false;
                reset();
            }
        }
        const bool playing = c.transport.valid && c.transport.playing;
        const double bpm = c.transport.tempoValid && std::isfinite(c.transport.bpm)
                               ? std::clamp(c.transport.bpm, 20., 300.)
                               : 120.;
        const double step = bpm / (60 * c.sampleRate);
        double pos = playing && c.transport.ppqValid && std::isfinite(c.transport.ppqPos)
                         ? c.transport.ppqPos
                         : expected;
        if (!playing || (wasPlaying && std::abs(expected - pos) > .02)) {
            // A looping MPC sequence can wrap before a late request reaches its target.
            if (playing && armed && c.transport.cycling && pos < expected) {
                target = 16 * std::ceil((pos + armedWidth - 1e-9) / 16.);
            } else if (armed) {
                armed = false;
                set(0, 0);
            }
            active = false;
        }
        const bool fill = getBool(0);

        if (playing && fill && !wasFill) {
            reuse = getBool(3) && held.count;
            armedSpan = reuse ? held.span : getInt(2);
            armedMode = getInt(1);
            armedWidth = widths[armedSpan];
            target = 16 * std::ceil((pos + armedWidth - 1e-9) / 16.);
            armed = true;
        }
        if (!fill)
            armed = false;
        wasFill = playing && fill;
        wasPlaying = playing;
        const double release = std::exp(-1 / (c.sampleRate * .022));
        const double start = pos;
        for (int i = 0; i < c.numFrames; i++) {
            pos = start + i * step;
            const double dry[] = {c.inputs[0][i], c.inputs[1][i]};
            if (armed && pos + 1e-9 >= target - armedWidth) {
                active = freeze(bpm);
                playEnd = target;
                armed = false;
                set(0, 0);
                wasFill = false;
            }
            if (active && pos + 1e-9 >= playEnd)
                active = false;
            if (active) {
                const double width = widths[held.span];
                const double elapsedFrames = std::round((pos - (playEnd - width)) / step);
                const double u = std::clamp(elapsedFrames * step / width, 0., .99999999);
                // Re-read a transient for a roll; reorder quarter-beat slices for an answer.
                int slices = held.mode == 0 ? 1 : 4;
                double local = std::fmod(u * slices, 1.);
                double gain = 1, index = 0;
                if (held.mode == 0) {
                    gain = u >= .75 ? 1 : 0;
                    local = std::max(0., (u - .75) * 4.);
                    index = held.onset + local * .25 * held.count;
                } else if (held.mode == 1) {
                    index = held.onset + local * .25 * held.count;
                    gain = .40 + .20 * int(u * 4);
                } else {
                    constexpr int order[] = {2, 0, 3, 1};
                    index = (order[int(u * 4)] + local) * .25 * held.count;
                    gain = int(u * 4) == 1 ? .55 : 1.;
                }
                // Silence past the captured tail instead of holding its final sample.
                if (index >= held.count)
                    gain = 0;
                const int k = int(index);
                const auto a = held.frame(k), b = held.frame(k + 1);
                const double edge = std::min(1., std::min(local, 1 - local) * width /
                                                     (step * c.sampleRate * .002 * slices));
                const double mix =
                    std::clamp(std::min(u, 1 - u) * width / (step * c.sampleRate * .002), 0., 1.);
                for (int ch = 0; ch < 2; ch++) {
                    const double sample = (a[ch] + (b[ch] - a[ch]) * (index - k)) / 32768.;
                    c.outputs[ch][i] = dry[ch] * (1 - mix) + sample * gain * edge * mix;
                }
            } else
                for (int ch = 0; ch < 2; ch++)
                    c.outputs[ch][i] = dry[ch];
            const double peak = std::max(std::abs(dry[0]), std::abs(dry[1]));
            if (peak > .025 && peak > env * 1.6)
                history.onset = history.end;
            env = std::max(peak, env * release);
            subsample += Rate / c.sampleRate;
            while (subsample >= 1) {
                for (int ch = 0; ch < 2; ch++)
                    history.pcm[history.end][ch] =
                        int16_t(std::clamp(std::lround(dry[ch] * 32768), -32768L, 32767L));
                history.end = (history.end + 1) % Capacity;
                history.count = std::min(Capacity, history.count + 1);
                subsample--;
            }
        }
        expected = playing ? start + c.numFrames * step : 0;
    }
    void saveExtraState(std::vector<uint8_t> &out) override {
        std::lock_guard<std::mutex> lock(mutex);
        const Clip &clip = pending ? loaded : held;
        auto word = [&](int value) {
            out.push_back(uint8_t(value));
            out.push_back(uint8_t(value >> 8));
        };
        out.push_back(1);
        out.push_back(clip.mode);
        out.push_back(clip.span);
        word(clip.count);
        word(std::max(0, clip.onset));
        for (int i = 0; i < clip.count; i++)
            for (int16_t value : clip.frame(i))
                word(uint16_t(value));
    }
    void loadExtraState(const uint8_t *p, size_t n) override {
        if (n < 7 || p[0] != 1 || p[1] > 2 || p[2] > 4)
            return;
        auto word = [&](size_t i) { return int(p[i]) + 256 * p[i + 1]; };
        int count = word(3), onset = word(5);
        if (count > Capacity || onset >= std::max(1, count) || n != size_t(7 + 4 * count))
            return;
        Clip clip;
        clip.mode = p[1];
        clip.span = p[2];
        clip.end = count % Capacity;
        clip.count = count;
        clip.onset = onset;
        for (int i = 0; i < count; i++)
            for (int ch = 0; ch < 2; ch++)
                clip.pcm[i][ch] = int16_t(word(7 + 4 * i + 2 * ch));
        std::lock_guard<std::mutex> lock(mutex);
        std::swap(clip, loaded);
        pending = true;
    }
};
MPC_PLUGIN_ENTRY(Turnaround)
