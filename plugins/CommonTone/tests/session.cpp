// SPDX-License-Identifier: MIT
#include "../../DrumHands/tests/host.h"
using namespace testhost;
constexpr int rate = 32000, beat = rate / 2;
double amplitude(const Audio &a, int note) {
    const double angle = 6.283185307179586 * 440 * std::pow(2., (note - 69) / 12.) / rate;
    double re = 0, im = 0;
    for (int i = 0; i < beat; i++) {
        double w = .5 - .5 * std::cos(6.283185307179586 * i / (beat - 1));
        re += a[0][i + beat] * w * std::cos(i * angle);
        im += a[0][i + beat] * w * std::sin(i * angle);
    }
    return std::hypot(re, im) / beat;
}
int main(int argc, char **argv) {
    if (argc != 2)
        return 2;
    const char *so = argv[1];
    const int expected[][4] = {{55, 58, 65, 67}, {51, 58, 62, 67}, {53, 57, 63, 67}};
    for (int shape = 0; shape < 3; shape++) {
        Plugin p(so);
        p.set(0, 0);
        auto bed = p.render(2 * beat, {{0, 67, 90}, {0, 36 + shape, 100}});
        for (int key : expected[shape])
            assert(amplitude(bed, key) > .012);
        assert(amplitude(bed, 61) < .003);
    }
    Bytes saved;
    {
        Plugin p(so);
        p.render(beat, {{0, 67, 90},
                        {3, 36, 100},
                        {12, 42, 100},
                        {20, 36, 0, 128},
                        {30, 64, 80},
                        {50, 38, 100},
                        {60, 43, 100}});
        saved = p.save();
        assert(saved[saved.size() - 4] == 67 && saved[saved.size() - 2] == 64 && saved.back() == 1);
    }
    auto recall = [&](int block) {
        Plugin p(so, rate, block);
        p.load(saved);
        assert(firstSound(p.render(3000)) == -1);
        return p.render(2 * beat, {{100, 40, 100}, {1901, 39, 78}, {4013, 41, 100}, {6033, 39, 41}});
    };
    assert(recall(127) == recall(257));
    Plugin p(so);
    p.load(saved);
    p.set(0, 0);
    p.set(1, 0);
    auto stab = p.render(beat, {{0, 41, 100}, {917, 39, 95}});
    assert(firstSound(stab) == 917 && energy(stab, 917, beat) > 1);
    auto bad = saved;
    bad.back() = 12;
    p.load(bad);
    assert(p.save().back() == 1);
    // Shared pitches remain phase-continuous when auditioning the same chord over its pin.
    auto compare = [&](bool audition) {
        Plugin v(so);
        v.load(saved);
        std::vector<Event> hits = {{0, 40, 100}};
        if (audition) {
            hits.push_back({1001, 36, 99});
            hits.push_back({2903, 36, 0, 128});
        }
        return v.render(beat, hits);
    };
    assert(compare(true) == compare(false));
    Plugin lead(so), pedal(so);
    auto dry = lead.render(beat, {{0, 67, 90}, {200, 67, 0, 128}});
    auto held = pedal.render(beat, {{0, 64, 127, 176}, {0, 67, 90}, {200, 67, 0, 128}});
    assert(energy(held, 5000, beat) > 1 && energy(dry, 5000, beat) < .001);
    assert(firstSound(pedal.render(1000, {{0, 123, 0, 176}})) == -1);
    std::cout << "All twelve chord tones, A/B recall, common-tone continuity, rhythmic stabs, sustain "
                 "and panic passed.\n";
}
