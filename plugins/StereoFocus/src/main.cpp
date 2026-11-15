// SPDX-License-Identifier: MIT
#include "../../Mastering/common.h"

class StereoFocus final : public mpc::Plugin {
  double bassSide = 0, amount = 0, midGain = 1, sideGain = 1;

public:
  StereoFocus()
      : Plugin(
            mastering::effect("Stereo Focus", MPC_FOURCC('F', 'g', 'S', 'f'))) {
    addParam(mpc::floatParam("frequency", "Frequency", 40, 250, 100, "Hz", 0));
    addParam(mpc::floatParam("focus", "Bass focus", 0, 100, 0, "%", 0));
    addParam(mpc::choiceParam("listen", "Listen", {"Stereo", "Mono", "Sides"}));
    addProgram("Original", {100, 0, 0});
    addProgram("Center the sub", {90, 100, 0});
  }
  void reset() override {
    bassSide = 0;
    amount = get(1) * .01;
    midGain = getInt(2) != 2;
    sideGain = getInt(2) != 1;
  }
  void process(mpc::ProcessContext &c) override {
    const double lp = -std::expm1(-6.283185307179586 * get(0) / c.sampleRate);
    const double smooth = -std::expm1(-1 / (.005 * c.sampleRate));
    const double target = get(1) * .01;
    const int mode = getInt(2);
    for (int i = 0; i < c.numFrames; ++i) {
      const double l = c.inputs[0][i], r = c.inputs[1][i];
      const double mid = (l + r) * .5, side = (l - r) * .5;
      bassSide += lp * (side - bassSide);
      amount += smooth * (target - amount);
      midGain += smooth * ((mode != 2) - midGain);
      sideGain += smooth * ((mode != 1) - sideGain);
      const double width = (side - amount * bassSide) * sideGain;
      c.outputs[0][i] = midGain * mid + width;
      c.outputs[1][i] = midGain * mid - width;
    }
  }
};
MPC_PLUGIN_ENTRY(StereoFocus)
