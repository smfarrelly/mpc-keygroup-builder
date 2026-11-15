// SPDX-License-Identifier: MIT
// Private audition driver: interleaved stereo float32 at 32 kHz on
// stdin/stdout.
#include "../DrumHands/tests/host.h"
#include <cstdio>
using namespace testhost;
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  Plugin p(argv[1], 32000);
  p.preset(std::stoi(argv[2]));
  std::array<float, 8192> buffer{};
  while (size_t count =
             std::fread(buffer.data(), sizeof(float), buffer.size(), stdin)) {
    if (count % 2)
      return 1;
    auto input = silence(count / 2);
    for (size_t i = 0; i < count; ++i)
      input[i % 2][i / 2] = buffer[i];
    const auto rendered = p.render(count / 2, {}, &input);
    for (size_t i = 0; i < count; ++i)
      buffer[i] = rendered[i % 2][i / 2];
    if (std::fwrite(buffer.data(), sizeof(float), count, stdout) != count)
      return 1;
  }
  return std::ferror(stdin) ? 1 : 0;
}
