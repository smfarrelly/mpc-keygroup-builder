// SPDX-License-Identifier: MIT
#pragma once
#include "mpc_plugin.h"
#include <algorithm>
#include <cmath>

namespace mastering {
inline mpc::PluginInfo effect(const char *name, int uid, int version = 1000) {
  mpc::PluginInfo p;
  p.name = name;
  p.vendor = "FG Scratchpad";
  p.uniqueId = uid;
  p.numInputs = p.numOutputs = 2;
  p.version = version;
  return p;
}
inline mpc::Param readout(const char *id, const char *name, float low,
                          float high) {
  auto p = mpc::floatParam(id, name, low, high, 0, "dB", 1);
  p.automatable = false;
  return p;
}
inline double amplitude(double db) { return std::pow(10., db / 20.); }
inline double db(double amplitude) {
  return 20. * std::log10(std::max(1e-6, amplitude));
}
} // namespace mastering
