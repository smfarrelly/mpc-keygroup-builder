// SPDX-License-Identifier: MIT
#include "variation.h"
#include <iostream>

// Convert the same performance decisions as the plugin into sixteenth-note events.
int main() {
    shadow::Groove groove{};
    int root;
    if (!(std::cin >> root) || root < 30 || root > 79)
        return 2;
    for (auto &row : groove)
        for (auto &v : row) {
            int vel;
            if (!(std::cin >> vel) || vel < 0 || vel > 127)
                return 2;
            v = uint8_t(vel);
        }
    for (int scene = 0; scene < 4; scene++)
        for (int step = 0; step < 16; step++)
            shadow::step(groove, step, scene, root, [&](shadow::Note n) {
                std::cout << scene << " " << step << " " << n.melody << " " << n.lane << " " << n.pitch
                          << " " << n.velocity << "\n";
            });
}
