// Compile against the same SDK headers as the plugin. Test the DSP directly
// so a simulator success on a dry signal cannot conceal a broken delay send.
#include "../src/LoopThrow.cpp"
#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <vector>

static void require(bool condition, const char* message)
{
    if (!condition) {
        std::cerr << message << '\n';
        std::exit(1);
    }
}

static std::vector<float> render(double bpm, int division, int blockSize, bool open)
{
    constexpr int sampleRate = 44100;
    const float beats[] = {0.25f, 0.5f, 0.75f, 1.0f};
    const int interval = static_cast<int>(std::lround(beats[division] * 60 * sampleRate / bpm));
    const int closedHit = 2 * interval + interval / 2;
    std::vector<float> left(4 * interval + 128), right(left.size());
    left[0] = 0.5f;
    left[closedHit] = 0.3f;

    LoopThrow effect;
    effect.set(LoopThrow::Throw, open ? 100 : 0);
    effect.set(LoopThrow::Division, static_cast<float>(division));
    effect.set(LoopThrow::Repeats, 50);
    effect.prepare(sampleRate, blockSize);
    effect.reset();

    for (int pos = 0; pos < static_cast<int>(left.size()); pos += blockSize) {
        if (pos >= blockSize)
            effect.set(LoopThrow::Throw, 0);
        float* channels[] = {left.data() + pos, right.data() + pos};
        mpc::ProcessContext ctx;
        ctx.inputs = channels;
        ctx.outputs = channels;
        ctx.numInputs = ctx.numOutputs = 2;
        ctx.numFrames = std::min(blockSize, static_cast<int>(left.size()) - pos);
        ctx.transport.bpm = bpm;
        ctx.sampleRate = sampleRate;
        effect.process(ctx);
    }

    require(left[0] == 0.5f && left[closedHit] == 0.3f, "dry transient changed");
    require(std::all_of(right.begin(), right.end(), [](float v) { return v == 0; }), "stereo bleed");
    require(std::abs(left[closedHit + interval]) < 0.000001f, "a closed send leaked a new hit");
    if (open) {
        require(left[interval] > 0.02f, "missing first tempo-synced echo");
        require(left[2 * interval] > 0.005f, "stored repeats stopped when Throw closed");
        require(left[2 * interval] < left[interval], "repeats failed to decay");
    } else {
        left[0] = left[closedHit] = 0;
        require(std::all_of(left.begin(), left.end(), [](float v) { return v == 0; }), "dry default leaked echo");
    }
    return left;
}

int main()
{
    for (int division = 0; division < 4; ++division) {
        for (double bpm : {75.0, 120.0, 150.0}) {
            const auto reference = render(bpm, division, 32, true);
            require(reference == render(bpm, division, 512, true), "delay timing changed with block size");
            render(bpm, division, 128, false);
        }
    }
    std::cout << "Passed impulse checks for all four divisions, three tempos, dry and throw states.\n";
}
