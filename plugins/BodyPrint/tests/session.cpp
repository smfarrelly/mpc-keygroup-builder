// SPDX-License-Identifier: MIT
#include "../../DrumHands/tests/host.h"
using namespace testhost;
int main(int argc, char **argv) {
  assert(argc == 2);
  const int frames = 18000;
  auto input = silence(frames);
  for (int i = 0; i < frames; i++) {
    double amp = i < 6000 ? .055 : i < 10000 ? 0. : i < 10500 ? .85 : .045;
    input[0][i] = amp * std::cos(.12 * i);
    input[1][i] = -.5 * input[0][i];
  }
  Plugin dry(argv[1]);
  dry.set(3, 0);
  assert(dry.render(frames, {}, &input) == input);
  auto render = [&](int preset, int block) {
    Plugin p(argv[1], 32000, block);
    p.preset(preset);
    p.set(3, 1);
    return p.render(frames, {}, &input);
  };
  const auto a = render(0, 128), b = render(1, 128), touch = render(2, 128);
  assert(touch == render(2, 257));
  assert(a != b);
  double softA = 0, softB = 0, heldA = 0, heldB = 0;
  for (int i = 3000; i < 5000; i++) {
    softA += std::abs(touch[0][i] - a[0][i]);
    softB += std::abs(touch[0][i] - b[0][i]);
    heldA += std::abs(touch[0][i + 11000] - a[0][i + 11000]);
    heldB += std::abs(touch[0][i + 11000] - b[0][i + 11000]);
  }
  assert(softA < softB * .01 && heldB < heldA * .01);
  assert(energy(touch, 8000, 9000) == 0);
}
