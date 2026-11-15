// SPDX-License-Identifier: MIT
#include "../../DrumHands/tests/host.h"
using namespace testhost;
int main(int argc, char **argv) {
  assert(argc == 2);
  auto take = [&](int block, float wander, int overridePad = 0) {
    Plugin p(argv[1], 32000, block);
    p.set(0, wander);
    std::vector<Event> hits = {{0, 40, 100},
                               {10, 36, 127},
                               {2010, 37, 127},
                               {4010, 38, 127},
                               {6010, 39, 127}};
    if (overridePad)
      hits.insert(hits.begin(), {0, overridePad, 100});
    return p.render(8000, hits);
  };
  const auto a = take(127, 0), b = take(257, 1), mix = take(128, .5);
  assert(a != b && mix != a && mix != b && mix == take(257, .5));
  assert(take(257, 0, 41) == mix && take(257, 0, 42) == b);
  // In the numbered bank kick->snare skips slice 1; hat must follow that snare.
  // Forward order makes the second hat the correct answer.
  for (int j = 0; j < 4; j++) {
    int code = std::array<int, 4>{1, 3, 4, 8}[j];
    double expected = .85 * code * 1000 / 32768.;
    assert(std::abs(a[0][2000 * j + 110] - expected) < 1e-6);
    assert(std::abs(b[0][2000 * j + 110] - expected - .85 * 8000 / 32768.) <
           1e-6);
    assert(a[1][2000 * j + 110] == -a[0][2000 * j + 110]);
  }
  Plugin p(argv[1]);
  p.set(0, .5);
  auto state = p.save();
  p.render(10000, {{0, 39, 80}, {3000, 37, 90}});
  auto restored = p.render(8000, {{0, 40, 100},
                                  {10, 36, 127},
                                  {2010, 37, 127},
                                  {4010, 38, 127},
                                  {6010, 39, 127}});
  assert(restored == mix);
  Plugin q(argv[1]);
  q.load(state);
  assert(q.render(8000, {{0, 40, 100},
                         {10, 36, 127},
                         {2010, 37, 127},
                         {4010, 38, 127},
                         {6010, 39, 127}}) == mix);
  Plugin tuned(argv[1]);
  auto oct = tuned.render(
      5000, {{0, 72, 90}, {10, 36, 127}, {2000, 72, 0, 128}, {2010, 36, 127}});
  assert(oct[0][700] == 0 && oct[0][2700] != 0);
}
