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

## Notes

Timing is scheduled against an absolute monotonic clock rather than by sleeping
per-message delta, so per-send latency doesn't accumulate into a dragging tempo.

Bluetooth MIDI has meaningfully more jitter and less throughput than USB. Dense
passages with many simultaneous note-ons may smear or drop notes over BLE. Use
USB if that matters.

## Music

`fetch-music.sh` pulls 16 solo piano pieces from
[mfiles.co.uk](https://www.mfiles.co.uk/classical-midi.htm). The compositions
are public domain; the MIDI sequences are mfiles' own work, offered free for
personal use, so they are **not** redistributed here — the script downloads
them to `music/`, which is gitignored.
