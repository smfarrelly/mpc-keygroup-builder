// SPDX-License-Identifier: MIT
#include "../DrumHands/tests/host.h"
using namespace testhost;
constexpr int sr = 32000, bar = sr * 2;
Audio drums() {
  auto a = silence(bar);
  for (int j = 0; j < 8; j++)
    for (int i = 0; i < 1600; i++) {
      float v = (j % 2 ? .13 : .8) * std::exp(-i / 500.) * std::cos(i * .15);
      a[0][j * 8000 + i] = v;
      a[1][j * 8000 + i] = -v * .7;
    }
  return a;
}
int main(int argc, char **argv) {
  assert(argc == 4);
  const auto input = drums();
  Plugin neutral(argv[1]);
  assert(neutral.render(bar, {}, &input) == input);
  Plugin ghosts(argv[1]), accents(argv[1]);
  ghosts.preset(1);
  accents.preset(2);
  const auto g = ghosts.render(bar, {}, &input),
             a = accents.render(bar, {}, &input);
  assert(energy(g, 8000, 9600) > energy(a, 8000, 9600) * 5);
  assert(energy(a, 16000, 17600) > energy(g, 16000, 17600) * 5);
  assert(energy(g, 8500, 9250) > energy(input, 8500, 9250) * .85);
  // Learn exact timing, save it, and articulate a different input in a fresh
  // instance.
  Plugin teach(argv[2]);
  teach.set(0, 1);
  assert(teach.render(bar, {}, &input) == input);
  teach.render(128);
  teach.set(0, 0);
  const auto state = teach.save();
  assert(state.size() >= 26 && state[state.size() - 25] == 8);
  for (int i = 0; i < 8; i++) {
    size_t at = state.size() - 24 + i * 3;
    assert((state[at] | state[at + 1] << 8) == i * 512);
    assert(i % 2 ? state[at + 2] < 32 : state[at + 2] == 127);
  }
  Audio constant = silence(bar);
  for (auto &ch : constant)
    std::fill(ch.begin(), ch.end(), .5);
  auto recall = [&](int block) {
    Plugin p(argv[2], sr, block);
    p.load(state);
    p.set(1, 1);
    return p.render(bar, {}, &constant);
  };
  auto shaped = recall(257);
  assert(shaped == recall(127));
  assert(energy(shaped, 16200, 16600) > energy(shaped, 8200, 8600) * 8);
  Plugin loop(argv[2]);
  loop.cycleEnd = 4;
  loop.set(0, 1);
  loop.render(bar, {}, &input);
  loop.position = 0;
  loop.render(128);
  loop.set(0, 0);
  assert(loop.save() == state);
  // Capturing silence and stopping in the middle of a new take preserve the
  // last groove.
  loop.render(bar - 128);
  loop.set(0, 1);
  loop.render(bar + 128);
  loop.set(0, 0);
  assert(loop.save() == state);
  loop.render(bar - 128);
  loop.set(0, 1);
  loop.render(512);
  loop.playing = false;
  loop.render(128);
  loop.set(0, 0);
  assert(loop.save() == state);
  Plugin stopped(argv[2]);
  stopped.playing = false;
  assert(stopped.render(bar, {}, &constant) == constant);
  // Sustain real stereo input, then clear the accumulated bed.
  Plugin choir(argv[3]);
  Audio source = silence(sr);
  for (int i = 0; i < sr / 3; i++) {
    source[0][i] = .5 * std::cos(.091 * i) * std::exp(-i / 7000.);
    source[1][i] = source[0][i] * -.5;
  }
  auto bed = choir.render(sr, {}, &source);
  assert(std::equal(bed[0].begin(), bed[0].begin() + 320, source[0].begin()));
  assert(energy(bed, sr / 2, sr) > 1);
  for (int i = sr / 2; i < sr; i++)
    assert(std::abs(bed[0][i] * .5 + bed[1][i]) < .00001);
  choir.set(3, 1);
  auto clear = choir.render(sr / 4);
  assert(energy(clear, sr / 8, sr / 4) < .00001);
  // Empty slots pass the input through. Set MPC_PLUGIN_FOLDER to a fixture
  // with an offbeat in slot 1 when checking installed-file discovery.
  if (std::getenv("MPC_PLUGIN_FOLDER")) {
    Plugin file(argv[2]);
    file.preset(1);
    file.set(1, 1);
    auto gate = file.render(bar, {}, &constant);
    assert(energy(gate, 5000, 6000) < .01 && energy(gate, 16200, 16600) > 20);
    file.preset(4);
    file.render(5000);
    auto dry = file.render(bar, {}, &constant);
    assert(dry[0].back() == .5f);
  }
}
