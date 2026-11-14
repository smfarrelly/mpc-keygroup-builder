// SPDX-License-Identifier: MIT
#include "mpc_plugin.h"
#include <array>
#include <cmath>
#include <vector>

class PocketLayers final : public mpc::Plugin {
    enum Kind { Shell, ClosedHat, OpenHat, Other };
    struct Layer {
        int high = 127;
        std::vector<float> pcm;
    };
    struct Pad {
        int note = -1, kind = Other, family = 0, group = 0;
        std::vector<Layer> layers;
    };
    struct Voice {
        const Layer *layer = nullptr;
        int pad = -1;
        double pos = 0;
        float gain = 0, decay = 1;
    };

  public:
    enum { Accent, Ring, Opening, Mapping };
    PocketLayers() : Plugin(metadata()) {
        addParam(mpc::intParam("accent", "Accent Point", 48, 120, 96, "vel"));
        addParam(mpc::floatParam("ring", "Shell Ring", 0, 100, 72, "%", 0));
        addParam(mpc::floatParam("opening", "Hat Opening", 0, 100, 56, "%", 0));
        addParam(mpc::choiceParam("mapping", "Pad Map", {"Bank A from 36", "Source XPM"}, 0));
    }
    void prepare(double rate, int) override {
        sampleRate = rate;
        step = 44100. / rate;
        pads = {};
        std::vector<uint8_t> data;
        // Resolve per instance. A static std::string destructor can outlive a dlclosed Zig-built
        // library.
        const auto folder = mpc::detail::computePluginFolder();
        if (folder.empty() || !mpc::readFile(folder + "/Content/kit.bin", data) || !load(data))
            factoryKit();
        reset();
    }
    void reset() override {
        voices = {};
        hits = {};
        next = 0;
    }
    void process(mpc::ProcessContext &c) override {
        int event = 0;
        for (int i = 0; i < c.numFrames; ++i) {
            while (event < c.numMidiEvents && c.midi[event].sampleOffset <= i) {
                const auto &e = c.midi[event++];
                if (e.isNoteOn())
                    strike(e.note(), e.velocity());
                else if (e.isAllNotesOff())
                    voices = {};
            }
            float mix = 0;
            for (auto &v : voices)
                if (v.layer) {
                    const auto &pcm = v.layer->pcm;
                    const size_t pos = static_cast<size_t>(v.pos);
                    if (pos >= pcm.size() || v.gain < .00008f) {
                        v.layer = nullptr;
                        continue;
                    }
                    const float a = pcm[pos], b = pos + 1 < pcm.size() ? pcm[pos + 1] : 0.f;
                    mix += (a + (b - a) * static_cast<float>(v.pos - pos)) * v.gain;
                    v.pos += step;
                    v.gain *= v.decay;
                }
            c.outputs[0][i] = c.outputs[1][i] = mix * .60f;
        }
    }

  private:
    bool load(const std::vector<uint8_t> &bytes) {
        if (bytes.size() < 5 || std::memcmp(bytes.data(), "FGL1", 4) != 0)
            return false;
        size_t p = 5;
        int count = bytes[4];
        if (count < 1 || count > 16)
            return false;
        for (int i = 0; i < count; ++i) {
            if (bytes.size() - p < 6)
                return false;
            int slot = bytes[p++];
            if (slot > 15 || pads[slot].note >= 0)
                return false;
            Pad &pad = pads[slot];
            pad.note = bytes[p++];
            pad.kind = bytes[p++];
            pad.family = bytes[p++];
            pad.group = bytes[p++];
            int layers = bytes[p++];
            if (layers < 1 || layers > 8 || pad.note > 127 || pad.kind > Other)
                return false;
            int previous = 0;
            for (int j = 0; j < layers; ++j) {
                if (bytes.size() - p < 5)
                    return false;
                Layer l;
                l.high = bytes[p++];
                if (l.high <= previous || l.high > 127)
                    return false;
                previous = l.high;
                uint32_t n = 0;
                for (int k = 0; k < 4; ++k)
                    n |= uint32_t(bytes[p++]) << (8 * k);
                if (!n || n > (bytes.size() - p) / 2)
                    return false;
                l.pcm.resize(n);
                for (float &value : l.pcm) {
                    int raw = bytes[p] + 256 * bytes[p + 1];
                    p += 2;
                    value = (raw >= 32768 ? raw - 65536 : raw) / 32768.f;
                }
                pad.layers.push_back(std::move(l));
            }
            if (previous != 127)
                return false;
        }
        return p == bytes.size();
    }
    // Self-contained practice kit for a fresh build without a personal sample bank.
    void factoryKit() {
        pads = {};
        constexpr int families[] = {1, 1, 2, 2, 3, 3, 4, 4, 5, 6, 5, 6, 7, 7, 8, 9};
        constexpr int map[] = {37, 36, 42, 82, 40, 38, 46, 44, 48, 47, 45, 43, 49, 55, 51, 53};
        for (int i = 0; i < 16; ++i) {
            Pad &pad = pads[i];
            pad.note = map[i];
            pad.family = families[i];
            pad.kind = pad.family == 5   ? ClosedHat
                       : pad.family == 6 ? OpenHat
                                         : (i < 4 || pad.family == 7 ? Shell : Other);
            pad.group = pad.kind == ClosedHat || pad.kind == OpenHat ? 1 : 0;
            for (int layer = 0; layer < 2; ++layer) {
                Layer sound;
                sound.high = layer == 0 ? 95 : 127;
                const float hz = pad.family == 1 ? 53 : pad.family == 7 ? 104 : 176;
                double phase = 0, prev = 0;
                uint32_t noise = 17 + i + layer * 42;
                const double tail = pad.kind == ClosedHat ? .05
                                    : pad.kind == OpenHat ? .26
                                    : pad.family == 1     ? .19
                                                          : .095;
                const int frames = static_cast<int>(44100 * tail * 6);
                for (int f = 0; f < frames; ++f) {
                    double t = f / 44100.;
                    noise = 1664525u * noise + 1013904223u;
                    double n = noise / 2147483648. - 1;
                    phase += 6.2831853 * (hz + i * 2 + 100 * std::exp(-t * 48)) / 44100.;
                    double mix = pad.family == 1     ? .9 * std::sin(phase)
                                 : pad.kind == Shell ? .44 * std::sin(phase) + .35 * n
                                                     : .47 * (n - prev);
                    sound.pcm.push_back(
                        static_cast<float>(mix * std::exp(-t / (tail * (1 + .3 * layer)))));
                    prev = n;
                }
                pad.layers.push_back(std::move(sound));
            }
        }
    }
    void strike(int note, int vel) {
        int slot = note - 36;
        if (getInt(Mapping) == 1) {
            slot = 0;
            while (slot < 16 && pads[slot].note != note)
                ++slot;
        }
        if (slot < 0 || slot >= 16 || pads[slot].layers.empty())
            return;
        const Pad &source = pads[slot];
        int siblings[16], count = 0;
        for (int i = 0; i < 16; ++i) {
            int candidate = (slot + i) % 16;
            if (!pads[candidate].layers.empty() && pads[candidate].family == source.family)
                siblings[count++] = candidate;
        }
        const Pad &variation = pads[siblings[hits[slot]++ % count]];
        const int point = getInt(Accent);
        const int threshold =
            variation.layers.size() > 1 ? variation.layers[variation.layers.size() - 2].high + 1 : 96;
        const int mapped = vel < point ? 1 + (vel - 1) * (threshold - 1) / (point - 1)
                                       : threshold + (vel - point) * (127 - threshold) / (127 - point);
        const Layer *layer = &variation.layers.back();
        for (const auto &l : variation.layers)
            if (mapped <= l.high) {
                layer = &l;
                break;
            }
        for (auto &v : voices)
            if (v.layer && (v.pad == slot || (source.group && pads[v.pad].group == source.group)))
                v.decay = std::min(v.decay, static_cast<float>(std::exp(-1 / (sampleRate * .001))));
        const double seconds = source.kind == ClosedHat ? .012 + .16 * get(Opening) / 100
                               : source.kind == OpenHat ? .04 + 1.35 * get(Opening) / 100
                               : source.kind == Shell   ? .04 + 1.35 * get(Ring) / 100
                                                        : 2.5;
        voices[next] = {layer, slot, 0, vel / 127.f,
                        static_cast<float>(std::exp(-1 / (sampleRate * seconds)))};
        next = (next + 1) % voices.size();
    }
    static mpc::PluginInfo metadata() {
        mpc::PluginInfo p;
        p.name = "Pocket Layers";
        p.vendor = "FG Scratchpad";
        p.uniqueId = MPC_FOURCC('F', 'g', 'P', 'L');
        p.version = 1000;
        p.isInstrument = true;
        p.numInputs = 0;
        return p;
    }
    std::array<Pad, 16> pads{};
    std::array<uint32_t, 16> hits{};
    std::array<Voice, 32> voices{};
    size_t next = 0;
    double sampleRate = 44100, step = 1;
};
MPC_PLUGIN_ENTRY(PocketLayers)
