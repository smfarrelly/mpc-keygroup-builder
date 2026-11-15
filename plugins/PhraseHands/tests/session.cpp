// SPDX-License-Identifier: MIT
#include "../../DrumHands/tests/host.h"
using namespace testhost;
int main(int argc, char **argv) {
    assert(argc == 2);
    Plugin teach(argv[1]);
    teach.render(300, {{0,40,100},{10,62,100},{20,69,50},{30,65,100},{40,40,0,128}});
    const auto state = teach.save();
    assert(state.back() == 3);
    auto strike = [&](int pad, int count, int velocity, int block) {
        Plugin p(argv[1],32000,block);
        p.load(state);
        std::vector<Event> hits;
        for (int i=0;i<count;i++) hits.push_back({10+i*17000,pad,velocity});
        return p.render(17000*count,hits);
    };
    // Direct keyboard notes are an exact synthesis reference for pad ordering.
    auto keys = [&](std::vector<int> notes, int velocity) {
        Plugin p(argv[1]);
        std::vector<Event> hits;
        for (int i=0;i<int(notes.size());i++) hits.push_back({10+i*17000,notes[i],velocity});
        return p.render(17000*notes.size(),hits);
    };
    assert(strike(36,4,90,257)==keys({62,69,65,62},90));
    assert(strike(37,3,90,127)==keys({65,69,62},90));
    assert(strike(38,3,90,127)==keys({62,65,69},90));
    assert(strike(39,1,127,127)==keys({65},127));
    assert(strike(39,1,1,127)==keys({62},1));
    teach.render(30,{{0,40,90},{10,40,0,128}});
    assert(teach.save()==state);
    Plugin reset(argv[1]); reset.load(state);
    auto two=reset.render(34000,{{10,36,90},{14000,41,90},{17010,36,90}});
    assert(two==keys({62,62},90));
}
