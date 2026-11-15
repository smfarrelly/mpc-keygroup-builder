// SPDX-License-Identifier: MIT
#include "../../PerformanceEffects/attack.h"
#include <cstdio>
#include <vector>

class BodyPrint final : public mpc::Plugin {
  struct Tap {
    int delay = 0;
    float gain = 0;
  };
  struct Body {
    std::array<Tap, 48> taps{};
    int count = 0;
  };
  std::array<Body, 2> bodies{};
  std::array<std::vector<float>, 2> ring;
  int write = 0, measure = 0;
  double peak = 0, held = .5, color = .5, previousLength = 1;
  performance::Attack detector;
  bool readBodies() {
    const auto path =
        mpc::detail::computePluginFolder() + "/Content/bodies.bin";
    auto f = std::fopen(path.c_str(), "rb");
    if (!f)
      return false;
    std::array<uint8_t, 391> bytes{};
    const auto n = std::fread(bytes.data(), 1, bytes.size(), f);
    std::fclose(f);
    if (n < 6 || std::memcmp(bytes.data(), "BOD1", 4))
      return false;
    size_t pos = 4;
    for (auto &b : bodies) {
      if (pos >= n)
        return false;
      b.count = bytes[pos++];
      if (b.count < 1 || b.count > 48 || pos + 4 * b.count > n)
        return false;
      int prev = -1;
      double power = 0;
      for (int i = 0; i < b.count; i++, pos += 4) {
        int d = bytes[pos] + 256 * bytes[pos + 1];
        int gain = bytes[pos + 2] + 256 * bytes[pos + 3];
        if (gain >= 32768)
          gain -= 65536;
        if (d <= prev || d > 1920)
          return false;
        prev = d;
        b.taps[i] = {d, gain / 32767.f};
        power += b.taps[i].gain * b.taps[i].gain;
      }
      if (power < .95 || power > 1.05)
        return false;
    }
    return pos == n;
  }
  void factory() {
    bodies = {};
    for (int b = 0; b < 2; b++) {
      auto &body = bodies[b];
      body.count = 8;
      for (int i = 0; i < 8; i++)
        body.taps[i] = {i * (b ? 93 : 23),
                        float((i % 2 && b ? -1 : 1) * .55 * std::pow(.86, i))};
    }
  }

public:
  BodyPrint()
      : Plugin(
            performance::info("Body Print", MPC_FOURCC('F', 'g', 'B', 'p'))) {
    const bool custom = readBodies();
    if (!custom)
      factory();
    addParam(mpc::floatParam("body", "Body", 0, 100, 0, "%", 0));
    addParam(mpc::floatParam("touch", "Touch", 0, 100, 0, "%", 0));
    addParam(mpc::floatParam("length", "Length", 25, 200, 100, "%", 0));
    addParam(mpc::floatParam("blend", "Blend", 0, 100, 65, "%", 0));
    addProgram(custom ? "Sample body A" : "Factory body A", {0, 0, 100, 65});
    addProgram("Body B", {100, 0, 100, 65});
    addProgram("Play both bodies", {50, 100, 100, 65});
  }
  void prepare(double sr, int) override {
    for (auto &channel : ring)
      channel.assign(size_t(std::ceil(sr * .121)) + 4, 0);
  }
  void reset() override {
    for (auto &channel : ring)
      std::fill(channel.begin(), channel.end(), 0);
    write = measure = 0;
    peak = 0;
    held = color = get(0) * .01;
    previousLength = get(2) * .01;
    detector = {};
  }
  void process(mpc::ProcessContext &c) override {
    const int size = int(ring[0].size());
    const double length = get(2) * .01, mix = get(3) * .01,
                 touch = get(1) * .01, manual = get(0) * .01;
    const double rate = c.sampleRate / 32000.,
                 fall = std::exp(-1 / (.007 * c.sampleRate));
    const double move = -std::expm1(-1 / (.002 * c.sampleRate));
    // Precompute delay indices outside the sample loop. Crossfade old and
    // new spacings over the block when the Length control is moved.
    std::array<std::array<std::array<int, 48>, 2>, 2> delays{};
    for (int b = 0; b < 2; b++)
      for (int j = 0; j < bodies[b].count; j++) {
        delays[0][b][j] =
            int(std::round(rate * length * bodies[b].taps[j].delay));
        delays[1][b][j] =
            int(std::round(rate * previousLength * bodies[b].taps[j].delay));
      }
    bool changing = length != previousLength;
    for (int i = 0; i < c.numFrames; i++) {
      const float l = c.inputs[0][i], r = c.inputs[1][i];
      const double amplitude = std::max(std::abs(l), std::abs(r));
      if (detector.tick(amplitude, .006, fall, int(.025 * c.sampleRate))) {
        peak = 0;
        measure = std::max(1, int(.008 * c.sampleRate));
      }
      if (measure > 0) {
        peak = std::max(peak, amplitude);
        held = std::clamp((peak - .08) / .52, 0., 1.);
        --measure;
      }
      color += (manual * (1 - touch) + touch * held - color) * move;
      ring[0][write] = l;
      ring[1][write] = r;
      double wet[2] = {};
      for (int b = 0; b < 2; b++) {
        const double weight = b ? color : 1 - color;
        if (weight < .000001)
          continue;
        for (int j = 0; j < bodies[b].count; j++) {
          int k = write - delays[0][b][j];
          if (k < 0)
            k += size;
          double a = weight * bodies[b].taps[j].gain;
          if (changing) {
            int old = write - delays[1][b][j];
            if (old < 0)
              old += size;
            double t = double(i + 1) / c.numFrames;
            wet[0] += a * (1 - t) * ring[0][old];
            wet[1] += a * (1 - t) * ring[1][old];
            a *= t;
          }
          wet[0] += a * ring[0][k];
          wet[1] += a * ring[1][k];
        }
      }
      c.outputs[0][i] = (1 - mix) * l + mix * std::tanh(wet[0]);
      c.outputs[1][i] = (1 - mix) * r + mix * std::tanh(wet[1]);
      if (++write == size)
        write = 0;
    }
    previousLength = length;
  }
};
MPC_PLUGIN_ENTRY(BodyPrint)
