// SPDX-License-Identifier: MIT
#include "mpc_plugin.h"
#undef MPC_PLUGIN_ENTRY
#define MPC_PLUGIN_ENTRY(Class)
#include "../../ChordRelay/src/ChordRelay.cpp"
#include "../../ResonantKit/src/ResonantKit.cpp"
#include "../../Turnaround/src/Turnaround.cpp"
#include <cassert>
#include <fstream>
#include <iostream>

constexpr int rate = 32000, beat = rate / 2;
using Audio = std::vector<float>;
using Event = mpc::MidiEvent;
Audio play(mpc::Plugin &p, int start, const Audio &in, std::vector<Event> events = {}, int block = 128) {
    Audio out(in.size()), right(in.size()), silent(in.size());
    for (int pos = 0; pos < int(in.size()); pos += block) {
        mpc::ProcessContext c{};
        c.numFrames = std::min(block, int(in.size()) - pos);
        const float *inputs[] = {in.data() + pos, silent.data() + pos};
        float *outputs[] = {out.data() + pos, right.data() + pos};
        c.inputs = inputs;
        c.outputs = outputs;
        c.numInputs = 2;
        c.numOutputs = 2;
        c.sampleRate = rate;
        c.transport.valid = c.transport.ppqValid = c.transport.playing = c.transport.tempoValid = true;
        c.transport.ppqPos = (start + pos) / double(beat);
        std::vector<Event> midi;
        for (auto e : events)
            if (e.sampleOffset >= pos && e.sampleOffset < pos + c.numFrames) {
                e.sampleOffset -= pos;
                midi.push_back(e);
            }
        c.midi = midi.data();
        c.numMidiEvents = midi.size();
        p.process(c);
    }
    assert(std::all_of(out.begin(), out.end(), [](float x) { return std::isfinite(x); }));
    if (dynamic_cast<ChordRelay *>(&p) == nullptr)
        assert(right == silent);
    return out;
}
Audio groove(int start, int frames) {
    Audio a(frames);
    for (int i = 0; i < frames; i++) {
        int t = (start + i) % (beat / 2), hit = (start + i) / (beat / 2);
        a[i] = (.4 + .08 * (hit % 4)) * std::exp(-t / 1700.) * std::cos(t * (hit % 2 ? .075 : .019));
    }
    return a;
}
Audio fill(Turnaround &fx, int arm, int mode, int span) {
    fx.set(1, mode);
    fx.set(2, span);
    play(fx, 0, groove(0, arm));
    fx.set(0, 1);
    return play(fx, arm, groove(arm, 17 * beat - arm));
}
double power(const Audio &a, int start, int end) {
    double energy = 0;
    for (int i = start; i < end; i++)
        energy += a[i] * a[i];
    return energy;
}
void timing() {
    const int arms[] = {8 * beat, 9 * beat + 901, 11 * beat + 111};
    Audio reference;
    for (int arm : arms) {
        Turnaround fx;
        auto audio = fill(fx, arm, 1, 2), dry = groove(arm, audio.size());
        assert(std::equal(audio.begin(), audio.begin() + 15 * beat - arm, dry.begin()));
        assert(std::equal(audio.end() - beat, audio.end(), dry.end() - beat));
        Audio tail(audio.end() - 2 * beat, audio.end() - beat);
        assert(power(tail, 0, beat) > 1 && !std::equal(tail.begin(), tail.end(), dry.end() - 2 * beat));
        if (reference.empty())
            reference = tail;
        else
            assert(reference == tail);
        fx.set(3, 1);
        auto state = fx.internalSaveState();
        Turnaround reopened;
        assert(reopened.internalLoadState(state.data(), state.size()));
        reopened.set(0, 1);
        auto repeat = play(reopened, 0, Audio(16 * beat));
        assert(std::equal(tail.begin() + 128, tail.end() - 128, repeat.begin() + 15 * beat + 128));
    }
    for (int mode : {0, 2}) {
        Turnaround fx;
        auto a = fill(fx, 8 * beat, mode, 0);
        auto dry = groove(8 * beat, a.size());
        assert(std::equal(a.begin(), a.end() - beat - beat / 4, dry.begin()));
        assert(!std::equal(a.end() - beat - beat / 4, a.end() - beat, dry.end() - beat - beat / 4));
    }
}
void resonance() {
    Audio soft(rate), loud(rate);
    soft[0] = .1;
    loud[0] = .8;
    ResonantKit fx;
    fx.set(3, 0);
    assert(play(fx, 0, loud) == loud);
    fx.set(3, 100);
    fx.reset();
    auto a = play(fx, 0, soft);
    fx.reset();
    auto b = play(fx, 0, loud);
    assert(power(a, 1, 4000) > 0);
    double difference = 0;
    for (int i = 1; i < 4000; i++)
        difference += std::abs(8 * a[i] - b[i]);
    assert(difference > .1);
    fx.set(1, 70);
    fx.reset();
    auto shortTail = play(fx, 0, soft);
    fx.set(1, 1500);
    fx.reset();
    auto longTail = play(fx, 0, soft);
    assert(power(longTail, rate / 2, rate) > 100 * power(shortTail, rate / 2, rate));
    fx.set(0, 60);
    fx.reset();
    assert(play(fx, 0, soft) != longTail);
}
void teach(ChordRelay &p, int slot, std::vector<int> notes) {
    p.set(0, 1);
    std::vector<Event> events;
    for (int n : notes)
        events.push_back(Event::noteOn(0, n, 90));
    events.push_back(Event::noteOn(0, slot, 90, 13));
    for (int n : notes)
        events.push_back(Event::noteOff(0, n, 19));
    play(p, 0, Audio(64), events);
    p.set(0, 0);
    play(p, 0, Audio(64));
}
void chords() {
    ChordRelay p;
    teach(p, 36, {62, 65, 69});
    teach(p, 40, {58, 62, 65});
    teach(p, 36, {});
    std::vector<uint8_t> notes;
    p.saveExtraState(notes);
    assert(notes == std::vector<uint8_t>({1, 62, 65, 69, 0, 0, 0, 58, 62, 65, 0, 0, 0}));
    auto state = p.internalSaveState();
    ChordRelay reopened;
    assert(reopened.internalLoadState(state.data(), state.size()));
    std::vector<Event> phrase;
    for (int bar = 0; bar < 8; bar++) {
        int slot = bar % 2 ? 40 : 36;
        phrase.push_back(Event::noteOn(0, slot, 100, bar * 4 * beat));
        phrase.push_back(Event::noteOn(0, slot + 1, 34, bar * 4 * beat + beat));
        phrase.push_back(Event::noteOn(0, slot + 2, 110, bar * 4 * beat + 2 * beat));
    }
    auto audio = play(p, 0, Audio(32 * beat), phrase);
    assert(power(audio, 0, audio.size()) > 100 &&
           play(reopened, 0, Audio(audio.size()), phrase, 191) == audio);
    ChordRelay single;
    teach(single, 36, {69});
    p.reset();
    auto top = std::vector<Event>{Event::noteOn(0, 36, 35)};
    assert(play(p, 0, Audio(2000), top) == play(single, 0, Audio(2000), top));
    p.reset();
    // Two slots containing the same pitch should hand it over without a second attack.
    ChordRelay common;
    teach(common, 36, {65});
    teach(common, 40, {65});
    auto first = Event::noteOn(0, 36, 100);
    auto sustained = play(common, 0, Audio(4000), {first});
    common.reset();
    assert(play(common, 0, Audio(4000), {first, Event::noteOn(0, 40, 100, 951)}) == sustained);
    auto invalid = notes;
    invalid[1] = 0;
    p.loadExtraState(invalid.data(),invalid.size());
    std::vector<uint8_t> preserved;
    p.saveExtraState(preserved);
    assert(preserved == notes);
    p.set(1, 0);
    auto spread = std::vector<Event>{Event::noteOn(0, 38, 110)};
    auto simultaneous = play(p, 0, Audio(3000), spread);
    p.reset();
    p.set(1, 120);
    assert(play(p, 0, Audio(3000), spread) != simultaneous);
}
// An original eight-bar audition. The last beat of each four-bar phrase uses the insert.
void audition(const char *path) {
    ChordRelay keys;
    ResonantKit ring;
    Turnaround fill;
    Audio mix;
    for (int bar = 0; bar < 8; bar++) {
        const int start = bar * 4 * beat;
        Audio drums = play(ring, start, groove(start, 4 * beat));
        if (bar % 4 == 2)
            fill.set(0, 1);
        drums = play(fill, start, drums);
        const int slot = bar % 2 ? 40 : 36;
        auto harmony = play(keys, start, Audio(4 * beat),
                            {Event::noteOn(0, slot, 98), Event::noteOn(0, slot + 1, 40, beat),
                             Event::noteOn(0, slot + 2, 102, 2 * beat)});
        for (size_t i = 0; i < drums.size(); i++)
            mix.push_back(.47f * drums[i] + .5f * harmony[i]);
    }
    std::ofstream file(path, std::ios::binary);
    auto le = [&](unsigned value, int bytes) {
        while (bytes--) {
            file.put(char(value & 255));
            value >>= 8;
        }
    };
    file.write("RIFF", 4);
    le(36 + 2 * mix.size(), 4);
    file.write("WAVEfmt ", 8);
    le(16, 4);
    le(1, 2);
    le(1, 2);
    le(rate, 4);
    le(2 * rate, 4);
    le(2, 2);
    le(16, 2);
    file.write("data", 4);
    le(2 * mix.size(), 4);
    for (float value : mix)
        le(uint16_t(int16_t(std::lround(32767 * std::clamp(value, -1.f, 1.f)))), 2);
    file.close();
    if (!file)
        throw std::runtime_error("could not write audition WAV");
}
int main(int argc, char **argv) {
    timing();
    resonance();
    chords();
    if (argc == 2)
        audition(argv[1]);
    std::cout << "Fill timing, held audio reopen, accent response and eight-bar chord replay passed.\n";
}
