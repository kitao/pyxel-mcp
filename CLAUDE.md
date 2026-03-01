# Pyxel App Development

## MCP Tools

- `run_and_capture(script_path, frames=60, scale=2)` — Run script, capture screenshot.
- `capture_frames(script_path, frames="1,15,30,60", scale=2)` — Capture at multiple frames.
- `inspect_sprite(script_path, image=0, x, y, w=8, h=8)` — Read sprite pixels and report colors.
- `inspect_layout(script_path, frames=5)` — Analyze text positioning and layout balance.
- `render_audio(script_path, sound_index=0)` — Render sound to WAV, analyze notes and rhythm.
- `pyxel_info()` — Get paths to API stubs and example scripts. Call this first.

## Workflow

1. Call `pyxel_info` to locate API stubs and examples.
2. Read stubs for API details. Read examples for coding patterns (01-18, 99).
3. Write code.
4. Verify with tools:
   - `run_and_capture` after every visual change.
   - `render_audio` for each sound channel separately.
   - Other tools as needed for the task.
5. Fix and re-verify.

### Testing Input-Dependent Logic

Replace input conditions with frame-based triggers, capture, then revert:

```python
# Original:  if pyxel.btnp(pyxel.KEY_SPACE): jump()
# Test:      if pyxel.frame_count == 30: jump()
```

## Pyxel Reference

- API reference: https://kitao.github.io/pyxel/wasm/api-reference/api-reference.json
- MML commands: https://kitao.github.io/pyxel/wasm/mml-studio/mml-commands.json
- Local stubs and examples: call `pyxel_info`.

For API details, read the type stubs or fetch the API reference JSON.
For MML syntax, fetch the MML commands JSON. Use `Sound.mml()` to set sounds via MML.

## Resource Creation

Pyxel resources (sprites, tilemaps, sounds) can be created programmatically.
Write code, `run_and_capture` to verify, then iterate.

### Image Banks (sprites/tiles)

```python
# Set pixels with hex color strings (each char = palette index 0-f)
pyxel.images[0].set(0, 0, [
    "00011000",  # 8px wide sprite, row by row
    "00111100",
    "01111110",
    "11011011",
])
```

### Tilemaps

```python
# Each 2-char pair = tile coords in image bank
pyxel.tilemaps[0].set(0, 0, [
    "0000010002000300",  # tiles at (0,0), (1,0), (2,0), (3,0)
])
pyxel.bltm(0, 0, 0, 0, 0, 128, 128)  # draw tilemap
```

### Sounds

```python
pyxel.sounds[0].set(
    notes="c2e2g2c3",    # notes: [cdefgab][0-4], r=rest
    tones="ssss",         # t=triangle s=square p=pulse n=noise
    volumes="7654",       # 0-7
    effects="nnnn",       # n=none s=slide v=vibrato f=fadeout
    speed=20,
)
```

### Quick BGM

`pyxel.gen_bgm(preset, instr, seed)` generates MML strings for background music.

### Color Palette

0:black 1:navy 2:purple 3:green 4:brown 5:dark_blue 6:light_blue 7:white
8:red 9:orange 10(a):yellow 11(b):lime 12(c):cyan 13(d):gray 14(e):pink 15(f):peach

### Text Centering

```python
x = (pyxel.width - len(text) * 4) // 2
```
