// SPDX-License-Identifier: MIT
#include "mpc_plugin.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <vector>

namespace relay {
struct Slice {
  int role, start, end;
  std::vector<int16_t> pcm;
};
struct Break {
  int rate = 0;
  std::vector<Slice> slices;
};
using Pair = std::array<Break, 2>;

bool readPair(Pair &pair) {
  auto path = mpc::detail::computePluginFolder() + "/Content/pair.brk";
  auto *file = std::fopen(path.c_str(), "rb");
  if (!file)
    return false;
  std::array<uint8_t, 4> magic{};
  bool valid = std::fread(magic.data(), 1, 4, file) == 4 &&
               magic == std::array<uint8_t, 4>{'B', 'R', 'K', '1'};
  size_t consumed = 4;
  auto number = [&](unsigned size) {
    uint8_t buf[4] = {};
    if (std::fread(buf, 1, size, file) != size)
      valid = false;
    consumed += size;
    uint32_t n = 0;
    for (unsigned i = 0; i < size; ++i)
      n |= uint32_t(buf[i]) << (8 * i);
    return n;
  };
  Pair temp;
  for (auto &bank : temp) {
    if (!valid)
      break;
    bank.rate = int(number(4));
    const unsigned count = number(1);
    int roles = 0, previous = -1;
    valid = valid && bank.rate >= 8000 && bank.rate <= 96000 && count >= 4 &&
            count <= 64;
    for (unsigned i = 0; valid && i < count; i++) {
      Slice s{};
      s.role = number(1);
      s.start = number(2);
      s.end = number(2);
      const unsigned frames = number(4);
      valid = valid && s.role <= 3 && s.start >= previous && s.end > s.start &&
              frames >= 8 && frames <= unsigned(2 * bank.rate) &&
              consumed + 4ull * frames <= 16 * 1024 * 1024;
      if (!valid)
        break;
      previous = s.start;
      roles |= 1 << s.role;
      s.pcm.resize(2 * frames);
      // Both MPC CPU targets and the SDK desktop targets are little endian.
      valid = std::fread(s.pcm.data(), 4, frames, file) == frames;
      consumed += 4 * frames;
      bank.slices.push_back(std::move(s));
    }
    valid = valid && roles == 15;
  }
  valid = valid && std::fgetc(file) == EOF && !std::ferror(file);
  std::fclose(file);
  if (valid)
    pair = std::move(temp);
  return valid;
}

// Original tiny synthesized breaks keep all four pads playable without user
// content.
void factoryPair(Pair &pair) {
  for (int b = 0; b < 2; b++) {
    auto &bank = pair[b];
    bank.rate = 24000;
    uint32_t rng = 13 + b;
    for (int i = 0; i < 8; i++) {
      const int role = std::array<int, 8>{0, 2, 1, 2, 0, 1, 2, 3}[i];
      Slice s{role, i * 8192, std::min(65535, (i + 1) * 8192), {}};
      double prev = 0;
      for (int j = 0; j < 6000; j++) {
        const double t = j / 24000.;
        rng = rng * 1664525u + 1013904223u;
        const double noise = double(rng) / 2147483648. - 1;
        const double hp = (noise - prev) * .5;
        prev = noise;
        const double f = (b ? 1.4 : 1.) * (1 + .008 * i);
        double x = 0;
        if (role == 0)
          x = .8 * std::exp(-18 * t) *
              std::sin(6.28318 * f * (47 * t + .95 * (1 - std::exp(-70 * t))));
        if (role == 1)
          x = (.38 * noise + .35 * std::sin(1120 * f * t)) * std::exp(-23 * t);
        if (role == 2)
          x = .42 * hp * std::exp(-60 * t);
        if (role == 3)
          x = .54 * hp * std::exp(-30 * std::fmod(t, b ? .09 : .12));
        const auto v = int16_t(x * 30000);
        s.pcm.push_back(v);
        s.pcm.push_back(v);
      }
      bank.slices.push_back(std::move(s));
    }
  }
}
} // namespace relay

class BreakRelay final : public mpc::Plugin {
  relay::Pair pair;
  struct Voice {
    const relay::Slice *slice = nullptr;
    double pos = 0, step = 1, amp = 0;
    int elapsed = 0;
  } now, old;
  int fade = 0, fadeLength = 1, phase = 0, activeSeed = -1;
  uint32_t random = 1;
  std::array<int, 128> held{};
  int keys = 0;
  bool wasPlaying = false, borrow = false, away = false;
  static mpc::PluginInfo meta() {
    mpc::PluginInfo p;
    p.name = "Break Relay";
    p.vendor = "FG Scratchpad";
    p.uniqueId = MPC_FOURCC('F', 'g', 'B', 'r');
    p.isInstrument = true;
    p.numInputs = 0;
    p.version = 1000;
    return p;
  }
  void home() {
    phase = 0;
    activeSeed = getInt(1);
    random = uint32_t(activeSeed) * 2654435761u;
  }
  void tail(double sr) {
    if (now.slice) {
      old = now;
      now = {};
      fade = fadeLength = std::max(1, int(.003 * sr));
    }
  }
  void strike(int role, int velocity, double sr) {
    if (activeSeed != getInt(1))
      home();
    random = random * 1664525u + 1013904223u;
    const double wander = away ? 100. : borrow ? 50. : get(0);
    const int bank = (random >> 8) < wander * 16777216. / 100. ? 1 : 0;
    auto &source = pair[bank];
    const relay::Slice *chosen = nullptr;
    for (const auto &s : source.slices) {
      if (s.role != role)
        continue;
      if (!chosen)
        chosen = &s;
      if (s.start >= phase) {
        chosen = &s;
        break;
      }
    }
    phase = chosen->end == 65535 ? 0 : chosen->end;
    tail(sr);
    int transpose = getInt(2) + (keys ? held[keys - 1] - 60 : 0);
    now = {chosen, 0,
           source.rate / sr * std::exp2(std::clamp(transpose, -36, 36) / 12.),
           velocity / 127., 0};
  }
  void event(const mpc::MidiEvent &e, double sr) {
    if (e.isAllNotesOff()) {
      tail(sr);
      keys = 0;
      borrow = away = false;
      home();
      return;
    }
    const int k = e.note();
    if (k > 127)
      return;
    if ((k == 41 || k == 42) && (e.isNoteOn() || e.isNoteOff())) {
      (k == 41 ? borrow : away) = e.isNoteOn();
      return;
    }
    if (k >= 48 && (e.isNoteOn() || e.isNoteOff())) {
      auto end = held.begin() + keys;
      auto it = std::find(held.begin(), end, k);
      if (it != end) {
        std::move(it + 1, end, it);
        --keys;
      }
      if (e.isNoteOn())
        held[keys++] = k;
    } else if (e.isNoteOn() && k == 40) {
      tail(sr);
      home();
    } else if (e.isNoteOn() && k >= 36 && k <= 39)
      strike(k - 36, e.velocity(), sr);
  }
  static void render(Voice &v, double mix, double sr, double &l, double &r) {
    if (!v.slice)
      return;
    auto &pcm = v.slice->pcm;
    const int frames = int(pcm.size() / 2), k = int(v.pos);
    if (k >= frames - 1) {
      v.slice = nullptr;
      return;
    }
    const double frac = v.pos - k;
    const double envelope =
        std::min({1., (v.elapsed + 1) / (.0004 * sr),
                  (frames - 1 - v.pos) / (v.step * .003 * sr)});
    const double amp = v.amp * mix * envelope / 32768.;
    l += amp * (pcm[2 * k] + frac * (pcm[2 * k + 2] - pcm[2 * k]));
    r += amp * (pcm[2 * k + 1] + frac * (pcm[2 * k + 3] - pcm[2 * k + 1]));
    v.pos += v.step;
    ++v.elapsed;
  }

public:
  BreakRelay() : Plugin(meta()) {
    addParam(mpc::floatParam("wander", "Wander", 0, 100, 0, "%", 0));
    addParam(mpc::intParam("seed", "Seed", 1, 127, 37));
    addParam(mpc::intParam("tune", "Tune", -12, 12, 0, "st"));
    addParam(mpc::floatParam("level", "Level", 0, 100, 85, "%", 0));
    const bool custom = relay::readPair(pair);
    addProgram(custom ? "Recorded pair - Home" : "Factory pair - Home",
               {0, 37, 0, 85});
    addProgram("Borrow a player", {50, 37, 0, 85});
    addProgram("Away break", {100, 37, 0, 85});
    if (!custom)
      relay::factoryPair(pair);
    home();
  }
  void reset() override {
    now = {};
    old = {};
    fade = keys = 0;
    wasPlaying = borrow = away = false;
    home();
  }
  void process(mpc::ProcessContext &c) override {
    const bool playing = c.transport.playing;
    if (wasPlaying && !playing) {
      tail(c.sampleRate);
      keys = 0;
      borrow = away = false;
      home();
    }
    wasPlaying = playing;
    const double level = get(3) * .01;
    int n = 0;
    for (int i = 0; i < c.numFrames; i++) {
      while (n < c.numMidiEvents && c.midi[n].sampleOffset <= i)
        event(c.midi[n++], c.sampleRate);
      double l = 0, r = 0;
      if (fade > 0) {
        render(old, double(fade) / fadeLength, c.sampleRate, l, r);
        --fade;
      }
      render(now, 1, c.sampleRate, l, r);
      c.outputs[0][i] = level * l;
      c.outputs[1][i] = level * r;
    }
  }
};
MPC_PLUGIN_ENTRY(BreakRelay)
