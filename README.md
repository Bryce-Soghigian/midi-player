# midi-player

Play MIDI files on a hardware digital piano from the command line on macOS.
Written for a **Roland FP-10**, but works with any class-compliant MIDI device.

## Setup

```sh
./setup.sh          # venv + mido/python-rtmidi
./fetch-music.sh    # download a set of public-domain piano pieces
```

## Connecting the piano

**USB** — cable from the piano's `Computer` (USB-B) port to the Mac. Class
compliant, no drivers. It appears in Audio MIDI Setup on its own.

**Bluetooth** — on the FP-10, hold `Function` + the lowest `A` key to enter
pairing mode. Then pair it in **Audio MIDI Setup → Window → Show MIDI Studio →
Bluetooth → Connect**.

> Pairing from System Settings → Bluetooth does **not** work for BLE MIDI. The
> piano will keep showing as unpaired there and that's expected.
>
> Likewise, `Add Device` in MIDI Studio just creates an inert placeholder for a
> MIDI-DIN device. It never produces a usable port. If your device shows with
> "Device is online" unchecked, that's a placeholder, not real hardware.

Confirm with `./play --list`.

## Usage

```sh
./play --list                        # list MIDI ports
./play song.mid                      # play
./play music/*.mid                   # play everything in order
./play song.mid -s 0.7               # 70% speed, for playing along
./play song.mid -t -12               # transpose down an octave
./play song.mid -p "FP-10"           # pick a port by substring
./play song.mid -c 0                 # force all notes onto channel 0
```

Filenames resolve against the script's own directory as a fallback, so it works
from any working directory:

```sh
~/midi-player/play music/clair-de-lune.mid    # from anywhere
~/midi-player/play clair-de-lune.mid          # bare name, found in music/
```

Ctrl-C stops and sends note-off for every sounding note plus all-notes-off and
sustain-pedal-up on all 16 channels, so nothing is left ringing.

## Practice mode

`practice` loops bar ranges, isolates hands, and can replace a recording's
rubato with a steady tempo you can actually play along to.

```sh
./practice song.mid --info                     # bar count and note distribution
./practice song.mid --bars 28-44               # loop a section
./practice song.mid --bars 28-44 --hand left   # one hand
./practice song.mid --bars 1-8 --bpm 50        # steady 50 bpm, no rubato
./practice song.mid --bars 1-8 --loop 0        # repeat until Ctrl-C
./practice song.mid --bars 1-8 --loop 5 --rest 2
./practice song.mid --bars 1-8 --split 55      # override the hand split
```

Hands are separated by a per-bar split point chosen by weighted 1-D 2-means
over that bar's pitches, rather than a fixed note. A fixed split breaks on
music that puts both hands in one register, and splitting on the widest pitch
gap breaks whenever an accompaniment figure sits closer to the melody than to
the bass. Pass `--split <note>` to force a fixed one.

`--bpm` ignores the file's tempo map entirely. Recorded performances encode
their rubato as tempo changes -- this prelude has over 80 of them -- which is
what you want to listen to and the opposite of what you want to practise with.

## Scales

`scale` generates a scale as a MIDI file: one note per beat, up then down,
hands together with the left an octave below the right. Steady by design --
it is a reference to play against, not a performance.

```sh
./scale D                        # music/d-major.mid
./scale Db                       # five flats, for the Consolation/Clair de Lune key
./scale D --bpm 72               # faster once it is solid
./scale D -O 2                   # two octaves
./scale D -H right               # one hand
./scale A -m harmonic-minor      # also natural-minor
```

Degrees are spelled on consecutive letters, so D major prints `F#` rather than
`Gb` and F# harmonic minor prints `E#`. Output lands in `music/`, which is
gitignored -- regenerate rather than keep the files around.

The closing tonic is held to the end of its bar, so a scale is always a whole
number of bars and `practice --bars` lines up with it:

```sh
./practice d-major.mid --bars 1-2 --loop 0     # first half, until Ctrl-C
./practice d-major.mid --hand right --bpm 50   # thumb-under, slow
```

For multi-octave scales prefer `./scale D -O 2 -H right` over `practice --hand
right`: past one octave the two hands overlap in pitch, and the splitter has
only pitch to go on.

## Notes

Timing is scheduled against an absolute monotonic clock rather than by sleeping
per-message delta, so per-send latency doesn't accumulate into a dragging tempo.

Bluetooth MIDI has meaningfully more jitter and less throughput than USB. Dense
passages with many simultaneous note-ons may smear or drop notes over BLE. Use
USB if that matters.

## Music

`fetch-music.sh` also pulls the engraved score for the Raindrop Prelude into
`scores/`, for reading alongside practice mode.

It pulls 16 solo piano pieces from
[mfiles.co.uk](https://www.mfiles.co.uk/classical-midi.htm). The compositions
are public domain; the MIDI sequences are mfiles' own work, offered free for
personal use, so they are **not** redistributed here — the script downloads
them to `music/`, which is gitignored.
