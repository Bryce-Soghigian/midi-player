#!/usr/bin/env python3
"""Practice driver: loop bar ranges, isolate hands, and play at a steady tempo.

Recorded MIDI performances carry heavy rubato, which makes them useless to play
along with. --bpm discards the file's tempo map and gives you a metronomic
reference instead.
"""

import argparse
import math
import os
import sys
import time

import mido

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MATCH = ("fp-10", "fp10", "roland", "digital piano")


def resolve(path):
    if os.path.exists(path):
        return path
    for cand in (os.path.join(HERE, path), os.path.join(HERE, "music", path)):
        if os.path.exists(cand):
            return cand
    sys.exit(f"No such MIDI file: {path}")


def pick_port(hint):
    ports = mido.get_output_names()
    if not ports:
        sys.exit("No MIDI output ports found. Connect the piano and retry.")
    for needle in ((hint.lower(),) if hint else DEFAULT_MATCH):
        for p in ports:
            if needle in p.lower():
                return p
    sys.exit(f"No port matching {hint!r}. Available: {ports}")


def extract(path):
    """Flatten to (start_tick, end_tick, note, velocity) plus sustain events."""
    mid = mido.MidiFile(path)
    tpb = mid.ticks_per_beat
    sounding, notes, pedal = {}, [], []
    tick = 0
    for msg in mido.merge_tracks(mid.tracks):
        tick += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            sounding.setdefault(msg.note, []).append((tick, msg.velocity))
        elif msg.type in ("note_off", "note_on"):
            stack = sounding.get(msg.note)
            if stack:
                start, vel = stack.pop(0)
                notes.append((start, tick, msg.note, vel))
        elif msg.type == "control_change" and msg.control == 64:
            pedal.append((tick, msg.value))
    for note, stack in sounding.items():           # unterminated: ring one beat
        for start, vel in stack:
            notes.append((start, start + tpb, note, vel))
    notes.sort()
    return notes, pedal, tpb, mid


def auto_splits(notes, bar_ticks):
    """Per-bar hand split via weighted 1-D 2-means over the bar's pitches.

    A fixed split fails on music that moves both hands into one register -- in
    this prelude's C-sharp minor middle section the right hand's repeated
    G-sharp sits at MIDI 56, below middle C, so a fixed split at 60 discards
    the entire right-hand part. Splitting on the largest pitch gap fails too:
    in the opening the gap from the bass note up to the repeated A-flat is
    wider than the one from that A-flat up to the melody, which strands the
    accompaniment in the wrong hand. Minimising within-cluster variance, with
    each pitch weighted by how often it sounds, tracks the two hands far more
    closely, since a repeated accompaniment note pulls its own cluster.
    """
    by_bar = {}
    for start, _, note, _ in notes:
        by_bar.setdefault(int(start // bar_ticks), []).append(note)

    splits, last = {}, 60.0
    for bar in sorted(by_bar):
        counts = {}
        for n in by_bar[bar]:
            counts[n] = counts.get(n, 0) + 1
        pitches = sorted(counts)
        if len(pitches) < 2:
            splits[bar] = last
            continue
        best, best_cost = None, float("inf")
        for i in range(1, len(pitches)):
            cost = 0.0
            for group in (pitches[:i], pitches[i:]):
                w = sum(counts[n] for n in group)
                mean = sum(n * counts[n] for n in group) / w
                cost += sum(counts[n] * (n - mean) ** 2 for n in group)
            if cost < best_cost:
                best, best_cost = (pitches[i - 1] + pitches[i]) / 2, cost
        splits[bar] = last = best
    return splits


def split_for(splits, tick, bar_ticks, fallback):
    if not splits:
        return fallback
    bar = int(tick // bar_ticks)
    if bar in splits:
        return splits[bar]
    near = min(splits, key=lambda b: abs(b - bar))
    return splits[near]


def beats_per_bar(mid):
    for track in mid.tracks:
        for msg in track:
            if msg.type == "time_signature":
                return msg.numerator * 4 / msg.denominator
    return 4.0


def tempo_map(mid):
    """[(tick, tempo_us_per_beat)] in absolute ticks."""
    changes, tick = [], 0
    for msg in mido.merge_tracks(mid.tracks):
        tick += msg.time
        if msg.type == "set_tempo":
            changes.append((tick, msg.tempo))
    return changes or [(0, 500000)]


def make_clock(mid, tpb, bpm):
    """tick -> seconds. Fixed bpm, or the file's own (rubato) tempo map."""
    if bpm:
        spt = 60.0 / bpm / tpb
        return lambda t: t * spt

    changes = tempo_map(mid)
    marks, secs, prev_tick, prev_tempo = [], 0.0, 0, changes[0][1]
    for tick, tempo in changes:
        secs += (tick - prev_tick) * prev_tempo / 1e6 / tpb
        marks.append((tick, secs, tempo))
        prev_tick, prev_tempo = tick, tempo

    def at(t):
        lo = 0
        for i, (tick, _, _) in enumerate(marks):
            if tick <= t:
                lo = i
            else:
                break
        tick, base, tempo = marks[lo]
        return base + (t - tick) * tempo / 1e6 / tpb

    return at


def play_window(out, notes, pedal, clock, lo, hi, speed, count_in_secs):
    """Emit one pass of the tick window [lo, hi). Returns True if interrupted."""
    events = []
    for start, end, note, vel in notes:
        if lo <= start < hi:
            events.append((start, mido.Message("note_on", note=note, velocity=vel)))
            events.append((min(end, hi), mido.Message("note_off", note=note)))
    for tick, value in pedal:
        if lo <= tick < hi:
            events.append((tick, mido.Message("control_change", control=64, value=value)))
    events.sort(key=lambda e: e[0])

    origin = clock(lo)
    start_wall = time.monotonic() + count_in_secs
    active = set()
    try:
        for tick, msg in events:
            due = start_wall + (clock(tick) - origin) / speed
            gap = due - time.monotonic()
            if gap > 0:
                time.sleep(gap)
            if msg.type == "note_on":
                active.add(msg.note)
            elif msg.type == "note_off":
                active.discard(msg.note)
            out.send(msg)
        tail = start_wall + (clock(hi) - origin) / speed - time.monotonic()
        if tail > 0:
            time.sleep(tail)
    except KeyboardInterrupt:
        return True
    finally:
        for note in active:
            out.send(mido.Message("note_off", note=note))
        out.send(mido.Message("control_change", control=64, value=0))
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("-b", "--bars", help="bar range, 1-indexed and inclusive, e.g. 28-44")
    ap.add_argument("-H", "--hand", choices=("left", "right", "both"), default="both")
    ap.add_argument("-S", "--split", default="auto",
                    help="hand split: 'auto' (per-bar, default) or a MIDI note number")
    ap.add_argument("--bpm", type=float, help="steady tempo; discards the file's rubato")
    ap.add_argument("-s", "--speed", type=float, default=1.0, help="tempo multiplier")
    ap.add_argument("-n", "--loop", type=int, default=1, help="repetitions (0 = forever)")
    ap.add_argument("-r", "--rest", type=float, default=1.5, help="seconds between reps")
    ap.add_argument("-c", "--count-in", type=int, default=0, help="count-in beats")
    ap.add_argument("-p", "--port")
    ap.add_argument("--info", action="store_true", help="print bar/section summary and exit")
    args = ap.parse_args()

    path = resolve(args.file)
    notes, pedal, tpb, mid = extract(path)
    bpb = beats_per_bar(mid)
    bar_ticks = bpb * tpb
    total_bars = math.ceil(max(n[1] for n in notes) / bar_ticks)

    if args.info:
        print(f"{os.path.basename(path)}: {total_bars} bars, {bpb:g} beats/bar, "
              f"{len(notes)} notes")
        splits = auto_splits(notes, bar_ticks)
        lows = sum(1 for n in notes
                   if n[2] < split_for(splits, n[0], bar_ticks, 60))
        print(f"  auto hand split -> LH {lows}  RH {len(notes) - lows}")
        return

    if args.bars:
        try:
            first, last = (int(x) for x in args.bars.split("-"))
        except ValueError:
            sys.exit("--bars wants a range like 28-44")
        lo, hi = int((first - 1) * bar_ticks), int(last * bar_ticks)
    else:
        first, last = 1, total_bars
        lo, hi = 0, int(total_bars * bar_ticks)

    if args.hand != "both":
        if args.split == "auto":
            splits, fallback = auto_splits(notes, bar_ticks), 60
        else:
            splits, fallback = {}, int(args.split)
        keep_low = args.hand == "left"
        notes = [n for n in notes
                 if (n[2] < split_for(splits, n[0], bar_ticks, fallback)) == keep_low]
    if not any(lo <= n[0] < hi for n in notes):
        sys.exit(f"No {args.hand}-hand notes in bars {first}-{last}.")

    clock = make_clock(mid, tpb, args.bpm)
    span = (clock(hi) - clock(lo)) / args.speed
    beat_secs = (60.0 / args.bpm if args.bpm else (clock(hi) - clock(lo)) /
                 max(1, (hi - lo) / tpb)) / args.speed
    count_in = args.count_in * beat_secs

    port = pick_port(args.port)
    tempo_desc = f"{args.bpm:g} bpm steady" if args.bpm else "original rubato"
    print(f"{os.path.basename(path)}  bars {first}-{last}  {args.hand} hand  "
          f"{tempo_desc}  x{args.speed}  ({span:.1f}s/rep)  -> {port}")

    with mido.open_output(port) as out:
        rep = 0
        while args.loop == 0 or rep < args.loop:
            rep += 1
            label = f"  rep {rep}" + (f"/{args.loop}" if args.loop else "")
            print(label, flush=True)
            if count_in:
                print(f"    count-in {args.count_in} beats...", flush=True)
            if play_window(out, notes, pedal, clock, lo, hi, args.speed, count_in):
                print("\nstopped")
                break
            if args.loop == 0 or rep < args.loop:
                try:
                    time.sleep(args.rest)
                except KeyboardInterrupt:
                    print("\nstopped")
                    break
        for ch in range(16):
            out.send(mido.Message("control_change", channel=ch, control=123, value=0))
            out.send(mido.Message("control_change", channel=ch, control=64, value=0))
        time.sleep(0.1)


if __name__ == "__main__":
    main()
