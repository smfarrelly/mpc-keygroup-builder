// SPDX-License-Identifier: MIT
#include "../../PerformanceEffects/attack.h"

class TailChoir final : public mpc::Plugin {
  static constexpr int capacity = 8192;
  struct Voice {
    std::array<std::array<float, capacity>, 2> audio{};
    int length = 0, phase = 0;
    double level = 0;
    bool retiring = false;
  };
  // Three sounding grains and one spare for a crossfade or the next recording.
  std::array<Voice, 4> voices{};
  performance::Attack detector;
  int slot = 0, wait = 0, written = 0, wanted = 0;

public:
  TailChoir()
      : Plugin(
            performance::info("Tail Choir", MPC_FOURCC('F', 'g', 'T', 'c'))) {
    addParam(mpc::floatParam("bed", "Bed", 0, 100, 52, "%", 0));
    addParam(mpc::floatParam("wait", "Wait", 12, 200, 45, "ms", 0));
    addParam(mpc::floatParam("grain", "Grain", 25, 120, 70, "ms", 0));
    addParam(mpc::boolParam("clear", "Clear", false));
    addProgram("Wurli breath", {52, 65, 92, 0});
    addProgram("Vinyl dust", {78, 25, 46, 0});
  }
  void reset() override {
    detector = {};
    slot = wait = written = wanted = 0;
    for (auto &v : voices) {
      v.length = 0;
      v.level = 0;
      v.retiring = false;
    }
  }
  void process(mpc::ProcessContext &c) override {
    const double fall = std::exp(-1 / (.007 * c.sampleRate)),
                 fade = -std::expm1(-1 / (.005 * c.sampleRate));
    const double bed = get(0) * .01 * .48;
    const bool clear = getBool(3);
    for (int i = 0; i < c.numFrames; i++) {
      const float l = c.inputs[0][i], r = c.inputs[1][i];
      const bool hit = detector.tick(std::max(std::abs(l), std::abs(r)), .009,
                                     fall, int(.028 * c.sampleRate));
      if (clear) {
        wanted = 0;
        for (auto &v : voices)
          v.retiring = true;
      } else if (hit) {
        wait = int(c.sampleRate * .001 * get(1));
        written = 0;
        wanted =
            std::clamp(2 * int(c.sampleRate * .0005 * get(2)), 4, capacity);
        voices[slot].retiring = true;
      }
      if (wanted && !clear) {
        if (wait)
          --wait;
        else {
          auto &v = voices[slot];
          // This spare was faded out while the previous three grains played.
          v.length = 0;
          v.audio[0][written] = l;
          v.audio[1][written] = r;
          if (++written == wanted) {
            v.length = wanted;
            v.phase = 0;
            v.level = 0;
            v.retiring = false;
            wanted = 0;
            slot = (slot + 1) % voices.size();
            voices[slot].retiring = true;
          }
        }
      }
      double sum[2] = {};
      for (auto &v : voices) {
        if (!v.length)
          continue;
        v.level += ((v.retiring ? 0. : 1.) - v.level) * fade;
        if (v.retiring && v.level < .00005) {
          v.length = 0;
          continue;
        }
        const int half = v.length / 2, second = (v.phase + half) % v.length;
        const double weight = 1. - std::abs(v.phase - half) / double(half);
        for (int ch = 0; ch < 2; ch++)
          sum[ch] += v.level * (weight * v.audio[ch][v.phase] +
                                (1 - weight) * v.audio[ch][second]);
        v.phase = (v.phase + 1) % v.length;
      }
      c.outputs[0][i] = l + bed * sum[0];
      c.outputs[1][i] = r + bed * sum[1];
    }
  }
};
MPC_PLUGIN_ENTRY(TailChoir)
