// Offline host for the SDK Simple Synth. Feed it start/end frame, note, velocity
// rows on stdin. Each row produces a note-on and note-off at exact sample offsets.
#include "SimpleSynth.cpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <string>
#include <vector>

struct NoteEdge {
    int frame;
    int note;
    int velocity; // zero releases the note
};

int main(int argc, char** argv) {
    if (argc != 4 && argc != 5) return 2;
    const std::string preset = argv[1];
    const int frames = std::stoi(argv[2]);
    const double bpm = std::stod(argv[3]);
    if (frames < 1 || !(bpm >= 20 && bpm <= 300)) return 2;
    SimpleSynth synth;
    int program = 0;
    while (program < synth.numPrograms() && preset != synth.programName(program)) ++program;
    if (program == synth.numPrograms()) {
        std::cerr << "Unknown Simple Synth preset: " << preset << '\n';
        return 2;
    }
    struct Move { int frame, index, value; };
    std::vector<Move> moves;
    if (argc == 5) {
        std::ifstream input(argv[4]);
        if (!input) return 2;
        Move move{};
        std::string name;
        while (input >> move.frame) {
            if (!(input >> move.index >> move.value >> std::quoted(name)) ||
                move.frame < 0 || move.frame >= frames || move.index < 0 || move.index >= synth.numParams() ||
                move.value < 0 || move.value > 127 || synth.param(move.index).name != name ||
                (!moves.empty() && move.frame < moves.back().frame)) {
                std::cerr << "Invalid gesture or parameter mismatch at frame " << move.frame << '\n';
                return 2;
            }
            moves.push_back(move);
        }
        if (!input.eof() || moves.empty()) return 2;
    }
    std::vector<NoteEdge> edges;
    int start, end, note, velocity;
    while (std::cin >> start) {
        if (!(std::cin >> end >> note >> velocity) || start < 0 || start >= end || end > frames ||
            note < 0 || note > 127 || velocity < 1 || velocity > 127) return 2;
        edges.push_back({start, note, velocity});
        edges.push_back({end, note, 0});
    }
    if (!std::cin.eof() || edges.empty()) return 2;
    std::stable_sort(edges.begin(), edges.end(), [](const NoteEdge& a, const NoteEdge& b) {
        if (a.frame != b.frame) return a.frame < b.frame;
        return (a.velocity == 0) > (b.velocity == 0);
    });
    constexpr int rate = 44100, block = 128;
    synth.setProgram(program);
    synth.prepare(rate, block);
    synth.reset();
    size_t next = 0, nextMove = 0;
    for (int pos = 0; pos < frames;) {
        while (nextMove < moves.size() && moves[nextMove].frame == pos) {
            const auto& move = moves[nextMove++];
            synth.setNormalised(move.index, move.value / 127.0f);
        }
        int count = std::min(block, frames - pos);
        if (nextMove < moves.size()) count = std::min(count, moves[nextMove].frame - pos);
        std::vector<mpc::MidiEvent> events;
        while (next < edges.size() && edges[next].frame < pos + count) {
            const auto& event = edges[next++];
            const int offset = event.frame - pos;
            events.push_back(event.velocity ? mpc::MidiEvent::noteOn(0, event.note, event.velocity, offset)
                                            : mpc::MidiEvent::noteOff(0, event.note, offset));
        }
        std::array<float, block> left{}, right{};
        float* stereo[] = {left.data(), right.data()};
        mpc::ProcessContext ctx{};
        ctx.sampleRate = rate;
        ctx.numFrames = count;
        ctx.numOutputs = 2;
        ctx.outputs = stereo;
        ctx.midi = events.data();
        ctx.numMidiEvents = static_cast<int>(events.size());
        ctx.transport.valid = ctx.transport.playing = ctx.transport.tempoValid = ctx.transport.ppqValid = true;
        ctx.transport.bpm = bpm;
        ctx.transport.samplePos = pos;
        ctx.transport.ppqPos = pos * bpm / (60.0 * rate);
        ctx.transport.barStartPpq = 4.0 * std::floor(ctx.transport.ppqPos / 4.0);
        synth.process(ctx);
        // Simple Synth mirrors its mono mix to both outputs. Keep one channel.
        std::array<unsigned char, block * 2> pcm{};
        for (int i = 0; i < count; ++i) {
            if (!std::isfinite(left[i]) || !std::isfinite(right[i]) || left[i] != right[i]) {
                std::cerr << "Expected finite dual-mono Simple Synth output\n";
                return 1;
            }
            const uint16_t sample = static_cast<uint16_t>(std::lround(std::clamp(left[i], -1.f, 1.f) * 32767.f));
            pcm[2*i] = static_cast<unsigned char>(sample);
            pcm[2*i+1] = static_cast<unsigned char>(sample >> 8);
        }
        if (std::fwrite(pcm.data(), 2, count, stdout) != static_cast<size_t>(count)) return 1;
        pos += count;
    }
    return std::fflush(stdout) == 0 ? 0 : 1;
}
