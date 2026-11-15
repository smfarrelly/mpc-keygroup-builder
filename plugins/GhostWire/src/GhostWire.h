// SPDX-License-Identifier: MIT
#pragma once
#include "../../DrumHands/percussion.h"

class GhostWire final : public mpc::Plugin {
  public:
    enum { Tension, Snares, BuzzRate, Damping };

  private:
    enum Stroke { Centre, Rim, Press, Cross };
    struct Stick {
        std::array<percussion::Partial, 3> shell{};
        double wire = 0, wireDecay = 0, noiseLow = 0, wireTone = 0;
        double gain = 1, fade = 1;
        int remaining = 0;
        uint32_t noise = 1;
        void damp(double sr) { fade = std::exp(-1 / (.003 * sr)); }
        double tick() {
            if (!remaining)
                return 0;
            noise = 1664525u * noise + 1013904223u;
            const double white = (noise >> 8) * (2. / 16777216.) - 1;
            noiseLow += wireTone * (white - noiseLow);
            double sound = wire * (white - noiseLow);
            for (auto &mode : shell)
                sound += mode.tick();
            wire *= wireDecay;
            gain *= fade;
            if (--remaining == 0 || gain < .00002)
                remaining = 0;
            return gain * sound;
        }
    };
    struct Hand {
        std::array<Stick, 4> sticks{};
        int cursor = 0, velocity = 0;
        double untilBounce = 0, pressure = .5;
        bool pressed = false;
    };
    std::array<Hand, 2> hands{};
    percussion::Partial kickBody;
    double kickClick = 0, kickDecay = 0, hat = 0, hatDecay = 0, hatLow = 0;
    int kickFrames = 0;
    uint32_t hatNoise = 13;
    bool wasPlaying = false;
    double expectedPpq = 0;
    static mpc::PluginInfo metadata() {
        mpc::PluginInfo p;
        p.name = "Ghost Wire";
        p.vendor = "FG Scratchpad";
        p.isInstrument = true;
        p.numInputs = 0;
        p.uniqueId = MPC_FOURCC('F', 'g', 'G', 'W');
        p.version = 1000;
        return p;
    }
    void stroke(int side, Stroke type, double strength, double sr) {
        auto &hand = hands[side];
        auto &v = hand.sticks[hand.cursor];
        hand.cursor = (hand.cursor + 1) % int(hand.sticks.size());
        const double tuning = (138 + 1.55 * get(Tension)) * (side ? 1.017 : .988);
        const double damping = get(Damping) * .01, wires = get(Snares) * .01;
        const double tail = (.065 + .135 * (1 - damping)) * (type == Cross ? .45 : 1.);
        const double rim = type == Rim ? 1. : type == Cross ? .75 : .15 + .22 * strength;
        const double body = type == Cross ? .22 : type == Press ? .72 : 1.;
        v.shell[0].strike(type == Cross ? 2.8 * tuning : tuning, tail, .53 * strength * body, sr);
        v.shell[1].strike((side ? 1.62 : 1.58) * tuning, tail * .59, .26 * strength * body, sr);
        v.shell[2].strike((type == Cross ? 5.91 : 4.12) * tuning, .013 + .021 * rim,
                          strength * rim * (.3 + .5 * strength), sr);
        v.wire = (type == Cross ? .04 : .68) * strength * wires * (type == Rim ? .72 : 1.);
        v.wireDecay = std::exp(-1 / (sr * (.021 + .067 * (1 - damping) + .023 * strength)));
        v.wireTone = -std::expm1(-6.2831853 * (800 + 1700 * strength) / sr);
        v.remaining = int(sr * tail * 8);
        v.gain = v.fade = 1;
        v.noiseLow = 0;
        v.noise = 1234567u * (side + 1) + uint32_t(strength * 8191) + hand.cursor;
    }
    void silence() {
        for (auto &hand : hands) {
            hand.pressed = false;
            for (auto &stick : hand.sticks)
                stick.remaining = 0;
        }
        kickFrames = 0;
        hat = 0;
    }
    void event(const mpc::MidiEvent &e, double sr) {
        if (e.isAllNotesOff()) {
            reset();
            return;
        }
        if (e.isAftertouch()) {
            for (auto &hand : hands)
                hand.pressure = e.data[1] / 127.;
            return;
        }
        if (e.status() == 0xA0 && (e.note() == 40 || e.note() == 41)) {
            hands[e.note() - 40].pressure = e.data[2] / 127.;
            return;
        }
        const int note = e.note();
        if (e.isNoteOff()) {
            if (note == 40 || note == 41)
                hands[note - 40].pressed = false;
            return;
        }
        if (!e.isNoteOn() || note < 36 || note > 47)
            return;
        const int side = (note - 36) % 2;
        auto &hand = hands[side];
        const double strength = e.velocity() / 127.;
        if (note < 44) {
            const auto kind = Stroke((note - 36) / 2);
            hand.pressed = kind == Press;
            hand.velocity = e.velocity();
            hand.untilBounce = 1.;
            stroke(side, kind, strength, sr);
        } else if (note == 44) {
            for (auto &h : hands) {
                h.pressed = false;
                for (auto &s : h.sticks)
                    s.damp(sr);
            }
        } else if (note == 45) {
            kickBody.strike(52, .14, strength * .95, sr);
            kickFrames = int(sr * .95);
            kickClick = .7 * strength;
            kickDecay = std::exp(-1 / (sr * .0018));
        } else {
            hat = .40 * strength;
            hatDecay = std::exp(-1 / (sr * (note == 46 ? .027 : .155)));
            hatLow = 0;
        }
    }

  public:
    GhostWire() : Plugin(metadata()) {
        addParam(mpc::floatParam("tension", "Tension", 0, 100, 44, "%", 0));
        addParam(mpc::floatParam("snares", "Snares", 0, 100, 72, "%", 0));
        addParam(mpc::floatParam("buzz_rate", "Buzz Rate", 8, 36, 19, "Hz", 1));
        addParam(mpc::floatParam("damping", "Damping", 0, 100, 48, "%", 0));
        addProgram("Studio Snare", {44, 72, 19, 48});
        addProgram("Tight Parade", {81, 84, 27, 72});
        addProgram("Loose Wires", {22, 95, 14, 20});
        addProgram("Dry Cross Stick", {63, 12, 18, 84});
    }
    void reset() override {
        hands = {};
        silence();
        kickBody = {};
        kickClick = hatLow = 0;
        hatNoise = 13;
        wasPlaying = false;
        expectedPpq = 0;
    }
    void process(mpc::ProcessContext &c) override {
        const bool playing = c.transport.valid && c.transport.playing;
        if (wasPlaying &&
            (!playing || (c.transport.ppqValid && std::abs(c.transport.ppqPos - expectedPpq) > .025))) {
            for (auto &hand : hands)
                hand.pressed = false;
        }
        expectedPpq = c.transport.ppqPos + c.numFrames * percussion::tempo(c) / (60 * c.sampleRate);
        wasPlaying = playing;
        int next = 0;
        const double rate = get(BuzzRate), sr = c.sampleRate;
        const double hatFilter = -std::expm1(-6.2831853 * 4100 / sr);
        for (int i = 0; i < c.numFrames; i++) {
            while (next < c.numMidiEvents && c.midi[next].sampleOffset <= i)
                event(c.midi[next++], sr);
            double sides[2]{};
            for (int side = 0; side < 2; side++) {
                auto &hand = hands[side];
                if (hand.pressed) {
                    hand.untilBounce -= rate * (.68 + .64 * hand.pressure) / sr;
                    if (hand.untilBounce <= 0) {
                        hand.untilBounce += 1;
                        stroke(side, Press, hand.velocity / 127. * (.26 + .48 * hand.pressure), sr);
                    }
                }
                for (auto &stick : hand.sticks)
                    sides[side] += stick.tick();
            }
            double feet = 0;
            if (kickFrames > 0) {
                --kickFrames;
                feet = kickBody.tick() + kickClick;
                kickClick *= kickDecay;
            }
            if (hat > .00001) {
                hatNoise = 1664525u * hatNoise + 1013904223u;
                double noise = (hatNoise >> 8) * (2. / 16777216.) - 1;
                hatLow += hatFilter * (noise - hatLow);
                feet += hat * (noise - hatLow);
                hat *= hatDecay;
            }
            c.outputs[0][i] = std::tanh(.70 * (feet + sides[0] + .73 * sides[1]));
            c.outputs[1][i] = std::tanh(.70 * (feet + .73 * sides[0] + sides[1]));
        }
    }
};
