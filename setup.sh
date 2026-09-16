#!/bin/sh
# Create the virtualenv and install MIDI dependencies.
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
echo "done. now run: ./play --list"
