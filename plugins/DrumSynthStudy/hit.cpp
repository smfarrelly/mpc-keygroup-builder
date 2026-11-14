// Render Akai's SDK example directly so preset and note velocity are explicit.
// Compile with the SDK framework and examples/DrumSynth/src on the include path.
#include "DrumSynth.cpp"
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>

int main(int argc, char** argv) {
    if (argc != 4) return 2;
    int program = std::stoi(argv[1]), note = std::stoi(argv[2]), velocity = std::stoi(argv[3]);
    if (program < 0 || program > 1 || note < 36 || note > 43 || velocity < 1 || velocity > 127) return 2;
    DrumSynth synth;
    synth.setProgram(program);
    constexpr int rate = 44100, block = 128;
    synth.prepare(rate, block);
    synth.reset();
    auto hit = mpc::MidiEvent::noteOn(0, note, velocity);
    for (int pos = 0; pos < 2 * rate; pos += block) {
        std::array<float, block> left{}, right{};
        float* stereo[] = {left.data(), right.data()};
        mpc::ProcessContext ctx{};
        ctx.sampleRate = rate;
        ctx.numFrames = std::min(block, 2 * rate - pos);
        ctx.numOutputs = 2;
        ctx.outputs = stereo;
        ctx.midi = &hit;
        ctx.numMidiEvents = pos == 0 ? 1 : 0;
        synth.process(ctx);
        for (int i = 0; i < ctx.numFrames; ++i) {
            for (auto channel : stereo) {
                auto value = static_cast<uint16_t>(std::lround(std::clamp(channel[i], -1.f, 1.f) * 32767.f));
                unsigned char bytes[] = {static_cast<unsigned char>(value), static_cast<unsigned char>(value >> 8)};
                if (std::fwrite(bytes, 1, 2, stdout) != 2) return 1;
            }
        }
    }
    return std::fflush(stdout) == 0 ? 0 : 1;
}
