// SPDX-License-Identifier: MIT
#pragma once
#include "mpc_plugin.h"
#include <algorithm>
#include <array>
#include <cmath>

// Stereo-linked peak envelope and a rising-edge detector. A decaying tail
// must pass a valley and rise again before it can become a new attack.
namespace performance {
struct Attack {
  double envelope = 0, peak = 0, valley = 0;
  int hold = 0;
  bool ready = true;
  bool tick(double level, double floor, double fall, int refractory) {
    envelope = std::max(level, envelope * fall);
    if (hold)
      --hold;
    if (!ready) {
      peak = std::max(peak, level);
      if (!hold && envelope < std::max(floor * .6, peak * .32)) {
        ready = true;
        valley = envelope;
      }
    }
    if (ready) {
      valley = std::min(valley, envelope);
      if (level >= std::max(floor, valley * 1.8)) {
        ready = false;
        hold = refractory;
        peak = level;
        return true;
      }
    }
    return false;
  }
};

inline mpc::PluginInfo info(const char *name, int uid) {
  mpc::PluginInfo p;
  p.name = name;
  p.vendor = "FG Scratchpad";
  p.uniqueId = uid;
  p.numInputs = 2;
  p.version = 1000;
  return p;
}
inline double threshold(double sensitivity) {
  return .12 * std::pow(.015, sensitivity * .01);
}
} // namespace performance
