// SPDX-License-Identifier: MIT
#pragma once
#include "../../DrumHands/percussion.h"

class RudimentKeys final : public mpc::Plugin {
  public:
    enum { Root, Scale, Accent, Tail, Stick, Tone, Width };

  private:
    struct Ladder {
        std::array<int, 7> intervals;
        int length, fifth;
    };
    static constexpr Ladder scales[] = {{{0, 3, 5, 7, 10}, 5, 3},
                                        {{0, 2, 4, 7, 9}, 5, 3},
                                        {{0, 2, 3, 5, 7, 9, 10}, 7, 4},
                                        {{0, 2, 3, 5, 7, 8, 10}, 7, 4}};
    struct Grace {
        int frames = 0, note = 0, velocity = 0, side = 0;
    };
    std::array<percussion::Mallet, 12> voices{};
    std::array<Grace, 2> flams{};
    int nextVoice = 0, degree = 0, direction = 1, lastHand = -1, lastDegree = 0;
    bool doubleStroke = false, wasPlaying = false;
    double expected = 0;
    static mpc::PluginInfo metadata() {
        mpc::PluginInfo p;
        p.name = "Rudiment Keys";
        p.vendor = "FG Scratchpad";
        p.isInstrument = true;
        p.numInputs = 0;
        p.uniqueId = MPC_FOURCC('F', 'g', 'R', 'u');
        p.version = 1000;
        return p;
    }
    void home() {
        degree = lastDegree = 0;
        direction = 1;
        lastHand = -1;
        doubleStroke = false;
    }
    static int semitones(int step, const Ladder &scale) {
        const int octave = step < 0 ? -1 : step / scale.length;
        const int within = (step % scale.length + scale.length) % scale.length;
        return scale.intervals[within] + 12 * octave;
    }
    int choose(int side, int velocity, const Ladder &scale) {
        if (velocity < 48)
            return lastDegree;
        if (velocity >= getInt(Accent)) {
            degree = side ? scale.fifth : 0;
            direction = side ? -1 : 1;
            doubleStroke = false;
            lastDegree = degree;
        } else if (lastHand == side) {
            doubleStroke = !doubleStroke;
            lastDegree = degree + (doubleStroke ? (side ? 1 : -1) : 0);
        } else {
            if (lastHand >= 0) {
                if (degree == scale.length)
                    direction = -1;
                if (degree == 0)
                    direction = 1;
                degree += direction;
            }
            lastDegree = degree;
            doubleStroke = false;
        }
        lastHand = side;
        return lastDegree;
    }
    void sound(int note, int velocity, int side, double sr, double tailFactor = 1) {
        auto &v = voices[nextVoice];
        nextVoice = (nextVoice + 1) % int(voices.size());
        const double amp = velocity / 127.;
        v.strike(note, .48 * std::pow(amp, 1.25), .001 * get(Tail) * tailFactor,
                 (.18 + .82 * amp) * .01 * get(Tone), side * .0048 * get(Width), sr);
    }
    void event(const mpc::MidiEvent &e, double sr) {
        if (e.isAllNotesOff()) {
            click[0] = click[1] = 0;
            voices = {};
            flams = {};
            home();
            return;
        }
        if (!e.isNoteOn())
            return;
        const int key = e.note(), vel = e.velocity();
        if (key >= 48 && key <= 84) {
            set(Root, key);
            home();
            return;
        }
        if (key < 36 || key > 44)
            return;
        if (key == 44) {
            home();
            flams = {};
            return;
        }
        if (key == 43) {
            for (auto &v : voices)
                v.damp(sr);
            flams = {};
            return;
        }
        if (key == 42) {
            sound(getInt(Root) - 12, vel, 0, sr);
            return;
        }
        const int hand = (key - 36) % 2, side = hand ? 1 : -1, gesture = (key - 36) / 2;
        const Ladder &scale = scales[getInt(Scale)];
        // Changing scale mid-phrase can shorten the ladder.
        degree = std::min(degree, scale.length);
        lastDegree = std::clamp(lastDegree, -1, scale.length + 1);
        const int step = choose(hand, vel, scale);
        const int note = getInt(Root) + semitones(step, scale);
        flams[hand] = {};
        if (vel < 48) {
            sound(note, vel, side, sr, .15);
        } else if (gesture == 2) {
            sound(note, std::max(1, vel / 2), side, sr, .19);
            flams[hand] = {int(sr * .022) + 1, note, vel, side};
        } else {
            sound(note, vel, side, sr);
            if (gesture == 1)
                sound(getInt(Root) + semitones(step + 2, scale), vel * 2 / 3, side, sr, .78);
        }
        click[hand] = .17 * vel / 127. * get(Stick) * .01;
    }
    double click[2]{};

  public:
    RudimentKeys() : Plugin(metadata()) {
        addParam(mpc::intParam("root", "Root", 30, 84, 50, "MIDI"));
        addParam(mpc::choiceParam("scale", "Scale", {"Minor pent", "Major pent", "Dorian", "Minor"}, 0));
        addParam(mpc::intParam("accent", "Accent Point", 64, 126, 104));
        addParam(mpc::logParam("tail", "Tail", 50, 1100, 280, "ms", 0));
        addParam(mpc::floatParam("stick", "Stick", 0, 100, 44, "%", 0));
        addParam(mpc::floatParam("tone", "Tone", 0, 100, 72, "%", 0));
        addParam(mpc::floatParam("width", "Width", 0, 100, 52, "%", 0));
        addProgram("D Minor Wood", {50, 0, 104, 280, 44, 72, 52});
        addProgram("G Major Bells", {55, 1, 110, 640, 21, 90, 72});
        addProgram("Dorian Bounce", {45, 2, 95, 175, 70, 54, 48});
        addProgram("Low Minor Walk", {38, 3, 102, 345, 50, 40, 35});
    }
    void reset() override {
        voices = {};
        flams = {};
        nextVoice = 0;
        home();
        click[0] = click[1] = 0;
        wasPlaying = false;
        expected = 0;
    }
    void process(mpc::ProcessContext &c) override {
        const bool playing = c.transport.valid && c.transport.playing;
        if (playing &&
            (!wasPlaying || (c.transport.ppqValid && std::abs(c.transport.ppqPos - expected) > .025))) {
            home();
            flams = {};
        }
        wasPlaying = playing;
        expected = c.transport.ppqPos + c.numFrames * percussion::tempo(c) / (60 * c.sampleRate);
        const double clickDecay = std::exp(-1 / (c.sampleRate * .00065));
        int next = 0;
        const double narrow = .0048 * get(Width);
        for (int i = 0; i < c.numFrames; i++) {
            while (next < c.numMidiEvents && c.midi[next].sampleOffset <= i)
                event(c.midi[next++], c.sampleRate);
            for (auto &grace : flams)
                if (grace.frames > 0 && !--grace.frames)
                    sound(grace.note, grace.velocity, grace.side, c.sampleRate);
            double left = 0, right = 0;
            for (auto &v : voices)
                v.add(left, right);
            left += click[0] * (1 + narrow) + click[1] * (1 - narrow);
            right += click[0] * (1 - narrow) + click[1] * (1 + narrow);
            for (double &pulse : click) {
                pulse *= clickDecay;
                if (pulse < .000001)
                    pulse = 0;
            }
            c.outputs[0][i] = std::tanh(left);
            c.outputs[1][i] = std::tanh(right);
        }
    }
};
