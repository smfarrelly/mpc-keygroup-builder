// SPDX-License-Identifier: MIT
#include "mpc_plugin.h"
#include "dsp/delay_line.h"
#include "dsp/onepole.h"
#include "dsp/smoother.h"
#include "dsp/tempo.h"

#include <array>
#include <cmath>

class LoopThrow final : public mpc::Plugin
{
public:
    enum Parameter { Throw, Division, Repeats, Tone };

    LoopThrow() : Plugin(metadata())
    {
        addParam(mpc::floatParam("throw", "Throw", 0, 100, 0, "%", 0));
        addParam(mpc::choiceParam("division", "Division", {"1/16", "1/8", "1/8D", "1/4"}, 1));
        addParam(mpc::floatParam("repeats", "Repeats", 0, 85, 40, "%", 0));
        addParam(mpc::logParam("tone", "Tone", 400, 14000, 5500, "Hz", 0));
    }

    void prepare(double sampleRate, int) override
    {
        // Four seconds accommodates quarter notes down to 15 BPM.
        for (auto& line : delay)
            line.prepare(static_cast<int>(4 * sampleRate));
        send.setTime(5, sampleRate);
        feedback.setTime(15, sampleRate);
        interval.setTime(25, sampleRate);
    }

    void reset() override
    {
        for (auto& line : delay)
            line.reset();
        for (auto& filter : color)
            filter.reset();
        send.snap(getNormalised(Throw));
        feedback.snap(get(Repeats) * 0.01f);
        firstBlock = true;
    }

    void process(mpc::ProcessContext& ctx) override
    {
        static constexpr float beats[] = {0.25f, 0.5f, 0.75f, 1.0f};
        const float target = mpc::dsp::beatsToSamples(beats[getInt(Division)], ctx.transport.bpm, ctx.sampleRate);
        if (firstBlock) {
            interval.snap(target);
            firstBlock = false;
        }
        interval.setTarget(target);
        send.setTarget(getNormalised(Throw));
        feedback.setTarget(get(Repeats) * 0.01f);
        for (auto& filter : color)
            filter.setCutoff(get(Tone), ctx.sampleRate);

        for (int frame = 0; frame < ctx.numFrames; ++frame) {
            const float amount = send.process();
            const float regeneration = feedback.process();
            const float tap = interval.process();
            for (int channel = 0; channel < 2; ++channel) {
                const float dry = ctx.inputs[channel][frame];
                const float echo = color[channel].process(delay[channel].readLinear(tap));
                // Closing Throw stops new hits entering the delay; stored repeats ring out.
                delay[channel].write(dry * amount + echo * regeneration);
                // Preserve the dry transient. Bound only the return; leave mixer headroom.
                ctx.outputs[channel][frame] = dry + 0.5f * (echo / (1.0f + std::abs(echo)));
            }
        }
    }

private:
    static mpc::PluginInfo metadata()
    {
        mpc::PluginInfo info;
        info.name = "Loop Throw";
        info.vendor = "FG Scratchpad";
        info.uniqueId = MPC_FOURCC('F', 'g', 'L', 't');
        info.version = 1000;
        info.isInstrument = false;
        info.numInputs = info.numOutputs = 2;
        return info;
    }

    std::array<mpc::dsp::DelayLine, 2> delay;
    std::array<mpc::dsp::OnePoleLP, 2> color;
    mpc::dsp::Smoother send, feedback, interval;
    bool firstBlock = true;
};

MPC_PLUGIN_ENTRY(LoopThrow)
