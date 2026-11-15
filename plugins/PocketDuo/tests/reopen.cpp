// Linux SDK test: unload the built library, then reopen its opaque host chunk.
#include "mpc_vst2_abi.h"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <dlfcn.h>
#include <iostream>
#include <vector>

static VstTimeInfo clockInfo{};
static VstIntPtr host(AEffect *, VstInt32 opcode, VstInt32, VstIntPtr, void *, float) {
    if (opcode == audioMasterVersion)
        return 2400;
    if (opcode == audioMasterGetTime)
        return reinterpret_cast<VstIntPtr>(&clockInfo);
    return 0;
}
class Instance {
    void *handle;
    AEffect *effect;

  public:
    explicit Instance(const char *path) {
        handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
        if (!handle)
            std::cerr << dlerror() << "\n";
        assert(handle);
        using Entry = AEffect *(*)(audioMasterCallback);
        auto entry = reinterpret_cast<Entry>(dlsym(handle, "VSTPluginMain"));
        assert(entry);
        effect = entry(host);
        assert(effect && effect->numOutputs == 2 && effect->numInputs == 0);
        dispatch(effOpen);
        dispatch(effSetSampleRate, 0, nullptr, 48000);
        dispatch(effSetBlockSize, 128);
        dispatch(effMainsChanged, 1);
    }
    ~Instance() {
        dispatch(effMainsChanged, 0);
        dispatch(effClose);
        dlclose(handle);
    }
    VstIntPtr dispatch(int opcode, VstIntPtr value = 0, void *ptr = nullptr, float opt = 0) {
        return effect->dispatcher(effect, opcode, 0, value, ptr, opt);
    }
    void keep() { effect->setParameter(effect, 2, 1.f); }
    std::vector<uint8_t> save() {
        void *data = nullptr;
        auto size = dispatch(effGetChunk, 0, &data);
        assert(size > 0);
        auto ptr = static_cast<uint8_t *>(data);
        return {ptr, ptr + size};
    }
    void load(std::vector<uint8_t> &chunk) {
        assert(dispatch(effSetChunk, chunk.size(), chunk.data()) == 1);
    }
    std::vector<float> bar(bool perform) {
        std::vector<float> result(96000);
        std::array<float, 128> right{};
        for (int i = 0; i < 96000; i += 128) {
            clockInfo.flags = kVstTransportPlaying | kVstPpqPosValid | kVstTempoValid;
            clockInfo.tempo = 120;
            clockInfo.sampleRate = 48000;
            clockInfo.samplePos = i;
            clockInfo.ppqPos = i / 24000.;
            if (perform && (i == 0 || i == 12288 || i == 48128 || i == 71936)) {
                VstMidiEvent note{};
                note.type = kVstMidiType;
                note.byteSize = sizeof(note);
                note.midiData[0] = char(0x90);
                note.midiData[1] = 36;
                note.midiData[2] = i == 12288 ? 34 : 103;
                VstEvents events{};
                events.numEvents = 1;
                events.events[0] = reinterpret_cast<VstEvent *>(&note);
                dispatch(effProcessEvents, 0, &events);
            }
            float *channels[] = {result.data() + i, right.data()};
            effect->processReplacing(effect, nullptr, channels, 128);
            assert(std::equal(right.begin(), right.end(), channels[0]));
        }
        return result;
    }
};
int main(int argc, char **argv) {
    assert(argc == 2);
    std::vector<uint8_t> chunk;
    std::vector<float> playback;
    {
        Instance machine(argv[1]);
        machine.bar(true);
        machine.keep();
        playback = machine.bar(false);
        chunk = machine.save();
    }
    {
        Instance machine(argv[1]);
        machine.load(chunk);
        assert(machine.bar(false) == playback);
        assert(machine.save() == chunk);
    }
    assert(*std::max_element(playback.begin(), playback.end()) > .1f);
    std::cout << "Built VST unloaded, reopened and rendered identical stereo output and state.\n";
}
