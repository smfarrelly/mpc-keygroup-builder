// SPDX-License-Identifier: MIT
#include "../../PerformanceEffects/attack.h"
#include <mutex>

class RhythmImprint final : public mpc::Plugin {
  struct Groove {
    std::array<int, 64> ticks{}, levels{};
    int size = 0;
    void add(int t, int v) {
      if (size && ticks[size - 1] == t)
        levels[size - 1] = std::max(levels[size - 1], v);
      else if (size < 64) {
        ticks[size] = t;
        levels[size++] = v;
      }
    }
  };
  Groove saved, live, draft;
  std::array<Groove, 4> files{};
  std::mutex state;
  unsigned version = 0, seen = 0;
  performance::Attack detector;
  int last = -1, cursor = 0, measure = 0, peakIndex = -1;
  bool wasLearn = false, armed = false, recording = false, pending = false;
  double env = 0, gain = 1, expected = 0;
  bool running = false;
  static Groove decode(const uint8_t *b, size_t n) {
    Groove g;
    if (n < 2 || b[0] != 1 || b[1] > 64 || n != size_t(2 + 3 * b[1]))
      return g;
    for (int i = 0; i < b[1]; i++) {
      const int t = b[2 + 3 * i] + 256 * b[3 + 3 * i], v = b[4 + 3 * i];
      if (t >= 4096 || (i && t <= g.ticks[i - 1]) || v < 1 || v > 127)
        return {};
      g.add(t, v);
    }
    return g;
  }

public:
  RhythmImprint()
      : Plugin(performance::info("Rhythm Imprint",
                                 MPC_FOURCC('F', 'g', 'R', 'i'))) {
    addParam(mpc::boolParam("learn", "Learn", false));
    addParam(mpc::floatParam("depth", "Depth", 0, 100, 80, "%", 0));
    addParam(mpc::logParam("release", "Release", 20, 1000, 155, "ms", 0));
    addParam(mpc::floatParam("sense", "Sensitivity", 0, 100, 70, "%", 0));
    addParam(mpc::choiceParam(
        "source", "Groove", {"Learned", "Slot 1", "Slot 2", "Slot 3", "Slot 4"},
        0));
    // Keep the path instance-local. The SDK cached string's destructor may
    // otherwise run after a Zig-built native plugin has been unloaded.
    const auto folder = mpc::detail::computePluginFolder();
    for (int j = 0; j < 4; j++) {
      const auto path =
          folder + "/Content/slot-" + std::to_string(j + 1) + ".gri";
      if (auto *file = std::fopen(path.c_str(), "rb")) {
        std::array<uint8_t, 195> bytes{};
        const auto size = std::fread(bytes.data(), 1, bytes.size(), file);
        std::fclose(file);
        files[j] = decode(bytes.data(), size);
      }
    }
    for (int t : {0, 768, 1536, 2048, 2816, 3584})
      saved.add(t, t % 2048 == 0 ? 127 : 78);
    live = saved;
    addProgram("Learn a bar", {0, 85, 155, 70, 0});
    for (int i = 1; i <= 4; i++)
      addProgram(("Groove slot " + std::to_string(i)).c_str(),
                 {0, 88, 145, 70, float(i)});
  }
  void reset() override {
    detector = {};
    last = -1;
    cursor = measure = 0;
    peakIndex = -1;
    env = 0;
    gain = 1;
    armed = recording = pending = running = false;
    wasLearn = false;
  }
  void process(mpc::ProcessContext &c) override {
    // A UI preset save/load may briefly hold this lock. Audio never waits for
    // it.
    if (state.try_lock()) {
      if (version != seen) {
        live = saved;
        seen = version;
        pending = false;
        last = -1;
      } else if (pending) {
        saved = live;
        seen = ++version;
        pending = false;
      }
      state.unlock();
    }
    const bool learn = getBool(0);
    const bool play = c.transport.playing && c.transport.ppqValid &&
                      c.transport.tempoValid &&
                      std::isfinite(c.transport.ppqPos) &&
                      std::isfinite(c.transport.bpm) && c.transport.bpm > 0;
    const double start = play ? c.transport.ppqPos : 0.;
    const double step = play ? c.transport.bpm / (60 * c.sampleRate) : 0.;
    const bool wrapped =
        c.transport.cycling &&
        std::abs(c.transport.ppqPos - c.transport.cycleStartPpq) < .03 &&
        std::abs(expected - c.transport.cycleEndPpq) < .03 &&
        std::abs(std::remainder(
            c.transport.cycleEndPpq - c.transport.cycleStartPpq, 4.)) < .001;
    if (!play || (running && std::abs(expected - c.transport.ppqPos) > .025 &&
                  !wrapped)) {
      recording = false;
      armed = learn;
      last = -1;
      env = 0;
      detector = {};
    }
    if (learn && !wasLearn)
      armed = true;
    if (!learn)
      armed = recording = false;
    wasLearn = learn;
    running = play;
    expected = start + step * c.numFrames;
    const int source = getInt(4);
    const double release = std::exp(-1 / (get(2) * .001 * c.sampleRate));
    const double fall = std::exp(-1 / (.007 * c.sampleRate)),
                 floor = performance::threshold(get(3));
    const double smooth = -std::expm1(-1 / (.002 * c.sampleRate)),
                 depth = get(1) * .01;
    for (int i = 0; i < c.numFrames; i++) {
      const float l = c.inputs[0][i], r = c.inputs[1][i];
      const double ppq = start + i * step;
      const int tick =
          int(std::floor((ppq - 4 * std::floor(ppq / 4)) * 1024 + 1e-8)) % 4096;
      const bool edge = play && (last > tick || (last < 0 && tick == 0));
      if (edge && recording) {
        if (draft.size) {
          const int max = *std::max_element(draft.levels.begin(),
                                            draft.levels.begin() + draft.size);
          for (int j = 0; j < draft.size; j++)
            draft.levels[j] = std::max(1, 127 * draft.levels[j] / max);
          live = draft;
          pending = true;
          if (state.try_lock()) {
            saved = live;
            seen = ++version;
            pending = false;
            state.unlock();
          }
        }
        recording = false;
      }
      if (edge && armed) {
        draft = {};
        detector = {};
        armed = false;
        recording = true;
        measure = 0;
        peakIndex = -1;
      }
      const double amplitude = std::max(std::abs(l), std::abs(r));
      if (recording) {
        if (detector.tick(amplitude, floor, fall, int(.024 * c.sampleRate)) &&
            draft.size < 64) {
          draft.add(tick, 1);
          peakIndex = draft.size - 1;
          measure = std::max(1, int(.009 * c.sampleRate));
        }
        if (measure > 0 && peakIndex >= 0) {
          draft.levels[peakIndex] =
              std::max(draft.levels[peakIndex],
                       std::clamp(int(127 * amplitude + .5), 1, 127));
          --measure;
        }
      }
      const auto &groove = source ? files[source - 1] : live;
      if (play) {
        if (edge || last < 0 || source != lastSource) {
          cursor = 0;
          if (!edge)
            while (cursor < groove.size && groove.ticks[cursor] < tick)
              ++cursor;
        }
        env *= release;
        while (cursor < groove.size && groove.ticks[cursor] <= tick)
          env = groove.levels[cursor++] / 127.;
        last = tick;
      }
      lastSource = source;
      const double target =
          (!play || learn || !groove.size) ? 1 : 1 - depth + depth * env;
      gain += (target - gain) * smooth;
      c.outputs[0][i] = l * gain;
      c.outputs[1][i] = r * gain;
    }
  }
  void saveExtraState(std::vector<uint8_t> &bytes) override {
    std::lock_guard<std::mutex> lock(state);
    bytes.push_back(1);
    bytes.push_back(uint8_t(saved.size));
    for (int i = 0; i < saved.size; i++) {
      bytes.push_back(uint8_t(saved.ticks[i]));
      bytes.push_back(uint8_t(saved.ticks[i] >> 8));
      bytes.push_back(uint8_t(saved.levels[i]));
    }
  }
  void loadExtraState(const uint8_t *bytes, size_t n) override {
    const auto groove = decode(bytes, n);
    if (!groove.size)
      return;
    std::lock_guard<std::mutex> lock(state);
    saved = groove;
    ++version;
  }

private:
  int lastSource = -1;
};
MPC_PLUGIN_ENTRY(RhythmImprint)
