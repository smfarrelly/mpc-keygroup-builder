// Offline source-level performance probe. PCM input and output are stereo signed LE16.
#include "mpc_plugin.h"
#undef MPC_PLUGIN_ENTRY
#define MPC_PLUGIN_ENTRY(Class)
#include "../BeatCatch/src/BeatCatch.cpp"
#include "../BloomKeys/src/BloomKeys.cpp"
#include "../PocketLayers/src/PocketLayers.cpp"
#include <fstream>
#include <iostream>
#include <memory>

struct Action {
    int frame;
    std::string kind;
    int index;
    float value;
};

int main(int argc, char **argv) {
    if (argc != 7)
        return 2;
    std::unique_ptr<mpc::Plugin> p;
    std::string name = argv[1];
    if (name == "PocketLayers")
        p = std::make_unique<PocketLayers>();
    else if (name == "BloomKeys")
        p = std::make_unique<BloomKeys>();
    else if (name == "BeatCatch")
        p = std::make_unique<BeatCatch>();
    else
        return 2;
    const int frames = std::stoi(argv[2]);
    const double bpm = std::stod(argv[3]);
    if (frames < 1 || !(bpm >= 20 && bpm <= 300))
        return 2;
    std::ifstream schedule(argv[4]);
    if (!schedule)
        return 2;
    std::vector<Action> actions;
    Action a;
    while (schedule >> a.frame) {
        if (!(schedule >> a.kind >> a.index >> a.value) || a.frame < 0 || a.frame >= frames ||
            (!actions.empty() && a.frame < actions.back().frame))
            return 2;
        if (a.kind == "set") {
            if (a.index < 0 || a.index >= p->numParams())
                return 2;
        } else if ((a.kind != "on" && a.kind != "off") || a.index < 0 || a.index > 127 || a.value < 0 ||
                   a.value > 127)
            return 2;
        actions.push_back(a);
    }
    if (!schedule.eof())
        return 2;
    const bool useInput = std::string(argv[5]) != "-";
    std::ifstream input(argv[5], std::ios::binary);
    std::ofstream output(argv[6], std::ios::binary);
    if (!output || (useInput && !input))
        return 2;
    p->prepare(44100, 128);
    p->reset();
    size_t next = 0;
    for (int pos = 0; pos < frames;) {
        std::vector<mpc::MidiEvent> events;
        while (next < actions.size() && actions[next].frame == pos) {
            const auto &action = actions[next++];
            if (action.kind == "set")
                p->set(action.index, action.value);
            else if (action.kind == "on")
                events.push_back(
                    mpc::MidiEvent::noteOn(0, action.index, static_cast<int>(action.value)));
            else
                events.push_back(mpc::MidiEvent::noteOff(0, action.index));
        }
        int count = std::min(128, frames - pos);
        if (next < actions.size())
            count = std::min(count, actions[next].frame - pos);
        float left[128]{}, right[128]{};
        float *channels[] = {left, right};
        unsigned char bytes[512]{};
        if (useInput) {
            if (!input.read(reinterpret_cast<char *>(bytes), count * 4))
                return 2;
            for (int i = 0; i < count; ++i)
                for (int ch = 0; ch < 2; ++ch) {
                    const int offset = 4 * i + 2 * ch;
                    int raw = bytes[offset] + 256 * bytes[offset + 1];
                    channels[ch][i] = (raw >= 32768 ? raw - 65536 : raw) / 32768.f;
                }
        }
        mpc::ProcessContext c{};
        c.outputs = channels;
        c.inputs = channels;
        c.numInputs = p->info().numInputs;
        c.numOutputs = 2;
        c.numFrames = count;
        c.sampleRate = 44100;
        c.transport.valid = c.transport.playing = c.transport.tempoValid = c.transport.ppqValid = true;
        c.transport.bpm = bpm;
        c.transport.ppqPos = pos * bpm / (60 * 44100);
        c.transport.samplePos = pos;
        c.midi = events.data();
        c.numMidiEvents = static_cast<int>(events.size());
        p->process(c);
        for (int i = 0; i < count; ++i)
            for (int ch = 0; ch < 2; ++ch) {
                float sample = channels[ch][i];
                if (!std::isfinite(sample))
                    return 1;
                int v = std::clamp(static_cast<int>(std::lround(sample * 32768)), -32768, 32767);
                bytes[4 * i + 2 * ch] = static_cast<uint8_t>(v);
                bytes[4 * i + 2 * ch + 1] = static_cast<uint8_t>(static_cast<uint16_t>(v) >> 8);
            }
        if (!output.write(reinterpret_cast<char *>(bytes), count * 4))
            return 1;
        pos += count;
    }
    // Preset recall uses the same SDK state serialization as the plugin binary.
    for (int i = 0; i < p->numParams(); ++i)
        p->setNormalised(i, .76f);
    const auto state = p->internalSaveState();
    std::vector<float> before;
    for (int i = 0; i < p->numParams(); ++i) {
        before.push_back(p->get(i));
        p->setNormalised(i, .13f);
    }
    if (!p->internalLoadState(state.data(), state.size()))
        return 1;
    for (int i = 0; i < p->numParams(); ++i)
        if (std::abs(p->get(i) - before[i]) > 1.e-4f)
            return 1;
    return 0;
}
