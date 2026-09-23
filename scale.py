#!/usr/bin/env python3
"""Generate scale MIDI files to practise along with.

One note per beat, ascending then descending, at a fixed tempo -- the point is
a steady reference to play against, so there is deliberately no rubato here.
The closing tonic is held out to the end of its bar so that bar ranges in
practice.py line up with the scale.
"""

import argparse
import os
import sys

import mido

HERE = os.path.dirname(os.path.abspath(__file__))

LETTERS = "CDEFGAB"
NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

MODES = {
    "major":          (0, 2, 4, 5, 7, 9, 11, 12),
    "natural-minor":  (0, 2, 3, 5, 7, 8, 10, 12),
    "harmonic-minor": (0, 2, 3, 5, 7, 8, 11, 12),
}

BEATS_PER_BAR = 4
TICKS_PER_BEAT = 480


def parse_tonic(name):
    """'D', 'Db', 'F#' -> pitch class 0-11."""
    text = name.strip()
    if not text or text[0].upper() not in NATURAL:
        sys.exit(f"Bad tonic {name!r}: want a letter A-G, optionally with # or b.")
    pc = NATURAL[text[0].upper()]
    for accidental in text[1:]:
        if accidental in "#♯":
            pc += 1
        elif accidental in "b♭":
            pc -= 1
        else:
            sys.exit(f"Bad accidental {accidental!r} in {name!r}.")
    return pc % 12


def scale_notes(pc, mode, octaves):
    """Right-hand notes, up then down, with the tonic at or above middle C."""
    steps = MODES[mode]
    root = 60 + pc
    up = [root + 12 * o + s for o in range(octaves) for s in steps[:-1]]
    up.append(root + 12 * octaves)
    return up + up[-2::-1]


def spell(tonic, notes):
    """Name each degree on its own letter, so D major reads F#, not Gb."""
    start = LETTERS.index(tonic[0].upper())
    names = []
    for i, note in enumerate(notes):
        letter = LETTERS[(start + i) % 7]
        delta = (note - NATURAL[letter]) % 12
        if delta > 6:
            delta -= 12
        names.append(letter + ("♯" * delta if delta > 0 else "♭" * -delta))
    return names


def build(notes, bpm, hands, velocity=80):
    mid = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm)))
    track.append(mido.MetaMessage("time_signature", numerator=BEATS_PER_BAR, denominator=4))

    # Hold the closing tonic to the end of its bar, so bar ranges stay whole.
    tail = BEATS_PER_BAR - ((len(notes) - 1) % BEATS_PER_BAR)

    for i, note in enumerate(notes):
        beats = tail if i == len(notes) - 1 else 1
        voices = []
        if hands in ("both", "right"):
            voices.append(note)
        if hands in ("both", "left"):
            voices.append(note - 12)
        for n in voices:
            track.append(mido.Message("note_on", note=n, velocity=velocity, time=0))
        for j, n in enumerate(voices):
            track.append(mido.Message("note_off", note=n,
                                      time=beats * TICKS_PER_BEAT if j == 0 else 0))
    return mid


def default_name(tonic, mode, octaves, hands):
    stem = tonic[0].lower()
    for accidental in tonic[1:]:
        stem += "-sharp" if accidental in "#♯" else "-flat"
    parts = [stem, mode]
    if octaves > 1:
        parts.append(f"{octaves}oct")
    if hands != "both":
        parts.append(hands)
    return "-".join(parts) + ".mid"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tonic", help="scale to build on, e.g. D, Db, F#")
    ap.add_argument("-m", "--mode", choices=sorted(MODES), default="major")
    ap.add_argument("-O", "--octaves", type=int, default=1)
    ap.add_argument("--bpm", type=float, default=60, help="one note per beat")
    ap.add_argument("-H", "--hands", choices=("both", "right", "left"), default="both",
                    help="'both' puts the left hand an octave below the right")
    ap.add_argument("-o", "--out", help="output path (default: music/<name>.mid)")
    args = ap.parse_args()

    if args.octaves < 1:
        sys.exit("--octaves wants at least 1")

    notes = scale_notes(parse_tonic(args.tonic), args.mode, args.octaves)
    mid = build(notes, args.bpm, args.hands)

    out = args.out or os.path.join(HERE, "music",
                                   default_name(args.tonic, args.mode,
                                                args.octaves, args.hands))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    mid.save(out)

    octave = notes[:len(MODES[args.mode])]
    print(f"{out}  ({mid.length:.1f}s)")
    print(f"  {' '.join(spell(args.tonic, octave))}")
    hands = "hands together" if args.hands == "both" else f"{args.hands} hand"
    print(f"  {len(notes)} notes, {hands}, {args.bpm:g} bpm")


if __name__ == "__main__":
    main()
