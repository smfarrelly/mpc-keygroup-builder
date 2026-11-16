// SPDX-License-Identifier: MIT
#include "../DrumHands/tests/host.h"
using namespace testhost;

Audio tone(int rate, double hz, double level, double right = 1) {
  Audio a = silence(rate);
  for (int i = 0; i < rate; ++i) {
    a[0][i] = level * std::sin(6.283185307179586 * hz * i / rate);
    a[1][i] = a[0][i] * right;
  }
  return a;
}

void checkClip(const char *binary, int rate) {
  auto input = tone(rate, 60, .18, -.35);
  Plugin p(binary, rate);
  assert(p.render(rate, {}, &input) == input);
  input[0][rate / 2] = 1.7;
  input[1][rate / 2] = -.595;
  p.preset(1);
  p.render(rate);
  auto wet = p.render(rate, {}, &input);
  for (int i = 0; i < rate; ++i) {
    assert(std::abs(wet[0][i]) <= std::pow(10., -1. / 20) + 1e-7);
    assert(std::abs(wet[1][i] + .35 * wet[0][i]) < 1e-6);
  }
  Plugin recall(binary, rate, 257);
  recall.load(p.save());
  assert(recall.render(rate, {}, &input) == wet);
  assert(std::stod(recall.display(3)) > 0);
  assert(std::abs(recall.normalized(3)*36 - std::stod(recall.display(3))) < .05);
  recall.render(2*rate);
  assert(recall.normalized(3) == 0);
  // With stationary levels and extra drive, the two audition positions should
  // null.
  input = tone(rate, 100, .12, .65);
  p.set(2, .5);
  p.render(rate, {}, &input);
  auto matched = p.render(rate, {}, &input);
  p.set(2, 1);
  auto dry = p.render(rate, {}, &input);
  double ratio = energy(dry, rate / 2, rate) / energy(matched, rate / 2, rate);
  assert(std::abs(10 * std::log10(ratio)) < .05);
}

void checkFocus(const char *binary, int rate) {
  Plugin p(binary, rate);
  auto signal = tone(rate, 80, .6, -.3);
  assert(p.render(rate, {}, &signal) == signal);
  p.preset(1);
  for (int hz : {25, 2000}) {
    auto side = tone(rate, hz, .5, -1);
    auto wet = p.render(rate, {}, &side);
    double ratio = energy(wet, rate / 2, rate) / energy(side, rate / 2, rate);
    assert(hz == 25 ? ratio < .1 : ratio > .95);
  }
  p.set(2, .5);
  auto mono = p.render(rate, {}, &signal);
  assert(std::abs(mono[0][rate / 2 + 1] - mono[1][rate / 2 + 1]) < 1e-6);
  p.set(2, 1);
  auto center = tone(rate, 80, .8);
  auto sides = p.render(rate, {}, &center);
  assert(energy(sides, rate / 2, rate) < 1e-12);
}

void checkSections(const char *binary, int rate) {
  Plugin p(binary, rate, 127);
  auto a = tone(rate, 100, .25), b = tone(rate, 100, .5);
  auto delta = [&](int i) { return std::stod(p.display(i)); };
  p.set(0, .5);
  assert(p.render(rate, {}, &a) == a);
  assert(p.display(4) == "A only");
  assert(std::abs(p.normalized(4) - 1.f / 3) < 1e-5);
  p.set(0, 1);
  p.playing = false;
  p.render(rate, {}, &a);
  assert(p.display(4) == "A only");
  p.playing = true;
  assert(p.render(rate, {}, &b) == b);
  assert(std::abs(delta(1) - 6.0) < .001 && std::abs(delta(2) - 6.0) < .001);
  assert(std::abs(delta(3)) < .001 && p.display(4) == "A and B");
  assert(std::abs(p.normalized(1) * 96 - 48 - 6.02) < .05);
  p.set(0, 0);
  p.render(rate);
  assert(std::abs(delta(1) - 6.0) < .001);
  p.set(0, 1);
  b = silence(rate);
  b[0][0] = .5;
  p.render(rate, {}, &b);
  assert(delta(3) > 30 && delta(1) < -30);
  p.set(0, .5);
  p.render(rate);
  assert(p.display(4) == "B only" && std::abs(delta(1)) < .001);
}

int main(int argc, char **argv) {
  assert(argc == 4);
  for (int rate : {32000, 44100, 48000, 96000}) {
    checkClip(argv[1], rate);
    checkFocus(argv[2], rate);
    checkSections(argv[3], rate);
  }
}
