"""Audio rendering harness - runs a Pyxel script and exports sound/music to WAV.

Executes the script with game loop functions (run/show/flip) patched to
no-ops so that only sound definitions are processed. Then renders the
specified sound or music slot to a WAV file for offline analysis.

Usage:
    python audio_harness.py <script> <output.wav> <sound_index> [duration_sec] [music_index]
"""

import json
import os
import sys

if len(sys.argv) < 4:
    print(
        "Usage: audio_harness <script> <output.wav> <sound_index> [duration_sec] [music_index]",
        file=sys.stderr,
    )
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
output_path = os.path.abspath(sys.argv[2])
sound_index = int(sys.argv[3])
duration_sec = float(sys.argv[4]) if len(sys.argv) > 4 else 0
music_index = int(sys.argv[5]) if len(sys.argv) > 5 else -1

import pyxel

from pyxel_mcp._headless import noop_game_loop, run_script, setup_harness

setup_harness(script_path)
noop_game_loop()

# Execute the script to set up sounds
run_script(script_path)

if music_index >= 0:
    # Render music (all channels mixed)
    music = pyxel.musics[music_index]

    if duration_sec <= 0:
        duration_sec = 10.0

    music.save(output_path, duration_sec)

    num_channels = sum(1 for seq in music.seqs if seq)
    meta = {
        "duration_sec": duration_sec,
        "music_index": music_index,
        "num_channels": num_channels,
    }
else:
    # Render single sound
    sound = pyxel.sounds[sound_index]

    if duration_sec <= 0:
        try:
            total = sound.total_sec()
            duration_sec = (total + 0.5) if total else 5.0
        except Exception:
            duration_sec = 5.0

    sound.save(output_path, duration_sec)

    meta = {
        "duration_sec": duration_sec,
        "sound_index": sound_index,
        "speed": sound.speed,
        "num_notes": len(sound.notes),
    }

print(json.dumps(meta))
sys.stdout.flush()
