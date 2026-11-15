// SPDX-License-Identifier: MIT
#include "../../DrumHands/percussion.h"
#include <atomic>

class PhraseHands final : public mpc::Plugin {
    // Eight 7-bit notes and a 4-bit length. A save sees one completed phrase.
    static constexpr int shift = 56;
    std::atomic<uint64_t> phrase{(uint64_t(4) << shift) | 60 | (uint64_t(63) << 7)
                                | (uint64_t(67) << 14) | (uint64_t(65) << 21)};
    uint64_t draft = 0;
    int count = 0, cursor = 0, voice = 0;
    bool learning = false;
    std::array<percussion::Mallet, 12> voices{};
    static mpc::PluginInfo info() {
        mpc::PluginInfo p;
        p.name = "Phrase Hands";
        p.vendor = "FG Scratchpad";
        p.isInstrument = true;
        p.numInputs = 0;
        p.uniqueId = MPC_FOURCC('F','g','P','h');
        p.version = 1000;
        return p;
    }
    void sound(int key, int velocity, double sr) {
        key = std::clamp(key + 12 * int(std::round(get(3))), 0, 127);
        voices[voice].strike(key, velocity / 127. * .42, get(1) * .001,
                             get(2) * .01, 0., sr);
        voice = (voice + 1) % int(voices.size());
    }
    void input(const mpc::MidiEvent &e, double sr) {
        if (e.isAllNotesOff()) {
            reset();
            return;
        }
        int k = e.note();
        if (e.isNoteOff() && k == 40 && learning) {
            if (count) {
                phrase.store(draft | (uint64_t(count) << shift));
                cursor = 0;
            }
            learning = false;
        }
        if (!e.isNoteOn()) return;
        if (k == 40) {
            learning = true;
            draft = 0;
            count = 0;
        } else if (k == 41) {
            cursor = 0;
        } else if (k >= 48) {
            if (learning && count < 8) {
                draft |= uint64_t(k) << (7 * count++);
            }
            sound(k, e.velocity(), sr);
        } else if (k >= 36 && k <= 39 && !learning) {
            const auto saved = phrase.load();
            const int length = int(saved >> shift);
            int i = cursor % length;
            if (k == 37) i = length - 1 - i;
            if (k == 38) i = i % 2 ? length - 1 - i / 2 : i / 2;
            if (k == 39) i = (e.velocity() - 1) * length / 127;
            sound(int((saved >> (7*i)) & 127), e.velocity(), sr);
            cursor = (cursor + 1) % length;
        }
    }
  public:
    PhraseHands() : Plugin(info()) {
        addParam(mpc::floatParam("level", "Level", 0, 100, 75, "%", 0));
        addParam(mpc::logParam("decay", "Decay", 30, 900, 210, "ms", 0));
        addParam(mpc::floatParam("tone", "Brightness", 0, 100, 50, "%", 0));
        addParam(mpc::floatParam("oct", "Register", -2, 2, 0, "oct", 0));
        addProgram("Pocket mallet", {75,210,50,0});
        addProgram("Bass knocks", {82,160,25,-1});
    }
    void reset() override {
        voices = {};
        cursor = voice = count = 0;
        learning = false;
    }
    void process(mpc::ProcessContext &c) override {
        int event = 0;
        const double level = get(0) * .01;
        for (int i = 0; i < c.numFrames; i++) {
            while (event < c.numMidiEvents && c.midi[event].sampleOffset <= i)
                input(c.midi[event++], c.sampleRate);
            double left=0, right=0;
            for (auto &v : voices) v.add(left,right);
            c.outputs[0][i] = std::tanh(left*level);
            c.outputs[1][i] = std::tanh(right*level);
        }
    }
    void saveExtraState(std::vector<uint8_t> &out) override {
        const auto word = phrase.load();
        out.push_back(1);
        for (int i=0; i<8; i++) out.push_back(uint8_t(word >> (8*i)));
    }
    void loadExtraState(const uint8_t *bytes, size_t size) override {
        if (size != 9 || bytes[0] != 1) return;
        uint64_t word = 0;
        for (int i=0; i<8; i++) word |= uint64_t(bytes[i+1]) << (8*i);
        const auto length = word >> shift;
        if (!length || length > 8) return;
        phrase.store(word);
    }
};
MPC_PLUGIN_ENTRY(PhraseHands)
