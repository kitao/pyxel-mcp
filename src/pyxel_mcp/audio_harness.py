"""Audio rendering harness - runs a Pyxel script and exports sound to WAV.

Executes the script with game loop functions (run/show/flip) patched to
no-ops so that only sound definitions are processed. Then renders the
specified sound slot to a WAV file for offline analysis.

Usage:
    python audio_harness.py <script> <output.wav> <sound_index> [duration_sec]
"""

import json
import os
import runpy
import sys

if len(sys.argv) < 4:
    print(
        "Usage: audio_harness <script> <output.wav> <sound_index> [duration_sec]",
        file=sys.stderr,
    )
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
output_path = os.path.abspath(sys.argv[2])
sound_index = int(sys.argv[3])
duration_sec = float(sys.argv[4]) if len(sys.argv) > 4 else 0

sys.argv = [script_path]

import pyxel

# Patch game loop functions to no-ops (we only need sound setup)
pyxel.run = lambda update, draw: None
pyxel.show = lambda: None
pyxel.flip = lambda: None

# Execute the script to set up sounds
sys.path.insert(0, os.path.dirname(script_path))
try:
    runpy.run_path(script_path, run_name="__main__")
except SystemExit:
    pass

# Get the target sound
sound = pyxel.sounds[sound_index]

# Auto-detect duration if not specified
if duration_sec <= 0:
    try:
        total = sound.total_sec()
        duration_sec = (total + 0.5) if total else 5.0
    except Exception:
        duration_sec = 5.0

# Render to WAV
sound.save(output_path, duration_sec)

# Print metadata as JSON for the server
meta = {
    "duration_sec": duration_sec,
    "sound_index": sound_index,
    "speed": sound.speed,
    "num_notes": len(sound.notes),
}
print(json.dumps(meta))
