// SPDX-License-Identifier: MIT
#pragma once
#include "mpc_plugin.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdio>

namespace mastering {
inline mpc::PluginInfo effect(const char *name, int uid) {
  mpc::PluginInfo p;
  p.name = name;
  p.vendor = "FG Scratchpad";
  p.uniqueId = uid;
  p.numInputs = p.numOutputs = 2;
  p.version = 1000;
  return p;
}
inline mpc::Param readout(const char *id, const char *name, float low,
                          float high) {
  auto p = mpc::floatParam(id, name, low, high, 0, "dB", 1);
  p.automatable = false;
  return p;
}
// Measurements are host display text. Keep volatile readings out of saved
// knobs.
template <size_t N> class Metered : public mpc::Plugin {
  int first;
  std::array<std::atomic<float>, N> measurements{};

protected:
  Metered(mpc::PluginInfo info, int firstIndex)
      : Plugin(info), first(firstIndex) {
    for (auto &m : measurements)
      m.store(0);
  }
  void meter(size_t i, float value) {
    measurements[i].store(value, std::memory_order_relaxed);
  }
  float reading(size_t i) const {
    return measurements[i].load(std::memory_order_relaxed);
  }

public:
  bool formatValue(int index, float, std::string &out) override {
    if (index < first || size_t(index - first) >= N)
      return false;
    char value[24];
    std::snprintf(value, sizeof(value), "%.1f", reading(index - first));
    out = value;
    return true;
  }
};
inline double amplitude(double db) { return std::pow(10., db / 20.); }
inline double db(double amplitude) {
  return 20. * std::log10(std::max(1e-6, amplitude));
}
} // namespace mastering
