#!/usr/bin/env python3
"""Play MIDI files to a hardware MIDI device (default: Roland FP-10)."""

import argparse
import sys
import time

import mido

DEFAULT_MATCH = ("fp-10", "fp10", "roland", "digital piano")


def pick_port(hint):
    ports = mido.get_output_names()
    if not ports:
        sys.exit(
            "No MIDI output ports found.\n"
            "  - USB: connect the FP-10's 'Computer' (USB-B) port to the Mac.\n"
            "  - Bluetooth: Audio MIDI Setup > Window > Show MIDI Studio > "
            "Bluetooth icon > Connect next to the FP-10."
        )
    for needle in ((hint.lower(),) if hint else DEFAULT_MATCH):
        for p in ports:
            if needle in p.lower():
                return p
    if hint:
        sys.exit(f"No port matching {hint!r}. Available: {ports}")
    print(f"No Roland port found; falling back to {ports[0]!r}", file=sys.stderr)
    return ports[0]


def silence(out, active):
    """Kill anything still ringing, then release the sustain pedal."""
    for ch, note in active:
        out.send(mido.Message("note_off", channel=ch, note=note))
    for ch in range(16):
        out.send(mido.Message("control_change", channel=ch, control=123, value=0))
        out.send(mido.Message("control_change", channel=ch, control=64, value=0))
    time.sleep(0.1)


def play(path, out, transpose=0, speed=1.0, channel=None):
    mid = mido.MidiFile(path)
    print(f"{path}  ({mid.length / speed:.1f}s)")
    active = set()
    # Absolute scheduling off a monotonic clock, so per-message send latency
    # doesn't accumulate into a dragging tempo.
    start = time.monotonic()
    elapsed = 0.0
    try:
        for msg in mid:
            elapsed += msg.time / speed
            drift = start + elapsed - time.monotonic()
            if drift > 0:
                time.sleep(drift)
            if msg.is_meta:
                continue
            if msg.type in ("note_on", "note_off"):
                msg = msg.copy(note=max(0, min(127, msg.note + transpose)))
                if channel is not None:
                    msg = msg.copy(channel=channel)
                if msg.type == "note_on" and msg.velocity > 0:
                    active.add((msg.channel, msg.note))
                else:
                    active.discard((msg.channel, msg.note))
            out.send(msg)
    except KeyboardInterrupt:
        print("\nstopped")
        silence(out, active)
        raise
    silence(out, active)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", help=".mid files to play in order")
    ap.add_argument("-l", "--list", action="store_true", help="list MIDI ports and exit")
    ap.add_argument("-p", "--port", help="substring of the output port name")
    ap.add_argument("-t", "--transpose", type=int, default=0, help="semitones")
    ap.add_argument("-s", "--speed", type=float, default=1.0, help="tempo multiplier")
    ap.add_argument("-c", "--channel", type=int, help="force all notes onto this channel (0-15)")
    args = ap.parse_args()

    if args.list:
        for label, ports in (("Outputs", mido.get_output_names()),
                             ("Inputs", mido.get_input_names())):
            print(f"{label}:")
            for p in ports or ["  (none)"]:
                print(f"  {p}" if ports else p)
        return

    if not args.files:
        ap.error("give at least one .mid file (or --list)")

    port = pick_port(args.port)
    print(f"-> {port}")
    with mido.open_output(port) as out:
        try:
            for f in args.files:
                play(f, out, args.transpose, args.speed, args.channel)
        except KeyboardInterrupt:
            sys.exit(130)


if __name__ == "__main__":
    main()
