// SPDX-License-Identifier: MIT
#include "host.h"
#include <cctype>
using namespace testhost;
namespace fs = std::filesystem;
constexpr int rate = 32000, beat = rate / 2;
static fs::path binaries;
static std::string architecture;
fs::path binary(const char *folder, const char *slug) {
    if (!architecture.empty()) {
        std::string display(slug);
        bool word = true;
        for (char &c : display) {
            if (c == '-') {
                c = ' ';
                word = true;
            } else if (word) {
                c = char(std::toupper(static_cast<unsigned char>(c)));
                word = false;
            }
        }
        return binaries / ("FG Scratchpad - VST - " + display) / "VST" /
               (std::string(slug) + "-" + architecture + ".so");
    }
    return binaries / folder / "build/native" / (std::string(slug) + ".so");
}
void ghostWire() {
    const auto so = binary("GhostWire", "ghost-wire");
    Plugin idle(so);
    assert(firstSound(idle.render(4096)) == -1);
    Plugin l(so), r(so), soft(so);
    auto left = l.render(4096, {{71, 36, 110}}), right = r.render(4096, {{71, 37, 110}});
    assert(firstSound(left) == 71 && left != right && left[0] != left[1]);
    auto ghost = soft.render(4096, {{71, 36, 35}});
    assert(energy(left, 71, 4000) > 4 * energy(ghost, 71, 4000));
    double color = 0;
    for (int i = 71; i < 4096; i++)
        color += std::abs(left[0][i] / 110 - ghost[0][i] / 35);
    assert(color > .1);
    Plugin press(so), released(so), pressure(so);
    auto roll = press.render(48000, {{0, 40, 100}});
    auto tap = released.render(48000, {{0, 40, 100}, {4000, 40, 0, 0x80}});
    auto heavy = pressure.render(48000, {{0, 40, 100}, {5000, 40, 120, 0xa0}});
    assert(energy(roll, 32000, 48000) > 100 && energy(tap, 32000, 48000) < .02);
    assert(heavy != roll && energy(heavy, 16000, 32000) > energy(roll, 16000, 32000));
    Plugin transport(so);
    transport.render(8192, {{27, 40, 107}});
    transport.playing = false;
    auto stopped = transport.render(2 * rate);
    assert(energy(stopped, rate, 2 * rate) < .001);
    Plugin choked(so), open(so);
    auto cut = choked.render(8000, {{0, 39, 105}, {800, 44, 100}});
    auto ring = open.render(8000, {{0, 39, 105}});
    assert(energy(cut, 1600, 6000) < .001 * energy(ring, 1600, 6000));
    // Panic from a held press must cancel future bounces as well as the current tail.
    assert(firstSound(press.render(beat, {{0, 123, 0, 0xb0}})) == -1);
    std::vector<Event> strokes = {{51, 45, 114},        {4011, 36, 32},       {6017, 39, 104},
                                  {8107, 40, 89},       {10000, 41, 102},     {12000, 90, 0, 0xd0},
                                  {12911, 40, 0, 0x80}, {13600, 41, 0, 0x80}, {14000, 46, 70}};
    Bytes state;
    Audio heard;
    {
        Plugin p(so);
        p.set(0, .25);
        p.set(1, .62);
        p.set(2, .81);
        p.set(3, .57);
        state = p.save();
        heard = p.render(rate, strokes);
    }
    {
        Plugin p(so, rate, 257);
        p.load(state);
        assert(p.render(rate, strokes) == heard && p.save() == state);
    }
    std::cout << "Ghost Wire: stereo hands, velocity, choke, press duration, pressure, panic and replay "
                 "passed.\n";
}
// Estimate the fundamental from a window of the rendered audio, independent of the plugin's scale logic.
int fundamental(const Audio &a, int start, int count, int sr) {
    double highest = -1;
    int best = 0;
    for (int note = 36; note <= 84; note++) {
        const double angle = 6.283185307179586 * 440 * std::pow(2., (note - 69) / 12.) / sr;
        double x = 0, y = 0;
        for (int i = 0; i < count; i++) {
            const double w = .5 - .5 * std::cos(6.283185307179586 * i / (count - 1));
            const double v = w * (a[0][start + i] + a[1][start + i]);
            x += v * std::cos(angle * i);
            y += v * std::sin(angle * i);
        }
        if (x * x + y * y > highest) {
            highest = x * x + y * y;
            best = note;
        }
    }
    return best;
}
void rudiments() {
    const auto so = binary("RudimentKeys", "rudiment-keys");
    const int keys[] = {36, 37, 36, 36, 37, 36, 37, 37, 36},
              vel[] = {115, 85, 83, 84, 82, 32, 85, 116, 84};
    const int pitches[] = {50, 53, 55, 53, 57, 57, 60, 57, 55};
    std::vector<Event> notes;
    for (int i = 0; i < 9; i++)
        notes.push_back({i * beat + 31, keys[i], vel[i]});
    Audio melody;
    Bytes state;
    {
        Plugin p(so);
        p.set(4, 0);
        p.set(5, 0);
        p.set(3, .32f);
        state = p.save();
        melody = p.render(9 * beat, notes);
        for (int i = 0; i < 9; i++) {
            const int actual = fundamental(melody, i * beat + 100, 3100, rate);
            if (actual != pitches[i])
                std::cerr << "stroke " << i << " expected " << pitches[i] << " heard " << actual << "\n";
            assert(actual == pitches[i]);
        }
    }
    {
        Plugin restored(so, rate, 193);
        restored.load(state);
        assert(restored.render(9 * beat, notes) == melody);
    }
    Plugin keyed(so);
    auto shifted = keyed.render(beat, {{0, 65, 100}, {100, 36, 116}});
    assert(firstSound(shifted) == 100 && fundamental(shifted, 300, 3000, rate) == 65);
    auto tune = keyed.save();
    Plugin recall(so);
    recall.load(tune);
    assert(fundamental(recall.render(beat, {{0, 36, 116}}), 200, 3000, rate) == 65);
    Plugin straight(so), flam(so), dyad(so);
    auto hit = straight.render(4000, {{0, 36, 100}}), grace = flam.render(4000, {{0, 40, 100}});
    assert(energy(grace, 0, 600) < energy(hit, 0, 600) * .45 &&
           energy(grace, 800, 1600) > energy(grace, 0, 600));
    assert(dyad.render(4000, {{0, 38, 100}}) != hit);
    assert(firstSound(flam.render(4000, {{0, 120, 0, 0xb0}})) == -1);
    std::cout << "Rudiment Keys: nine audible pitches, ghost and accent decisions, grace, dyad and root "
                 "recall passed.\n";
}
Audio callAudio(int frames) {
    auto a = silence(frames);
    a[0][0] = .39f;
    a[1][beat / 4] = .78f;
    a[0][3 * beat / 4] = .24f;
    return a;
}
void restReply() {
    const auto so = binary("RestReply", "rest-reply");
    const int frames = 4 * beat, first = 7 * beat / 4;
    auto call = callAudio(frames);
    Plugin dry(so);
    dry.set(3, 0);
    assert(dry.render(frames, {}, &call) == call);
    Audio reply;
    Bytes state;
    {
        Plugin p(so);
        p.set(6, 0);
        reply = p.render(frames, {}, &call);
        for (int ch = 0; ch < 2; ch++)
            assert(std::equal(reply[ch].begin(), reply[ch].begin() + first, call[ch].begin()));
        assert(firstSound(reply, 3 * beat / 4 + 1) == first && energy(reply, first, first + 1000) > 1);
        p.set(2, 1);
        state = p.save();
    }
    {
        Plugin p(so, rate, 251);
        p.load(state);
        auto cue = silence(frames);
        cue[1][0] = .15f;
        auto recalled = p.render(frames, {}, &cue);
        assert(firstSound(recalled, 1) == beat);
        for (int ch = 0; ch < 2; ch++)
            assert(std::equal(reply[ch].begin() + first, reply[ch].end(), recalled[ch].begin() + beat));
        assert(p.save() == state);
    }
    // Echo starts with the first interval; reverse starts with the last one.
    Plugin echo(so);
    echo.set(6, 0);
    echo.set(1, 0);
    auto forward = echo.render(frames, {}, &call);
    assert(energy(forward, first + beat / 4, first + beat / 4 + 800) >
           8 * energy(reply, first + beat / 4, first + beat / 4 + 800));
    Plugin cancel(so);
    cancel.set(6, 0);
    auto interrupted = call;
    interrupted[1][first + 300] = .7f;
    auto stopped = cancel.render(frames, {}, &interrupted);
    assert(energy(stopped, first + beat / 2, first + beat) <
           .001 * energy(reply, first + beat / 2, first + beat));
    // A single long-decaying kick and sustained input must not invent a second strike.
    Plugin tail(so);
    auto one = silence(frames);
    for (int i = 0; i < frames; i++)
        one[0][i] = float(.65 * std::exp(-i / 4200.) * std::cos(i * .019));
    assert(tail.render(frames, {}, &one) == one);
    Plugin drone(so);
    std::fill(one[1].begin(), one[1].end(), .44f);
    assert(drone.render(frames, {}, &one) == one);
    // Two audible hits at a slower tempo should receive a quarter-note wait at that tempo.
    Plugin slow(so);
    slow.bpm = 80;
    auto slowCall = silence(2 * rate);
    slowCall[1][0] = .8f;
    slowCall[0][7000] = .35f;
    assert(firstSound(slow.render(2 * rate, {}, &slowCall), 7001) == 7000 + 3 * rate / 4);
    std::cout << "Rest Reply: stereo detection, tempo, timing, reverse contour, tail rejection, "
                 "interruption and kept call recall passed.\n";
}
void splitCycle() {
    const auto so = binary("SplitCycle", "split-cycle");
    const int frames = 7 * beat, period = 3 * beat / 2;
    Plugin left(so);
    auto repeated = left.render(frames, {{0, 36, 100}});
    for (int start = period; start < frames - 200; start += period) {
        assert(firstSound(repeated, start - 20) == start);
        assert(std::equal(repeated[0].begin(), repeated[0].begin() + 200, repeated[0].begin() + start));
    }
    Plugin right(so);
    right.set(7, 0);
    auto bell = right.render(frames, {{0, 37, 100}});
    assert(firstSound(bell, beat) == 2 * beat);
    Plugin fresh(so), monitor(so);
    monitor.set(0, 0);
    auto finger = fresh.render(frames, {{beat / 5, 36, 99}}),
         solo = monitor.render(frames, {{beat / 5, 36, 99}});
    const int repeat = period + beat / 4; // performed at .20, stored at .25, heard immediately only once
    assert(std::equal(solo[0].begin(), solo[0].begin() + repeat, finger[0].begin()));
    assert(firstSound(finger, repeat - 30) == repeat);
    Bytes state;
    Audio mix;
    {
        Plugin p(so);
        p.set(7, 0);
        p.render(beat, {{0, 36, 100}, {0, 37, 80}, {beat / 2 + 80, 39, 50}});
        p.set(0, 0);
        state = p.save();
        p.render(128, {{0, 47, 100}});
        assert(p.save() != state);
        p.render(128, {{0, 44, 100}});
        assert(p.save() == state);
        p.position = 0;
        mix = p.render(frames);
    }
    {
        Plugin p(so, rate, 193);
        p.load(state);
        assert(p.render(frames) == mix && p.save() == state);
    }
    {
        Plugin p(so);
        p.load(state);
        p.set(4, 1);
        p.set(5, 1);
        assert(firstSound(p.render(2 * beat)) == -1);
    }
    {
        Plugin p(so);
        p.load(state);
        p.playing = false;
        assert(firstSound(p.render(beat)) == -1);
        p.playing = true;
        assert(firstSound(p.render(beat)) >= 0);
    }
    // With transport stopped the first stroke establishes phase, even halfway through a callback.
    Plugin free(so);
    free.playing = false;
    auto loose = free.render(3 * beat, {{1249, 36, 95}});
    assert(firstSound(loose) == 1249 && firstSound(loose, 1249 + beat) == 1249 + period);
    std::cout << "Split Cycle: 3:4 cycles, quantized overdub, no doubled live stroke, undo, mutes, free "
                 "clock and restart passed.\n";
}
void drumSeat() {
    const auto so = binary("DrumSeat", "drum-seat");
    Plugin p(so);
    p.set(4, 0);
    p.set(2, 0);
    assert(firstSound(p.render(beat, {{37, 36, 110}, {beat / 2, 39, 112}})) == -1);
    assert(firstSound(p.render(beat, {{83, 36, 40}})) == 83);
    Plugin learn(so);
    learn.set(8, 1);
    assert(firstSound(learn.render(4000, {{30, 83, 101}, {70, 83, 114}, {2003, 62, 75}})) == -1);
    learn.preset(0); // A sound change preserves the player's physical assignments.
    auto mapping = learn.save();
    Plugin mapped(so), original(so);
    mapped.load(mapping);
    assert(mapped.render(beat, {{121, 83, 43}, {2000, 62, 99}}) ==
           original.render(beat, {{121, 36, 43}, {2000, 37, 99}}));
    Plugin accents(so);
    accents.preset(1);
    accents.set(4, 0);
    accents.set(2, 0);
    auto high = accents.render(beat, {{48, 36, 50}, {2000, 39, 110}});
    assert(firstSound(high) == 2000);
    Plugin rest(so);
    rest.preset(2);
    rest.set(4, 0);
    auto trade = rest.render(4 * beat, {{0, 45, 115}, {beat / 4, 36, 63}, {beat, 39, 104}});
    const int first = firstSound(trade);
    assert(first >= 3 * beat / 2 && first < 2 * beat);
    // Soloing the answer still lets the insert listen to the original performance.
    assert(energy(trade, first, first + 2000) > 1);
    rest.set(7, 1);
    auto state = rest.save();
    Audio kept;
    {
        Plugin a(so, rate, 127);
        a.load(state);
        kept = a.render(3 * beat, {{51, 39, 95}});
        assert(firstSound(kept) > beat / 2 && energy(kept, beat / 2, 2 * beat) > 1);
    }
    {
        Plugin a(so, rate, 509);
        a.load(state);
        assert(a.render(3 * beat, {{51, 39, 95}}) == kept && a.save() == state);
    }
    Plugin tuned(so);
    tuned.preset(3);
    tuned.set(4, 0);
    tuned.set(2, 0);
    auto line = tuned.render(beat, {{301, 67, 80}, {315, 36, 116}});
    assert(firstSound(line) == 315 && fundamental(line, 510, 3500, rate) == 67);
    auto tunedState = tuned.save();
    Plugin restored(so);
    restored.load(tunedState);
    assert(fundamental(restored.render(beat, {{100, 36, 116}}), 300, 3500, rate) == 67);
    // Check the rack routes pressure and releases identically to the standalone kit.
    std::vector<Event> rolls = {
        {121, 40, 100}, {3033, 40, 119, 0xa0}, {5517, 40, 0, 0x80}, {6601, 45, 95}};
    Plugin kit(binary("GhostWire", "ghost-wire"), 48000, 67), rack(so, 48000, 4096);
    rack.set(1, 0);
    rack.set(2, 0);
    rack.set(4, 1);
    auto drum = kit.render(22000, rolls), desk = rack.render(22000, rolls);
    for (int ch = 0; ch < 2; ch++)
        for (size_t i = 0; i < drum[ch].size(); i++)
            assert(std::abs(desk[ch][i] - std::tanh(.88 * drum[ch][i])) < .000002);
    std::cout << "Drum Seat: ghost-only melody, accent preset, gap-only answers, kept recall, tuning "
                 "and large host blocks passed.\n";
}
int main(int argc, char **argv) {
    if (argc == 2)
        binaries = fs::absolute(argv[1]);
    else if (argc == 4 && std::string(argv[1]) == "--packages" &&
             (std::string(argv[3]) == "arm32" || std::string(argv[3]) == "arm64")) {
        binaries = fs::absolute(argv[2]);
        architecture = argv[3];
    } else {
        std::cerr << "usage: session REPO/plugins | session --packages 'VST2 Plugins' arm32|arm64\n";
        return 2;
    }
    ghostWire();
    rudiments();
    restReply();
    splitCycle();
    drumSeat();
}
