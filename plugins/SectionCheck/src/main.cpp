// SPDX-License-Identifier: MIT
#include "../../Mastering/common.h"
#include <array>
#include <cstdint>

struct Reading {
  double energy = 0, peak = 0;
  uint64_t frames = 0;
  double rms() const { return frames ? std::sqrt(energy / frames) : 0; }
};

class SectionCheck final : public mastering::Metered<4> {
  std::array<Reading, 2> windows{};
  int previous = 0;

public:
  SectionCheck()
      : Metered(
            mastering::effect("Section Check", MPC_FOURCC('F', 'g', 'S', 'c')),
            1) {
    addParam(mpc::choiceParam("capture", "Capture", {"Hold", "A", "B"}));
    addParam(mastering::readout("rms", "RMS B-A", -48, 48));
    addParam(mastering::readout("peak", "Peak B-A", -48, 48));
    addParam(mastering::readout("crest", "Crest B-A", -48, 48));
    auto status = mpc::choiceParam("status", "Readings",
                                   {"Empty", "A only", "B only", "A and B"});
    status.automatable = false;
    addParam(status);
    addProgram("Compare sections", {0, 0, 0, 0, 0});
  }
  bool formatValue(int index, float value, std::string &out) override {
    if (index == 4) {
      static constexpr const char *labels[] = {"Empty", "A only", "B only",
                                               "A and B"};
      out = labels[static_cast<int>(reading(3))];
      return true;
    }
    return Metered::formatValue(index, value, out);
  }
  void reset() override {
    windows = {};
    previous = 0;
    for (int i = 0; i < 4; ++i)
      meter(i, 0);
  }
  void process(mpc::ProcessContext &c) override {
    const int mode = getInt(0);
    if (mode && mode != previous)
      windows[mode - 1] = {};
    previous = mode;
    for (int i = 0; i < c.numFrames; ++i) {
      const double l = c.inputs[0][i], r = c.inputs[1][i];
      if (mode && c.transport.playing) {
        auto &w = windows[mode - 1];
        w.energy += .5 * (l * l + r * r);
        w.peak = std::max({w.peak, std::abs(l), std::abs(r)});
        ++w.frames;
      }
      c.outputs[0][i] = l;
      c.outputs[1][i] = r;
    }
    const auto &a = windows[0], &b = windows[1];
    const bool valid = a.peak > 0 && b.peak > 0;
    const double rms =
        valid ? mastering::db(b.rms()) - mastering::db(a.rms()) : 0;
    const double peak =
        valid ? mastering::db(b.peak) - mastering::db(a.peak) : 0;
    meter(3, (a.peak > 0 ? 1 : 0) + (b.peak > 0 ? 2 : 0));
    meter(0, rms);
    meter(1, peak);
    meter(2, peak - rms);
  }
};
MPC_PLUGIN_ENTRY(SectionCheck)
