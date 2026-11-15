// SPDX-License-Identifier: MIT
// Exercise the built shared objects through the same plugin ABI used to save a project.
#pragma once
#ifdef NDEBUG
#error "The rehearsal host requires active assertions. Compile with -UNDEBUG."
#endif
#include "mpc_vst2_abi.h"
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <dlfcn.h>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace testhost {
struct Event {
    int frame, key, value, status = 0x90;
};
using Audio = std::array<std::vector<float>, 2>;
using Bytes = std::vector<uint8_t>;
inline Audio silence(int frames) { return {std::vector<float>(frames), std::vector<float>(frames)}; }
inline VstTimeInfo clock{};
inline VstIntPtr callback(AEffect *, VstInt32 op, VstInt32, VstIntPtr, void *, float) {
    if (op == audioMasterVersion)
        return 2400;
    if (op == audioMasterGetTime)
        return reinterpret_cast<VstIntPtr>(&clock);
    return 0;
}
class Plugin {
    void *handle = nullptr;
    AEffect *effect = nullptr;
    VstIntPtr call(int op, VstIntPtr value = 0, void *ptr = nullptr, float opt = 0) const {
        return effect->dispatcher(effect, op, 0, value, ptr, opt);
    }

  public:
    double bpm = 120;
    int position = 0;
    bool playing = true, ppqValid = true;
    double cycleStart = 0, cycleEnd = 0;
    const int rate, block;
    Plugin(const std::filesystem::path &binary, int sr = 32000, int blockSize = 128)
        : rate(sr), block(blockSize) {
        handle = dlopen(binary.c_str(), RTLD_NOW | RTLD_LOCAL);
        if (!handle)
            throw std::runtime_error(dlerror());
        using Entry = AEffect *(*)(audioMasterCallback);
        auto entry = reinterpret_cast<Entry>(dlsym(handle, "VSTPluginMain"));
        assert(entry);
        effect = entry(callback);
        assert(effect && effect->numOutputs == 2);
        call(effOpen);
        call(effSetSampleRate, 0, nullptr, float(rate));
        call(effSetBlockSize, block);
        call(effMainsChanged, 1);
        call(effStartProcess);
    }
    Plugin(const Plugin &) = delete;
    ~Plugin() {
        call(effStopProcess);
        call(effMainsChanged, 0);
        call(effClose);
        dlclose(handle);
    }
    void preset(int index) {
        assert(index >= 0 && index < effect->numPrograms);
        call(effSetProgram, index);
    }
    std::string display(int param) const {
        char value[64]{};
        effect->dispatcher(effect, effGetParamDisplay, param, 0, value, 0);
        return value;
    }
    void set(int param, float normalized) {
        assert(param >= 0 && param < effect->numParams && normalized >= 0 && normalized <= 1);
        effect->setParameter(effect, param, normalized);
    }
    Bytes save() const {
        void *data = nullptr;
        auto size = call(effGetChunk, 0, &data);
        assert(size > 0 && data);
        auto p = static_cast<uint8_t *>(data);
        return {p, p + size};
    }
    void load(const Bytes &chunk) {
        assert(call(effSetChunk, chunk.size(), const_cast<uint8_t *>(chunk.data())) == 1);
    }
    Audio render(int frames, std::vector<Event> events = {}, const Audio *input = nullptr) {
        std::stable_sort(events.begin(), events.end(), [](auto a, auto b) { return a.frame < b.frame; });
        Audio out = input ? *input : silence(frames);
        size_t next = 0;
        assert(out[0].size() == size_t(frames) && out[1].size() == size_t(frames));
        for (int offset = 0; offset < frames; offset += block) {
            int n = std::min(block, frames - offset);
            clock.flags =
                kVstTempoValid | (ppqValid ? kVstPpqPosValid : 0) | (playing ? kVstTransportPlaying : 0);
            if (cycleEnd > cycleStart) {
                clock.flags |= kVstCyclePosValid | kVstTransportCycleActive;
                clock.cycleStartPos = cycleStart;
                clock.cycleEndPos = cycleEnd;
            }
            clock.sampleRate = rate;
            clock.samplePos = position + offset;
            clock.tempo = bpm;
            clock.ppqPos = double(position + offset) * bpm / (60 * rate);
            while (next < events.size() && events[next].frame < offset + n) {
                const auto e = events[next++];
                assert(e.frame >= offset && e.key >= 0 && e.key <= 127 && e.value >= 0 &&
                       e.value <= 127);
                VstMidiEvent msg{};
                msg.type = kVstMidiType;
                msg.byteSize = sizeof(msg);
                msg.deltaFrames = e.frame - offset;
                msg.midiData[0] = char(e.status);
                msg.midiData[1] = char(e.key);
                msg.midiData[2] = char(e.value);
                VstEvents batch{};
                batch.numEvents = 1;
                batch.events[0] = reinterpret_cast<VstEvent *>(&msg);
                call(effProcessEvents, 0, &batch);
            }
            float *channels[] = {out[0].data() + offset, out[1].data() + offset};
            effect->processReplacing(effect, effect->numInputs ? channels : nullptr, channels, n);
        }
        position += frames;
        assert(next == events.size());
        for (auto &ch : out)
            for (float x : ch)
                assert(std::isfinite(x));
        return out;
    }
};
inline double energy(const Audio &a, int start, int end) {
    assert(start >= 0 && end >= start && end <= int(a[0].size()));
    double sum = 0;
    for (auto &ch : a)
        for (int i = start; i < end; i++)
            sum += double(ch[i]) * ch[i];
    return sum;
}
inline int firstSound(const Audio &a, int start = 0, double threshold = .00001) {
    for (int i = start; i < int(a[0].size()); i++)
        if (std::abs(a[0][i]) > threshold || std::abs(a[1][i]) > threshold)
            return i;
    return -1;
}
} // namespace testhost
