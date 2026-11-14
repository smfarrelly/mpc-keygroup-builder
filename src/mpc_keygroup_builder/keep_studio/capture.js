// Transport-independent MIDI capture. Times are seconds until a take is kept.
"use strict";
const Capture = (() => {
  const PPQ = 960,
    END = 16 * PPQ;
  function state() {
    return { held: new Map(), ringing: new Map(), pedal: 0 };
  }
  function apply(s, [, status, key, value]) {
    if (status === 176) {
      s.pedal = value;
      if (value < 64) s.ringing.clear();
    } else if (status === 144) {
      s.held.set(key, value);
      s.ringing.delete(key);
    } else if (s.held.has(key)) {
      if (s.pedal >= 64) s.ringing.set(key, s.held.get(key));
      s.held.delete(key);
    }
  }
  // Fold old input into a checkpoint so held notes survive long idle periods.
  class History {
    constructor() {
      this.base = state();
      this.events = [];
      this.floor = -Infinity;
    }
    prune(before) {
      let n = 0;
      while (n < this.events.length && this.events[n][0] < before)
        apply(this.base, this.events[n++]);
      if (n) this.events.splice(0, n);
      this.floor = Math.max(this.floor, before);
    }
    add(event) {
      this.events.push(event);
    }
    phrase(now) {
      const s = {
        held: new Map(this.base.held),
        ringing: new Map(this.base.ringing),
        pedal: this.base.pedal,
      };
      const sounding = () => s.held.size + s.ringing.size;
      let start = sounding() ? this.floor : null,
        end = null;
      for (const event of this.events) {
        const before = sounding();
        if (
          event[1] === 144 &&
          (start === null || (!before && end !== null && event[0] - end >= 2))
        )
          start = event[0];
        apply(s, event);
        if (before && !sounding()) end = event[0];
      }
      if (start === null) throw Error("No recent notes on this instrument.");
      return [start, sounding() ? now : Math.min(now, (end ?? now) + 0.06)];
    }
    slice(start, end, drum = false) {
      if (start < this.floor || !(end > start))
        throw Error("That interval is outside the capture history.");
      const s = {
        held: new Map(this.base.held),
        ringing: new Map(this.base.ringing),
        pedal: this.base.pedal,
      };
      const out = [];
      for (const event of this.events) {
        if (event[0] >= start) break;
        apply(s, event);
      }
      if (!drum) {
        if (s.pedal) out.push([0, 176, 64, s.pedal]);
        for (const [k, v] of s.ringing)
          out.push([0, 144, k, v], [0, 128, k, 0]);
        for (const [k, v] of s.held) out.push([0, 144, k, v]);
      } else {
        s.held.clear();
        s.ringing.clear();
        s.pedal = 0;
      }
      for (const event of this.events) {
        if (event[0] < start) continue;
        if (event[0] >= end) break;
        const [, status, key, value] = event;
        if (drum && (status === 176 || (status === 128 && !s.held.has(key))))
          continue;
        const tick = Math.min(
          END - 1,
          Math.round(((event[0] - start) * END) / (end - start)),
        );
        out.push([tick, status, key, value]);
        apply(s, event);
      }
      for (const key of s.held.keys()) out.push([END, 128, key, 0]);
      if (s.pedal) out.push([END, 176, 64, 0]);
      return out;
    }
  }
  // Make a seconds-independent note list for audition and XPJ. MIDI and take
  // files separately retain the original key-up and pedal positions.
  function notes(events, strength = 0) {
    const down = new Map(),
      ringing = new Map(),
      result = [];
    let pedal = false;
    function finish(map, k, t) {
      const n = map.get(k);
      if (!n) return;
      n.end = Math.max(n.start + 1, t);
      result.push(n);
      map.delete(k);
    }
    for (const [t, s, k, v] of events) {
      if (s === 176) {
        pedal = v >= 64;
        if (!pedal)
          for (const key of [...ringing.keys()]) finish(ringing, key, t);
      }
      if (s === 144) {
        finish(down, k, t);
        finish(ringing, k, t);
        down.set(k, { start: t, key: k, velocity: v });
      }
      if (s === 128 && down.has(k)) {
        if (pedal) {
          ringing.set(k, down.get(k));
          down.delete(k);
        } else finish(down, k, t);
      }
    }
    for (const map of [down, ringing])
      for (const k of [...map.keys()]) finish(map, k, END);
    for (const n of result) {
      const old = n.start;
      n.start = Math.min(
        END - 1,
        Math.max(
          0,
          Math.round(old + (Math.round(old / 240) * 240 - old) * strength),
        ),
      );
      n.end = Math.min(END, Math.max(n.start + 1, n.end + n.start - old));
    }
    return result.sort((a, b) => a.start - b.start);
  }
  function window4(now, tempo, anchor = null) {
    const bar = 240 / tempo;
    if (anchor === null) {
      const end = Math.floor(now / bar) * bar;
      return [end - 4 * bar, end];
    }
    const end = anchor + Math.floor((now - anchor) / (4 * bar)) * 4 * bar;
    return [end - 4 * bar, end];
  }
  // Rotate a rolling overdub back into the existing loop's musical phase.
  function aligned(history, start, end, anchor, drum) {
    const length = end - start,
      split = anchor + Math.ceil((start - anchor) / length - 1e-8) * length;
    if (split <= start + 1e-7 || split >= end - 1e-7)
      return history.slice(start, end, drum);
    const join = Math.round(((end - split) / length) * END);
    const segment = (a, b, from, to) =>
      history.slice(a, b, drum).map(([tick, ...m]) => {
        const t = from + Math.round((tick / END) * (to - from));
        return [m[0] === 144 ? Math.min(to - 1, t) : t, ...m];
      });
    return [
      ...segment(split, end, 0, join),
      ...segment(start, split, join, END),
    ];
  }
  return { History, notes, aligned, window4, END, PPQ };
})();
if (typeof module !== "undefined") module.exports = Capture;
