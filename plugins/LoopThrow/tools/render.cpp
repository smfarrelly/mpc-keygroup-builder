// Offline Loop Throw renderer. The Python front end supplies validated timing
// and streams stereo PCM16 little-endian frames through stdin/stdout.
#include "../src/LoopThrow.cpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>

int main(int argc, char** argv)
{
    if (argc != 8) return 2;
    const double rate = std::stod(argv[1]);
    const double bpm = std::stod(argv[2]);
    const auto open = std::stoll(argv[3]);
    const auto close = std::stoll(argv[4]);
    LoopThrow effect;
    effect.set(LoopThrow::Division, std::stof(argv[5]));
    effect.set(LoopThrow::Repeats, std::stof(argv[6]));
    effect.set(LoopThrow::Tone, std::stof(argv[7]));
    // A throw beginning on the first sample should catch the initial transient.
    effect.set(LoopThrow::Throw, open == 0 ? 100 : 0);
    constexpr int block = 128;
    effect.prepare(rate, block);
    effect.reset();
    std::int64_t position = 0;
    std::array<unsigned char, block * 4> pcm;
    std::array<float, block> left, right;
    long clipped = 0;
    while (true) {
        const bool active = position >= open && position < close;
        effect.set(LoopThrow::Throw, active ? 100 : 0);
        int count = block;
        // Split exactly on gesture boundaries, even in the middle of a block.
        for (auto boundary : {open, close})
            if (boundary > position && boundary < position + count)
                count = static_cast<int>(boundary - position);
        const auto bytes = std::fread(pcm.data(), 1, count * 4, stdin);
        if (bytes % 4 || std::ferror(stdin)) return 1;
        if (bytes == 0) break;
        count = static_cast<int>(bytes / 4);
        float* channels[] = {left.data(), right.data()};
        for (int i = 0; i < count; ++i) {
            for (int ch = 0; ch < 2; ++ch) {
                const int offset = i * 4 + ch * 2;
                const int raw = pcm[offset] | (pcm[offset + 1] << 8);
                channels[ch][i] = (raw >= 32768 ? raw - 65536 : raw) / 32768.0f;
            }
        }
        mpc::ProcessContext ctx;
        ctx.inputs = channels;
        ctx.outputs = channels;
        ctx.numFrames = count;
        ctx.numInputs = ctx.numOutputs = 2;
        ctx.sampleRate = rate;
        ctx.transport.bpm = bpm;
        effect.process(ctx);
        for (int i = 0; i < count; ++i) {
            for (int ch = 0; ch < 2; ++ch) {
                const auto sample = std::lround(channels[ch][i] * 32768.0f);
                if (sample < -32768 || sample > 32767) ++clipped;
                const auto raw = static_cast<std::uint16_t>(std::clamp(sample, -32768L, 32767L));
                const int offset = i * 4 + ch * 2;
                pcm[offset] = raw & 255;
                pcm[offset + 1] = raw >> 8;
            }
        }
        if (std::fwrite(pcm.data(), 1, bytes, stdout) != bytes) return 1;
        position += count;
    }
    if (clipped) std::fprintf(stderr, "%ld clipped channel samples: lower the source level for more headroom.\n", clipped);
    return std::fflush(stdout) == 0 ? 0 : 1;
}
