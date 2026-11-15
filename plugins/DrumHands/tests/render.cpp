// SPDX-License-Identifier: MIT
// Render the rehearsal MIDI score with the built plugins, including the optional stereo insert.
#include "host.h"
#include <fstream>
using namespace testhost;
void pcm(const char *path, const Audio &a) {
    std::ofstream out(path, std::ios::binary);
    double peak = 0;
    for (size_t i = 0; i < a[0].size(); i++) {
        for (const auto &channel : a) {
            double v = .85 * channel[i];
            peak = std::max(peak, std::abs(v));
            if (std::abs(v) > 1)
                throw std::runtime_error("rehearsal clipped");
            const auto sample = uint16_t(int16_t(std::lround(32767 * v)));
            out.put(char(sample & 255));
            out.put(char(sample >> 8));
        }
    }
    out.close();
    if (!out || peak < .02)
        throw std::runtime_error("empty or unwritable rehearsal");
}
int main(int argc, char **argv) {
    if (argc != 6 && argc != 8) {
        std::cerr << "render plugin.so frames bpm score.tsv stereo.pcm [insert.so dry.pcm]\n";
        return 2;
    }
    const int frames = std::stoi(argv[2]);
    if (frames <= 0 || frames > 8 * 60 * 44100)
        return 2;
    std::ifstream in(argv[4]);
    if (!in)
        return 2;
    std::vector<Event> events;
    Event e{};
    while (in >> e.frame >> e.key >> e.value >> e.status)
        events.push_back(e);
    if (!in.eof())
        return 2;
    Plugin instrument(argv[1], 44100);
    instrument.bpm = std::stod(argv[3]);
    Audio audio = instrument.render(frames, events);
    if (argc == 8) {
        pcm(argv[7], audio);
        Plugin insert(argv[6], 44100);
        insert.bpm = instrument.bpm;
        audio = insert.render(frames, {}, &audio);
    }
    pcm(argv[5], audio);
}
