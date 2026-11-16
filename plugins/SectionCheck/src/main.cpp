// SPDX-License-Identifier: MIT
#include "../../Mastering/common.h"
#include <array>
#include <cstdint>

struct Reading {
  double energy = 0, peak = 0;
  uint64_t frames = 0;
  double rms() const { return frames ? std::sqrt(energy / frames) : 0; }
};

class SectionCheck final : public mpc::Plugin {
  std::array<Reading, 2> windows{};
  int previous = 0, refreshIn = 0;

public:
  SectionCheck()
      : Plugin([] {
          auto info = mastering::effect("Section Check", MPC_FOURCC('F', 'g', 'S', 'c'));
          info.version = 1001;
          return info;
        }()) {
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
  void reset() override {
    windows = {};
    // Leave the restored panel visible until the first measurement interval.
    previous = getInt(0);
    refreshIn = std::max(1, int(sampleRate() / 5));
  }
  void process(mpc::ProcessContext &c) override {
    const int mode = getInt(0);
    const bool switched = mode != previous;
    if (mode && switched)
      windows[mode - 1] = {};
    previous = mode;
    for (int i = 0; i < c.numFrames; ++i) {
      const double l = c.inputs[0][i], r = c.inputs[1][i];
      if (mode && (!c.transport.valid || c.transport.playing)) {
        auto &w = windows[mode - 1];
        w.energy += .5 * (l * l + r * r);
        w.peak = std::max({w.peak, std::abs(l), std::abs(r)});
        ++w.frames;
      }
      c.outputs[0][i] = l;
      c.outputs[1][i] = r;
    }
    refreshIn -= c.numFrames;
    if (!switched && refreshIn > 0)
      return;
    refreshIn = std::max(1, int(c.sampleRate / 5));
    const auto &a = windows[0], &b = windows[1];
    const bool valid = a.peak > 0 && b.peak > 0;
    const double rms =
        valid ? mastering::db(b.rms()) - mastering::db(a.rms()) : 0;
    const double peak =
        valid ? mastering::db(b.peak) - mastering::db(a.peak) : 0;
    const std::array<float, 4> values = {
        float(rms), float(peak), float(peak - rms),
        float((a.peak > 0 ? 1 : 0) + (b.peak > 0 ? 2 : 0))};
    bool changed = false;
    for (int i = 1; i <= 4; ++i) {
      const float target = param(i).toNormalised(values[i-1]);
      if (getNormalised(i) != target) {
        setNormalised(i, target);
        changed = true;
      }
    }
    if (changed || switched)
      requestDisplayUpdate();
  }
};
MPC_PLUGIN_ENTRY(SectionCheck)
