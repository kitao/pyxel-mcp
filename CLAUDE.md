# Pyxel App Development

## MCP Tools

- `run_and_capture` — Run a Pyxel script and see a screenshot of the result.
  - `frames`: number of frames to render before capturing (default: 60)
  - `scale`: screenshot scale multiplier (default: 2)
  - After writing or modifying code, always run_and_capture to verify the visual result.
- `pyxel_info` — Get Pyxel's installed location, examples path, and API stubs path.
  - Call this first to find where examples and API docs are on this system.
  - If Pyxel is not installed, guide the user to run `pip install pyxel`.
- `render_audio` — Render a Pyxel sound to WAV and analyze the waveform.
  - `sound_index`: sound slot to render, 0-63 (default: 0)
  - `duration_sec`: duration in seconds, 0 = auto-detect (default: 0)
  - Returns note sequence with timing, frequency, and volume analysis.
  - Use this to verify MML/sound output without listening. Run for each channel separately.

## Verification Workflows

### Graphics
1. Write/modify code
2. `run_and_capture` to see the visual result
3. Fix issues and re-capture until correct

### Audio
1. Define sounds via `Sound.mml()` or `Sound.set()`
2. `render_audio` for each sound slot to get note/frequency/volume analysis
3. Adjust and re-render until correct

### Input/Interaction
To test game logic that depends on input, temporarily replace input conditions
with frame-based triggers, then `run_and_capture` to verify:

```python
# Original:  if pyxel.btnp(pyxel.KEY_SPACE): jump()
# Test:      if pyxel.frame_count == 30: jump()
```

Capture at different frame counts to verify before/after states. Revert when done.

## Pyxel Documentation

- API reference (web): https://kitao.github.io/pyxel/wasm/api-reference/api-reference.json
- MML commands (web): https://kitao.github.io/pyxel/wasm/mml-studio/mml-commands.json
- API type stubs and examples: call `pyxel_info` to get local paths.

For API details, read the type stubs or fetch the API reference JSON.
For MML syntax, fetch the MML commands JSON. Use `Sound.mml()` to set sounds via MML.
For coding patterns, read the example scripts (01-18, 99).

## Resource Creation

Pyxel resources (sprites, tilemaps, sounds) can be created programmatically.
Write a script, run_and_capture to verify, then iterate.

### Image Banks (sprites/tiles)

```python
import pyxel
pyxel.init(128, 128)

# Set pixels with hex color strings (each char = palette index 0-f)
pyxel.images[0].set(0, 0, [
    "00011000",  # 8px wide sprite, row by row
    "00111100",
    "01111110",
    "11011011",
])

# Or load from PNG
pyxel.images[0].load(0, 0, "sprites.png")

# Draw to screen to verify
pyxel.cls(0)
pyxel.blt(0, 0, 0, 0, 0, 128, 128)  # Show entire image bank 0
pyxel.show()
```

### Tilemaps

```python
# Set tiles (each 2-char pair = tile coords in image bank)
pyxel.tilemaps[0].set(0, 0, [
    "0000010002000300",  # tiles at (0,0), (1,0), (2,0), (3,0)
])

# Draw tilemap to screen
pyxel.bltm(0, 0, 0, 0, 0, 128, 128)
```

### Sounds

```python
# Define sound with string notation
pyxel.sounds[0].set(
    notes="c2e2g2c3",    # notes
    tones="ssss",         # s=square, t=triangle, p=pulse, n=noise
    volumes="7654",       # 0-7
    effects="nnnn",       # n=none, s=slide, v=vibrato, f=fadeout
    speed=20,
)
```

### Save Resources

```python
pyxel.save("my_resource.pyxres")
```

### Color Palette

0:black 1:navy 2:purple 3:green 4:brown 5:dark_blue 6:light_blue 7:white
8:red 9:orange 10:yellow 11:lime 12:cyan 13:gray 14:pink 15:peach
