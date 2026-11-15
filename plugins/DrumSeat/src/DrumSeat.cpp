// SPDX-License-Identifier: MIT
#include "../../GhostWire/src/GhostWire.h"
#include "../../RestReply/src/RestReply.h"
#include "../../RudimentKeys/src/RudimentKeys.h"

class DrumSeat final : public mpc::Plugin {
    enum {
        Follow,
        MelodyLevel,
        ReplyLevel,
        Root,
        DrumLevel,
        Snares,
        Gap,
        Keep,
        LearnHands,
        LeftInput,
        RightInput
    };
    enum Mode { Ghosts, Sticking, Accents, Rests };
    int firstLearned = -1;
    bool wasLearning = false;
    GhostWire kit;
    RudimentKeys keys;
    RestReply reply;
    static constexpr int Block = 128;
    // The SDK admits at most 1024 MIDI events per callback.
    std::array<mpc::MidiEvent, 1024> drumEvents{}, melodyEvents{};
    using Stereo = std::array<std::array<float, Block>, 2>;
    Stereo drum{}, melody{}, response{};
    static mpc::PluginInfo metadata() {
        mpc::PluginInfo p;
        p.name = "Drum Seat";
        p.vendor = "FG Scratchpad";
        p.isInstrument = true;
        p.numInputs = 0;
        p.uniqueId = MPC_FOURCC('F', 'g', 'D', 'S');
        p.version = 1000;
        return p;
    }
    bool routeHand(mpc::MidiEvent &event) {
        if (!event.isNoteOn())
            return true;
        const int key = event.note();
        if (getBool(LearnHands)) {
            if (firstLearned < 0)
                firstLearned = key;
            else if (key != firstLearned) {
                set(LeftInput, firstLearned);
                set(RightInput, key);
                set(LearnHands, 0);
                firstLearned = -1;
                wasLearning = false;
            }
            return false;
        }
        if (key == getInt(LeftInput))
            event.data[1] = 36;
        else if (key == getInt(RightInput))
            event.data[1] = 37;
        return true;
    }
    bool melodyEvent(mpc::MidiEvent &e, int mode) {
        if (e.isAllNotesOff())
            return true;
        if (!e.isNoteOn())
            return false;
        const int key = e.note(), vel = e.velocity();
        if (key >= 48 && key <= 79) {
            set(Root, key);
            return true;
        }
        if (key == 44) {
            e.data[1] = 43;
            return true;
        }
        if (key < 36 || key > 43 || mode == Rests)
            return false;
        const int side = (key - 36) % 2;
        if (mode == Ghosts) {
            if (vel >= 60)
                return false;
            // A quiet stroke can carry a clear pitched line beneath loud backbeats.
            e.data[1] = 36 + side;
            e.data[2] = 64 + vel / 2;
        } else if (mode == Accents) {
            if (vel < 98)
                return false;
            e.data[1] = 38 + side;
        } else if (key >= 42) {
            e.data[1] = 36 + side;
            e.data[2] = std::min(47, vel);
        }
        return true;
    }

  public:
    DrumSeat() : Plugin(metadata()) {
        addParam(mpc::choiceParam("follow", "Follow",
                                  {"Ghost notes", "Sticking", "Accents", "Rests only"}, Ghosts));
        addParam(mpc::floatParam("melody", "Melody Level", 0, 100, 65, "%", 0));
        addParam(mpc::floatParam("reply", "Reply Level", 0, 100, 45, "%", 0));
        addParam(mpc::intParam("root", "Root", 30, 79, 50, "MIDI"));
        addParam(mpc::floatParam("drums", "Drum Level", 0, 100, 83, "%", 0));
        addParam(mpc::floatParam("snares", "Snares", 0, 100, 72, "%", 0));
        addParam(
            mpc::choiceParam("gap", "Reply Gap", {"Eighth", "Quarter", "Dotted quarter", "Half"}, 1));
        addParam(mpc::boolParam("keep", "Keep Call", false));
        addParam(mpc::boolParam("learn_hands", "Learn Hands", false));
        addParam(mpc::intParam("left_input", "Left Input", 0, 127, 36, "MIDI"));
        addParam(mpc::intParam("right_input", "Right Input", 0, 127, 37, "MIDI"));
        // Sound presets deliberately cover only the musical controls; retain the player's pad map.
        addProgram("Ghost Line", {Ghosts, 65, 45, 50, 83, 72, 1, 0});
        addProgram("Accent Stabs", {Accents, 72, 10, 45, 78, 55, 2, 0});
        addProgram("Trade Phrases", {Rests, 0, 85, 55, 79, 63, 0, 0});
        addProgram("Two Mallets", {Sticking, 86, 16, 62, 53, 35, 2, 0});
    }
    void reset() override {
        firstLearned = -1;
        wasLearning = false;
        kit.reset();
        keys.reset();
        reply.reset();
    }
    void process(mpc::ProcessContext &c) override {
        const bool learning = getBool(LearnHands);
        if (learning != wasLearning) {
            firstLearned = -1;
            if (learning) {
                kit.reset();
                keys.reset();
                reply.reset();
            }
        }
        wasLearning = learning;
        kit.set(GhostWire::Snares, get(Snares));
        keys.set(RudimentKeys::Root, get(Root));
        reply.set(RestReply::Gap, get(Gap));
        reply.set(RestReply::Keep, get(Keep));
        reply.set(RestReply::Level, 100);
        const int mode = getInt(Follow);
        const double drumGain = .01 * get(DrumLevel), keysGain = .01 * get(MelodyLevel),
                     replyGain = .01 * get(ReplyLevel);
        int next = 0;
        for (int pos = 0; pos < c.numFrames;) {
            int nd = 0, nk = 0;
            while (next < c.numMidiEvents && c.midi[next].sampleOffset <= pos) {
                auto e = c.midi[next++];
                e.sampleOffset = 0;
                if (!routeHand(e))
                    continue;
                if (e.isAllNotesOff())
                    reply.reset();
                if (nd < int(drumEvents.size()))
                    drumEvents[nd++] = e;
                if (melodyEvent(e, mode) && nk < int(melodyEvents.size()))
                    melodyEvents[nk++] = e;
            }
            int n = std::min(Block, c.numFrames - pos);
            if (next < c.numMidiEvents)
                n = std::min(n, c.midi[next].sampleOffset - pos);
            auto part = c;
            part.numFrames = n;
            part.transport.samplePos += pos;
            part.transport.ppqPos += pos * percussion::tempo(c) / (60 * c.sampleRate);
            float *ds[] = {drum[0].data(), drum[1].data()};
            float *ks[] = {melody[0].data(), melody[1].data()};
            float *rs[] = {response[0].data(), response[1].data()};
            part.outputs = ds;
            part.midi = drumEvents.data();
            part.numMidiEvents = nd;
            kit.process(part);
            part.outputs = ks;
            part.midi = melodyEvents.data();
            part.numMidiEvents = nk;
            keys.process(part);
            reply.set(RestReply::Root, get(Root));
            part.inputs = ds;
            part.numInputs = 2;
            part.outputs = rs;
            part.midi = nullptr;
            part.numMidiEvents = 0;
            reply.process(part);
            for (int ch = 0; ch < 2; ch++)
                for (int i = 0; i < n; i++) {
                    // The listener always hears the dry drums, including when the drummer solos the
                    // answer.
                    double wet = rs[ch][i] - ds[ch][i];
                    c.outputs[ch][pos + i] =
                        std::tanh(.88 * (drumGain * ds[ch][i] + keysGain * ks[ch][i] + replyGain * wet));
                }
            pos += n;
        }
    }
    void saveExtraState(std::vector<uint8_t> &out) override { reply.saveExtraState(out); }
    void loadExtraState(const uint8_t *data, size_t n) override { reply.loadExtraState(data, n); }
};
MPC_PLUGIN_ENTRY(DrumSeat)
