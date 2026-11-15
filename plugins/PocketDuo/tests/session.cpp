// Software acceptance through the SDK's MIDI, audio and state entry points.
#include "mpc_plugin.h"
#undef MPC_PLUGIN_ENTRY
#define MPC_PLUGIN_ENTRY(Class)
#include "../src/PocketDuo.cpp"
#include <cassert>
#include <fstream>
#include <iostream>

constexpr int rate = 48000, bar = 96000;
struct Stroke {
    int sample, key, vel;
};
using Audio = std::vector<float>;
Audio render(PocketDuo &p, int start, int frames, bool transport, std::vector<Stroke> notes = {},
             int block = 128) {
    Audio out(frames);
    for (int pos = 0; pos < frames; pos += block) {
        int n = std::min(frames - pos, block);
        Audio right(n);
        float *channels[] = {out.data() + pos, right.data()};
        std::vector<mpc::MidiEvent> midi;
        for (const auto &e : notes)
            if (e.sample >= pos && e.sample < pos + n)
                midi.push_back(mpc::MidiEvent::noteOn(0, e.key, e.vel, e.sample - pos));
        mpc::ProcessContext c{};
        c.numFrames = n;
        c.outputs = channels;
        c.numOutputs = 2;
        c.sampleRate = rate;
        c.transport.valid = c.transport.tempoValid = c.transport.ppqValid = true;
        c.transport.playing = transport;
        c.transport.bpm = 120;
        c.transport.ppqPos = (start + pos) / 24000.;
        c.transport.samplePos = start + pos;
        c.midi = midi.data();
        c.numMidiEvents = midi.size();
        p.process(c);
        assert(std::equal(right.begin(), right.end(), channels[0]));
    }
    return out;
}
std::vector<uint8_t> extra(PocketDuo &p) {
    std::vector<uint8_t> data;
    p.saveExtraState(data);
    return data;
}
struct Note {
    int tick, gate, key, vel;
};
std::vector<Note> unpack(const std::vector<uint8_t> &s) {
    size_t i = 2 + s.at(1);
    auto word = [&]() {
        int n = s.at(i) + 256 * s.at(i + 1);
        i += 2;
        return n;
    };
    word();
    const int count = word();
    std::vector<Note> out;
    while (int(out.size()) < count) {
        int t = word(), g = word(), k = s.at(i++), v = s.at(i++);
        out.push_back({t, g, k, v});
    }
    assert(i == s.size());
    return out;
}
void wav(const char *path, const Audio &audio) {
    std::ofstream f(path, std::ios::binary);
    auto le = [&](unsigned x, int n) {
        while (n--) {
            f.put(char(x & 255));
            x >>= 8;
        }
    };
    f.write("RIFF", 4);
    le(36 + audio.size() * 2, 4);
    f.write("WAVEfmt ", 8);
    le(16, 4);
    le(1, 2);
    le(1, 2);
    le(rate, 4);
    le(rate * 2, 4);
    le(2, 2);
    le(16, 2);
    f.write("data", 4);
    le(audio.size() * 2, 4);
    for (float x : audio)
        le(uint16_t(std::lround(x * 32767)), 2);
    assert(f.good());
}
int main(int argc, char **argv) {
    PocketDuo p;
    p.prepare(rate, 128);
    p.reset();
    p.set(1, 1);
    const Audio silent = render(p, 0, 256, false, {{0, 38, 90}, {32, 41, 90}, {64, 45, 90}});
    assert(std::all_of(silent.begin(), silent.end(), [](float x) { return x == 0; }));
    p.set(1, 0);
    p.set(0, 85);
    std::vector<Stroke> strokes = {{0, 36, 96},     {6000, 42, 72},  {11900, 36, 38},
                                   {19250, 43, 93}, {24600, 38, 96}, {41400, 36, 111},
                                   {48250, 42, 78}, {60500, 36, 98}, {72200, 38, 101}};
    Audio live = render(p, 0, bar, true, strokes);
    // Begin a different pass; keep must recall the previous complete one.
    render(p, bar, 3000, true, {{100, 49, 111}});
    p.set(2, 1);
    render(p, bar + 3000, 128, true);
    const auto raw = extra(p);
    const auto notes = unpack(raw);
    std::vector<int> keys, vels;
    for (const auto &e : notes) {
        assert(e.key != 49);
        if (e.gate) {
            keys.push_back(e.key);
            vels.push_back(e.vel);
        }
    }
    assert((keys == std::vector<int>{38, 38, 41, 45, 45}));
    assert((vels == std::vector<int>{96, 38, 111, 74, 98}));
    assert(raw[1] == 3 && raw[2] == 38 && raw[3] == 41 && raw[4] == 45);
    const auto saved = p.internalSaveState();
    auto replay = [&](int block, float activity, bool drums) {
        PocketDuo fresh;
        fresh.prepare(rate, block);
        assert(fresh.internalLoadState(saved.data(), saved.size()));
        fresh.set(0, activity);
        fresh.set(3, drums ? 0 : 1);
        return render(fresh, 0, bar, true, {}, block);
    };
    Audio recalled = replay(37, 0, true);
    assert(recalled == replay(128, 100, true));
    assert(*std::max_element(recalled.begin(), recalled.end()) > .1f);
    const auto bass = replay(97, 50, false);
    assert(bass != recalled && *std::max_element(bass.begin(), bass.end()) > .1f);
    PocketDuo loaded;
    loaded.prepare(rate, 128);
    assert(loaded.internalLoadState(saved.data(), saved.size()));
    loaded.set(3, 1);
    auto overdub = render(loaded, 0, bar, true, {{12345, 39, 105}});
    assert(std::equal(bass.begin(), bass.begin() + 12345, overdub.begin()) && bass != overdub);
    auto corrupt = raw;
    corrupt.pop_back();
    loaded.loadExtraState(corrupt.data(), corrupt.size());
    assert(extra(loaded) == raw);
    PocketDuo idle;
    idle.prepare(rate, 128);
    auto immediate = render(idle, 0, 5000, false, {{1536, 36, 100}});
    assert(*std::max_element(immediate.begin(), immediate.begin() + 1536) == 0 && immediate[1537] != 0);
    idle.set(2, 1);
    render(idle, 0, 128, false);
    assert(unpack(extra(idle)).size() == 2);
    for (int choice : {1, 2}) {
        PocketDuo longer;
        longer.prepare(rate, 128);
        longer.set(4, choice);
        longer.reset();
        const int samples = bar * (1 << choice);
        render(longer, 0, samples, true, {{250, 36, 95}, {samples - 2400, 36, 43}});
        longer.set(2, 1);
        render(longer, samples, 128, true);
        const auto hits = unpack(extra(longer));
        assert(hits.size() == 4 && std::abs(hits.back().tick - (samples - 2400) / 25) <= 1);
    }
    // Stopping a moving transport and starting a free pass must not splice a
    // second set of zero-based timestamps onto the old one.
    PocketDuo stopped;
    stopped.prepare(rate, 128);
    render(stopped, 0, bar / 2, true, {{bar / 4, 36, 100}});
    render(stopped, 0, bar, false, {{0, 37, 100}, {bar / 2, 38, 90}});
    stopped.set(2, 1);
    render(stopped, 0, 128, false);
    const auto freePass = unpack(extra(stopped));
    assert(freePass.size() == 3 && freePass.front().key == 37 && freePass.back().key == 38);
    PocketDuo overflow;
    overflow.prepare(rate, 128);
    std::vector<Stroke> flood(1025, {0, 42, 80});
    render(overflow, 0, 256, false, flood);
    overflow.set(2, 1);
    render(overflow, 0, 128, false);
    assert(overflow.get(2) == 0 && unpack(extra(overflow)).empty());
    if (argc == 2) {
        live.insert(live.end(), recalled.begin(), recalled.end());
        live.insert(live.end(), overdub.begin(), overdub.end());
        wav(argv[1], live);
    }
    std::cout << "Passed free play, learned notes, ghost, pickup, completed/partial keep, saved-state "
                 "recall, live drum replacement and corrupt state.\n";
}
