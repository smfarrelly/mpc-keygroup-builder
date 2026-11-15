// SPDX-License-Identifier: MIT
#include "../../PerformanceEffects/attack.h"

class GhostFader final : public mpc::Plugin {
  performance::Attack detector;
  std::array<double, 8> history{};
  int next = 0, measuring = 0;
  double previous = 0, peak = 0, gain = 1, relative = 1;

public:
  GhostFader()
      : Plugin(
            performance::info("Ghost Fader", MPC_FOURCC('F', 'g', 'G', 'f'))) {
    addParam(mpc::floatParam("balance", "Balance", -100, 100, 0, "%", 0));
    addParam(mpc::floatParam("split", "Split", 15, 85, 52, "%", 0));
    addParam(mpc::floatParam("isolation", "Isolation", 0, 100, 95, "%", 0));
    addParam(mpc::floatParam("sense", "Sensitivity", 0, 100, 70, "%", 0));
    addProgram("Full take", {0, 52, 95, 70});
    addProgram("Ghost strokes", {-100, 52, 95, 70});
    addProgram("Backbone", {100, 52, 95, 70});
  }
  void reset() override {
    detector = {};
    history = {};
    next = measuring = 0;
    previous = peak = 0;
    gain = relative = 1;
  }
  void process(mpc::ProcessContext &c) override {
    const double fall = std::exp(-1 / (.007 * c.sampleRate)),
                 smooth = -std::expm1(-1 / (.001 * c.sampleRate));
    const double floor = performance::threshold(get(3)), split = get(1) * .01,
                 balance = get(0) * .01;
    for (int i = 0; i < c.numFrames; ++i) {
      const double l = c.inputs[0][i], r = c.inputs[1][i],
                   level = std::max(std::abs(l), std::abs(r));
      if (detector.tick(level, floor, fall, int(.023 * c.sampleRate))) {
        previous = *std::max_element(history.begin(), history.end());
        peak = 0;
        measuring = std::max(1, int(.009 * c.sampleRate));
      }
      if (measuring) {
        peak = std::max(peak, level);
        relative = previous > 0 ? peak / previous : 1;
        if (!--measuring) {
          history[next] = peak;
          next = (next + 1) % history.size();
        }
      }
      const double accent = std::clamp((relative - split + .12) / .24, 0., 1.);
      const double rejected = balance < 0 ? accent : 1 - accent;
      const double target = 1 - std::abs(balance) * get(2) * .01 * rejected;
      gain += (target - gain) * smooth;
      c.outputs[0][i] = l * gain;
      c.outputs[1][i] = r * gain;
    }
  }
};
MPC_PLUGIN_ENTRY(GhostFader)
