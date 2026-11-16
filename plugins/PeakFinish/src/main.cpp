// SPDX-License-Identifier: MIT
#include "../../Mastering/common.h"

class PeakFinish final : public mpc::Plugin {
  double reductionDb = 0, drive = 1;
  double windowPeak = 0;
  int refreshIn = 0;
  double dryPower = 0, wetPower = 0, dryMix = 0, matchMix = 0;

public:
  PeakFinish()
      : Plugin(mastering::effect("Peak Finish", MPC_FOURCC('F', 'g', 'P', 'f'), 1001)) {
    addParam(mpc::floatParam("drive", "Drive", 0, 12, 0, "dB", 1));
    addParam(mpc::floatParam("ceiling", "Ceiling", -12, 0, -1, "dBFS", 1));
    addParam(mpc::choiceParam("listen", "Listen",
                              {"Print", "Matched wet", "Matched dry"}));
    addParam(mastering::readout("reduction", "Reduction", 0, 36));
    addProgram("Gentle peaks", {0, -1, 0, 0});
    addProgram("Drum push", {3, -1, 0, 0});
  }
  void reset() override {
    dryPower = wetPower = 0;
    drive = mastering::amplitude(get(0));
    dryMix = getInt(2) == 2;
    matchMix = getInt(2) != 0;
    reductionDb = 0;
    windowPeak = 0;
    refreshIn = std::max(1, int(sampleRate() / 10));
  }
  void process(mpc::ProcessContext &c) override {
    const double driveTarget = mastering::amplitude(get(0)),
                 ceiling = mastering::amplitude(get(1));
    const double knee = .8 * ceiling, span = ceiling - knee;
    const double average = -std::expm1(-1. / (.4 * c.sampleRate));
    const double fade = -std::expm1(-1. / (.004 * c.sampleRate));
    const int mode = getInt(2);
    double minGain = 1;
    for (int i = 0; i < c.numFrames; ++i) {
      const double l = c.inputs[0][i], r = c.inputs[1][i];
      drive += fade * (driveTarget - drive);
      const double peak = std::max(std::abs(l), std::abs(r)) * drive;
      const double excess = std::max(0., peak - knee);
      const double gain =
          excess > 0 ? (knee + span * excess / (span + excess)) / peak : 1;
      minGain = std::min(gain, minGain);
      const double wet = drive * gain;
      const double power = (l * l + r * r) * .5;
      dryPower += average * (power - dryPower);
      wetPower += average * (power * wet * wet - wetPower);
      // Compare at the quieter level, so auditioning never needs extra
      // headroom.
      const double ratio = std::sqrt((wetPower + 1e-15) / (dryPower + 1e-15));
      dryMix += fade * ((mode == 2) - dryMix);
      matchMix += fade * ((mode != 0) - matchMix);
      double out =
          wet * (1 - dryMix) * (1 + matchMix * (std::min(1., 1 / ratio) - 1)) +
          dryMix * std::min(1., ratio);
      if (mode == 0 && peak > 0)
        out = std::min(out, ceiling * drive / peak);
      c.outputs[0][i] = l * out;
      c.outputs[1][i] = r * out;
    }
    reductionDb = std::max(-mastering::db(minGain),
                           reductionDb - 12. * c.numFrames / c.sampleRate);
    windowPeak = std::max(windowPeak, reductionDb);
    refreshIn -= c.numFrames;
    if (refreshIn <= 0) {
      // Keep brief drum peaks visible between panel refreshes.
      const float db = std::min(36., std::round(windowPeak * 10) / 10);
      if (getNormalised(3) != param(3).toNormalised(db)) {
        set(3, db);
        requestDisplayUpdate();
      }
      windowPeak = 0;
      refreshIn = std::max(1, int(c.sampleRate / 10));
    }
  }
};
MPC_PLUGIN_ENTRY(PeakFinish)
