"""MCP server for Pyxel, a retro game engine for Python."""

import asyncio
import glob
import json
import math
import os
import shutil
import struct
import sys
import tempfile
import wave
from importlib.util import find_spec

from mcp.server.fastmcp import FastMCP, Image

HARNESS_PATH = os.path.join(os.path.dirname(__file__), "harness.py")
AUDIO_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "audio_harness.py")
SPRITE_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "sprite_harness.py")
FRAMES_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "frames_harness.py")
LAYOUT_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "layout_harness.py")

_MAX_STDERR = 4000


def _pyxel_dir():
    """Find installed Pyxel package directory (without importing Pyxel)."""
    try:
        spec = find_spec("pyxel")
        if spec:
            if spec.origin:
                return os.path.dirname(spec.origin)
            if spec.submodule_search_locations:
                return list(spec.submodule_search_locations)[0]
    except (ModuleNotFoundError, ValueError):
        pass
    return None


def _decode_stderr(stderr):
    """Decode subprocess stderr, truncating if too long."""
    if not stderr:
        return ""
    text = stderr.decode(errors="replace").strip()
    if len(text) > _MAX_STDERR:
        return text[:_MAX_STDERR] + "\n... (truncated)"
    return text


_INSTRUCTIONS = """\
# Pyxel App Development

## Workflow

1. Call `pyxel_info` to locate API stubs and examples.
2. Read stubs for API details. Read examples for coding patterns (01-18, 99).
3. Write code.
4. Verify with tools:
   - `run_and_capture` after every visual change.
   - `render_audio` for each sound channel separately.
   - Other tools as needed for the task.
5. Fix and re-verify.

### Error Recovery

- **`run_and_capture` timeout**: Script has an infinite loop or heavy computation. \
Check `update()`/`draw()` for blocking logic. Reduce `frames` parameter to test earlier.
- **`run_and_capture` black screen**: `cls()` called but nothing drawn, or drawing \
with the same color as background. Check draw coordinates are within screen bounds.
- **`render_audio` empty output**: Sound slot not populated. Verify the script calls \
`pyxel.sounds[N].set()` or `.mml()` before the game loop.
- **`inspect_sprite` all zeros**: Image bank not populated. Ensure `pyxel.images[N].set()` \
or `.load()` runs before the game loop starts.
- **`inspect_layout` no text detected**: Text may be too small, overlapping, or same \
color as background. Try a different frame number.

### Reading Tool Output

- **`run_and_capture`**: Returns a screenshot image. Visually verify layout, colors, \
and sprite positions.
- **`render_audio`**: Returns note sequence with timing/frequency. Check that notes \
match the intended melody and rhythm feels correct.
- **`inspect_sprite`**: Returns a pixel grid + symmetry report. Asymmetric pixels \
are listed by row — fix those coordinates in `images[N].set()`.
- **`inspect_layout`**: Returns text positions and horizontal balance ratio. \
Balance close to 1.0 = centered. Offset > 2px from center = likely misaligned.
- **`capture_frames`**: Returns multiple screenshots. Compare frames to verify \
animation progresses smoothly without jumps or flicker.

### Testing Input-Dependent Logic

Replace input conditions with frame-based triggers, capture, then revert:

```python
# Original:  if pyxel.btnp(pyxel.KEY_SPACE): jump()
# Test:      if pyxel.frame_count == 30: jump()
```

### Letting the User Play

When suggesting the user run a script directly, check for a virtual environment \
(`.venv/bin/python` or similar) and include the full path in the command. \
Users may not have Pyxel installed globally.

## Pyxel Reference

- API reference: https://kitao.github.io/pyxel/wasm/api-reference/api-reference.json
- MML commands: https://kitao.github.io/pyxel/wasm/mml-studio/mml-commands.json
- Local stubs and examples: call `pyxel_info`.

For API details, read the type stubs or fetch the API reference JSON.
For MML syntax, fetch the MML commands JSON.
User-created games for reference: https://github.com/kitao/pyxel/wiki/Pyxel-User-Examples

## App Structure

```python
# Class-based game (most common)
class App:
    def __init__(self):
        pyxel.init(160, 120, title="My Game")
        pyxel.load("my_resource.pyxres")  # optional: load .pyxres file
        pyxel.run(self.update, self.draw)
    def update(self):
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()
    def draw(self):
        pyxel.cls(0)
App()

# Static image (no game loop)
pyxel.init(160, 120)
pyxel.cls(1)
pyxel.circ(80, 60, 20, 8)
pyxel.show()
```

System variables: `pyxel.width`, `pyxel.height`, `pyxel.frame_count`.

## Coordinate System

Origin `(0, 0)` is the **top-left** corner. X increases rightward, Y increases downward.
Screen bounds: `0 <= x < pyxel.width`, `0 <= y < pyxel.height`.

## Drawing API

```
cls(col)                            clear screen
pset(x, y, col)                     draw pixel
line(x1, y1, x2, y2, col)          draw line
rect(x, y, w, h, col)              filled rectangle
rectb(x, y, w, h, col)             rectangle border
circ(x, y, r, col)                 filled circle
circb(x, y, r, col)                circle border
elli(x, y, w, h, col)              filled ellipse
ellib(x, y, w, h, col)             ellipse border
tri(x1, y1, x2, y2, x3, y3, col)  filled triangle
trib(x1, y1, x2, y2, x3, y3, col) triangle border
fill(x, y, col)                     flood fill
text(x, y, s, col)                  draw text (font: 4px wide, 6px tall)
blt(x, y, img, u, v, w, h, [colkey], [rotate], [scale])   sprite
bltm(x, y, tm, u, v, w, h, [colkey], [rotate], [scale])   tilemap
```

### Sprite Drawing (blt)

- `colkey`: transparent color index (e.g., `colkey=0` treats black as transparent)
- Negative `w` flips horizontally, negative `h` flips vertically
- `rotate`: rotation in degrees, `scale`: scaling factor
- Animation: `u = pyxel.frame_count // 4 % 2 * 8`

## Input

```
btn(key)                    True while key is held
btnp(key, [hold], [repeat]) True on press (with optional auto-repeat)
btnr(key)                   True on release
mouse_x, mouse_y            mouse position
```

Common keys: `KEY_LEFT/RIGHT/UP/DOWN`, `KEY_SPACE`, `KEY_RETURN`, \
`KEY_A`..`KEY_Z`, `MOUSE_BUTTON_LEFT`

## Audio Playback

```python
pyxel.play(ch, snd, loop=False)   # play sound on channel 0-3
pyxel.play(ch, snd, resume=True)  # play without stopping current sound on channel
pyxel.playm(msc, loop=False)      # play music
pyxel.stop(ch)                    # stop channel (omit ch to stop all)
```

### Channel Management

Pyxel has 4 audio channels (0-3). `playm()` assigns music tracks to channels
starting from ch0. `play(ch, snd)` on the same channel **interrupts** the music
on that channel. Plan channel allocation to avoid BGM/SE conflicts:

- **BGM on ch0-2, SE on ch3**: Use 3-channel music so SE never interrupts BGM.
- **Title/menu screens**: Can safely use all 4 channels for BGM (no frequent SE).
- Use `resume=True` for non-critical SE to avoid cutting off other sounds.

## Math

`sin(deg)`, `cos(deg)` use **degrees** (not radians). `atan2(y, x)` returns degrees.
`rndi(a, b)` random int, `rndf(a, b)` random float.
`ceil(x)`, `floor(x)`, `sgn(x)`, `sqrt(x)`.

## Camera & Effects

```python
pyxel.camera(x, y)       # shift drawing origin (for scrolling)
pyxel.camera()            # reset origin
pyxel.clip(x, y, w, h)   # restrict drawing area
pyxel.clip()              # reset clip
pyxel.pal(col1, col2)    # swap palette color (e.g., damage flash)
pyxel.pal()               # reset palette
pyxel.dither(alpha)       # dithering (0.0-1.0), affects subsequent draws
```

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

Tilemaps compose maps from 8x8 tile regions in an image bank. Each tile is referenced \
by its (x, y) position in the image bank in tile units (0-based, where tile (1, 0) = \
pixels (8, 0)).

```python
# Tilemap data format: each tile = 4 hex chars "XXYY" (x, y in tile units)
# Example: "0000" = tile(0,0), "0100" = tile(1,0), "0001" = tile(0,1)

# Create tilemap: Tilemap(width, height, imgsrc)
# Default tilemaps (pyxel.tilemaps[0-7]) are also available

# Define a 4x3 tile map (32x24 pixels)
pyxel.tilemaps[0].set(0, 0, [
    "0000010002000300",  # row 0: tiles (0,0) (1,0) (2,0) (3,0)
    "0001010102000300",  # row 1: tiles (0,1) (1,1) (2,0) (3,0)
    "0002010202000300",  # row 2: tiles (0,2) (1,2) (2,0) (3,0)
])

# Draw tilemap (colkey for transparent color)
pyxel.bltm(0, 0, 0, 0, 0, 32, 24, colkey=0)
# bltm(x, y, tm, u, v, w, h, colkey) — u,v,w,h in pixels

# Read/write individual tiles
tile = pyxel.tilemaps[0].pget(tx, ty)  # returns (tile_x, tile_y)
pyxel.tilemaps[0].pset(tx, ty, (tile_x, tile_y))
```

Typical workflow: define tiles in an image bank with `images[N].set()`, then arrange \
them into a map with `tilemaps[N].set()`.

### Sounds

```python
pyxel.sounds[0].set(
    notes="c2e2g2c3",    # notes: [cdefgab][0-4], r=rest
    tones="ssss",         # t=triangle s=square p=pulse n=noise
    volumes="7654",       # 0-7
    effects="nnnn",       # n=none s=slide v=vibrato f=fadeout h=half_fadeout q=quarter_fadeout
    speed=20,
)
```

### MML (Music Macro Language)

`Sound.mml()` provides flexible music composition beyond `Sound.set()`:

```python
pyxel.sounds[0].mml("T120 @1 V100 L8 O4 CDEFGAB>C")
```

Key commands: `T`=tempo, `@`=tone(0:tri 1:sq 2:pulse 3:noise), `V`=volume(0-127), \
`O`=octave, `>`/`<`=octave up/down, `L`=default length, `R`=rest, `#`/`-`=sharp/flat, \
`.`=dotted, `&`=tie, `[`..`]N`=repeat N times.
Advanced: `@ENV`=envelope, `@VIB`=vibrato, `@GLI`=glide.
Full syntax: fetch the MML commands JSON.

### Quick BGM

```python
mml_list = pyxel.gen_bgm(preset, instr, seed=None)
# preset: 0-7 (music style), instr: 0-3 (instrument set)
# Returns: list of 4 MML strings (one per channel)
# Always returns 4 channels — drop extras if you need to reserve channels for SE

# Example: 3-channel BGM (reserve ch3 for SE)
mml = pyxel.gen_bgm(7, 1, seed=42)
for i in range(3):
    pyxel.sounds[10 + i].mml(mml[i])
pyxel.musics[0].set([10], [11], [12])

# Quick play (uses all 4 channels — good for title screens)
pyxel.gen_bgm(preset, instr, seed=42, play=True)
```

### Music

```python
# Combine sounds into multi-channel music
pyxel.musics[0].set([0, 1], [2, 3], [4])  # ch0: snd 0,1  ch1: snd 2,3  ch2: snd 4
pyxel.playm(0, loop=True)
```

## Advanced

```python
# Tilemap collision (for platformers)
dx, dy = pyxel.tilemaps[0].collide(x, y, w, h, dx, dy, wall_tiles)
# wall_tiles: list of (tile_x, tile_y) tuples treated as walls

# Custom font (TTF)
font = pyxel.Font("font.ttf", 12)
pyxel.text(x, y, "Hello", col, font)
w = font.text_width("Hello")

# Load external images
pyxel.images[0].load(0, 0, "sprite.png")

# Load Tiled map
tm = pyxel.Tilemap.from_tmx("map.tmx", layer=0)

# Custom tone (wavetable)
pyxel.tones[0].wavetable[:] = [0, 4, 8, 12, 15, 12, 8, 4] * 4  # 32 samples, 0-15

# PCM audio
pyxel.sounds[0].pcm("sound.wav")
```

## Color Palette & Hierarchy

0:black 1:navy 2:purple 3:green 4:brown 5:dark_blue 6:light_blue 7:white
8:red 9:orange 10(a):yellow 11(b):lime 12(c):cyan 13(d):gray 14(e):pink 15(f):peach

### 3-Layer Color Hierarchy

Establish clear visual layers in every game:

1. **Background** (dark): 0 (black), 1 (navy), 5 (dark_blue) — recedes visually
2. **Environment** (mid-tones): 3 (green), 4 (brown), 13 (gray) — terrain, walls
3. **Interactive** (bright): 8 (red), 10 (yellow), 11 (lime) — player, items, danger

Use 10-14 of the 16 colors. Restrict each sprite to 3-4 colors for readability. \
The player sprite should use a unique color not shared with enemies.

### Genre Palettes

Concrete color assignments by game theme:

- **Space / Shmup**: BG: 0, 1 | Stars: 5, 6, 7 | Player: 12, 7 | Enemies: 8, 9 | Bullets: 10, 11
- **Forest / Platformer**: BG: 1, 5 | Ground: 3, 4, 11 | Player: 8, 7, 15 | Items: 10, 9 | Sky: 6, 12
- **Dungeon / RPG**: BG: 0, 1 | Walls: 4, 13, 5 | Player: 7, 6, 15 | Enemies: 2, 8 | Items: 10, 9
- **Castle / Lava**: BG: 0 | Walls: 13, 5, 1 | Lava: 8, 9, 10 | Player: 7, 12 | Fire: 9, 10
- **Underwater / Ice**: BG: 1, 5 | Terrain: 6, 12, 7 | Player: 8, 9, 15 | Items: 10, 14

### Game Boy (4-color)

```python
pyxel.pal(0, 1)   # black → navy
pyxel.pal(1, 3)   # navy → green
pyxel.pal(3, 11)  # green → lime
pyxel.pal(7, 7)   # white stays white
```

### Palette Swap for Level Theming

Same tiles, different mood — use `pyxel.pal()`:

```python
# Underground: warm browns → cold blues
pyxel.pal(4, 1)   # brown → navy
pyxel.pal(9, 12)  # orange → cyan
pyxel.pal(3, 5)   # green → dark_blue
```

## Pixel Art Rules

### 3-Color-Per-Material Rule

Every surface in a sprite uses 3 colors: base, shadow, highlight. \
Shift hue slightly between them (not just brightness) for richer results.

| Material | Shadow | Base | Highlight |
|----------|--------|------|-----------|
| Skin | 4 (brown) | 15 (peach) | 7 (white) |
| Green | 3 (green) | 11 (lime) | 10 (yellow) |
| Blue | 1 (navy) | 6 (light_blue) | 12 (cyan) |
| Red | 2 (purple) | 8 (red) | 9 (orange) |
| Metal | 5 (dark_blue) | 13 (gray) | 7 (white) |
| Wood | 4 (brown) | 9 (orange) | 15 (peach) |

### Outline Strategy

Use **black outlines** (color 0) for maximum readability at small sizes. \
At 8x8, outlines define the silhouette — draw silhouette first, then fill.

### Sprite Size Guidelines

| Size | Use Case | Colors |
|------|----------|--------|
| 8x8 | Tiles, items, bullets, small enemies | 3-4 colors |
| 16x16 | Player, main enemies, NPCs | 5-6 colors |
| 24x24 | RPG characters, detailed sprites | 5-7 colors |

Player/item sprites should be **horizontally symmetric**. \
Enemy sprites can be asymmetric for organic/alien look. \
Use `inspect_sprite` to verify symmetry after creation.

### Anti-Patterns

- **Pillow shading**: Shadow around edges, highlight in center — looks puffy. \
Shadow goes on bottom/right, highlight on top/left.
- **Too many colors**: 3-4 colors per 8x8, 5-6 per 16x16. More = messy.
- **Random dithering**: Only dither in transition zones, never randomly.

## Sprite Templates

Ready-to-use hex sprites for `pyxel.images[N].set()`. Color 0 = transparent.

### 8x8 Player Ship (shmup)

```python
pyxel.images[0].set(0, 0, [
    "00c00c00",
    "0c7007c0",
    "0c7007c0",
    "c703b07c",
    "77033077",
    "785cc587",
    "85c77c58",
    "0c0880c0",
])
```

### 8x8 Player Character (platformer)

```python
pyxel.images[0].set(0, 0, [
    "00777700",
    "77711100",
    "77711100",
    "77777700",
    "77777777",
    "00777000",
    "00700700",
    "00700700",
])
```

### 8x8 Slime Enemy

```python
pyxel.images[0].set(8, 0, [
    "00000000",
    "00333300",
    "03b33b30",
    "0b3333b0",
    "33333333",
    "33333333",
    "03333330",
    "00333300",
])
```

### 8x8 Coin

```python
pyxel.images[0].set(16, 0, [
    "00aaaa00",
    "0a9aa9a0",
    "a99aa99a",
    "a99aa99a",
    "a99aa99a",
    "a99aa99a",
    "0a9aa9a0",
    "00aaaa00",
])
```

### 8x8 Heart

```python
pyxel.images[0].set(24, 0, [
    "08800880",
    "88888888",
    "88888888",
    "88888888",
    "08888880",
    "00888800",
    "00088000",
    "00000000",
])
```

### 8x8 Skull Enemy

```python
pyxel.images[0].set(32, 0, [
    "07777770",
    "70700707",
    "70700707",
    "77777777",
    "70777707",
    "07700770",
    "07777770",
    "00000000",
])
```

### 8x8 Shield Collectible

```python
pyxel.images[0].set(40, 0, [
    "00c77c00",
    "0c6666c0",
    "c670076c",
    "c670076c",
    "0c6666c0",
    "00c66c00",
    "000cc000",
    "00000000",
])
```

### 8x8 Sword

```python
pyxel.images[0].set(48, 0, [
    "00000070",
    "00000770",
    "00007700",
    "00077000",
    "04077000",
    "00440000",
    "00940000",
    "00090000",
])
```

### Sprite Sheet Organization

Pack sprites in image bank 0 at 8px intervals:
- (0,0): Player | (8,0): Enemy1 | (16,0): Item1 | (24,0): Item2
- (0,8): Player walk frame 2 | (8,8): Enemy2 | etc.
- Animation frames: adjacent horizontally \
`u = pyxel.frame_count // speed % frame_count * 8`

## Background Design

Background quality is the single biggest factor in visual polish. \
Never leave the background as a plain solid color.

| Tier | Technique | Example |
|------|-----------|---------|
| S | Multi-layer parallax, atmospheric gradients, detailed tile art | Mountains + sky layers scrolling at different speeds |
| A | Varied tile patterns, color-coded zones | Brick walls with shading, biome-colored terrain |
| B | Dark background + subtle detail | Black sky with star particles, dark blue with dithering |
| C | Solid single color (looks amateur) | `cls(0)` with nothing else — avoid this |

```python
# Minimal star background (huge improvement over plain black)
stars = [(pyxel.rndi(0, 159), pyxel.rndi(0, 119), pyxel.rndi(1, 3)) for _ in range(30)]
# In draw():
for sx, sy, brightness in stars:
    pyxel.pset(sx, sy, [1, 5, 6, 7][brightness])
```

### Parallax Scrolling

```python
# 2-layer parallax (great for shmups/platformers)
# In draw():
for i in range(20):
    x = (i * 40 - pyxel.frame_count // 2) % (pyxel.width + 20) - 10
    pyxel.circ(x, 20, 6, 1)   # far clouds (slow)
for i in range(10):
    x = (i * 50 - pyxel.frame_count) % (pyxel.width + 20) - 10
    pyxel.circ(x, 40, 10, 5)  # near clouds (fast)

# Draw layers back-to-front with different scroll speeds:
# Layer 1 (far): offset = frame_count // 16
# Layer 2 (mid): offset = frame_count // 8
# Layer 3 (near): offset = frame_count // 4
# Layer 4 (ground): offset = frame_count (1:1 with camera)

# Seamless wrap:
for i in range(2):
    pyxel.blt(i * pyxel.width - offset % pyxel.width, y,
              0, u, v, pyxel.width, h, colkey=0)
```

## Screen & Text Layout

Plan the screen composition **before** coding. Allocate regions for each element, \
then derive all coordinates from those regions.

```python
# Example: game with side panel (160x120 screen)
MARGIN = 4
PANEL_W = 32
GAME_W = pyxel.width - PANEL_W - MARGIN * 3   # play area width
GAME_X = MARGIN                                 # play area left
GAME_Y = MARGIN                                 # play area top
GAME_H = pyxel.height - MARGIN * 2             # play area height
PANEL_X = GAME_X + GAME_W + MARGIN             # panel left

# Center play area if no side panel
GAME_W = COLS * CELL
GAME_X = (pyxel.width - GAME_W) // 2
```

Layout rules:
- **Center the main play area**: The play area is the player's focal point — \
center it both horizontally and vertically. Compute total content height \
(play area + gaps + controls) and derive `BY = (pyxel.height - content_h) // 2`. \
Place secondary info (score, next piece) in the remaining margins.
- **Define regions first**: Assign rectangles for play area, HUD, and panels. \
Derive all draw coordinates from these — never scatter magic numbers.
- **Uniform margins**: Use a consistent `MARGIN` (typically 4-8px) around and between regions.
- **No overlap**: HUD text must not intrude into the play area. Draw a border or \
leave a gap between regions.
- **Fill the screen**: Avoid large dead zones. If the play area is narrow, center it \
and use side margins for info panels.
- **Verify with `inspect_layout`**: Check horizontal balance is close to 50% and \
text offsets are small.

### Text Positioning

Always **calculate** text positions — never hardcode pixel coordinates.
The built-in font is `FONT_WIDTH=4` px wide, `FONT_HEIGHT=6` px tall.

```python
# Horizontal centering
x = (pyxel.width - len(text) * pyxel.FONT_WIDTH) // 2

# Right-align (with margin)
x = pyxel.width - len(text) * pyxel.FONT_WIDTH - margin

# Center a group (e.g., sprite 8px + gap 4px + text)
group_w = 8 + 4 + len(text) * pyxel.FONT_WIDTH
x = (pyxel.width - group_w) // 2

# Vertical centering of N lines (with spacing between lines)
block_h = N * pyxel.FONT_HEIGHT + (N - 1) * spacing
y = (pyxel.height - block_h) // 2

# Text shadow for readability over any background
pyxel.text(x + 1, y + 1, s, 1)  # shadow (dark)
pyxel.text(x, y, s, 7)          # foreground (bright)
```

## Title Screen Design

A plain text title looks amateur. Good title screens include:

1. **Pixel art game name** — larger than regular text, styled
2. **Animated elements** — bouncing sprites, scrolling background
3. **Controls hint** — key bindings visible
4. **Blinking prompt** — "PRESS ENTER" toggled with `frame_count`

```python
def draw_title(self):
    # Animated sprite decoration
    for i in range(5):
        x = 20 + i * 28
        y = 20 + pyxel.sin(pyxel.frame_count * 3 + i * 72) * 3
        pyxel.blt(x, int(y), 0, i * 8, 0, 8, 8, colkey=0)
    # Game title (centered)
    t = "MY GAME"
    pyxel.text((pyxel.width - len(t) * 4) // 2, 48, t, 7)
    # Controls
    pyxel.text(40, 70, "ARROWS:MOVE  Z:JUMP", 13)
    # Blinking prompt
    if pyxel.frame_count % 40 < 28:
        t2 = "PRESS ENTER"
        pyxel.text((pyxel.width - len(t2) * 4) // 2, 100, t2, 10)
```

## Visual Feedback

Every player-visible event needs visual and audio feedback:

| Event | Visual | Sound |
|-------|--------|-------|
| Hit/damage | `pal()` flash to white 2-3f | Descending (snd 2) |
| Collect item | Sparkle particles | Ascending (snd 1) |
| Destroy enemy | Expanding explosion | Noise burst (snd 3) |
| Clear/combo | Screen flash with `dither()` | Fanfare (snd 5) |
| Death | Sprite blink then fade | Game over (snd 4) |
| Land | Screen shake 1-2px | Impact noise (snd 8) |

```python
# Damage flash (in draw)
if self.hit_timer > 0:
    pyxel.pal(player_color, 7)  # flash white
# After drawing player:
    pyxel.pal()  # reset

# Simple explosion particles
class Particle:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.dx = pyxel.rndf(-2, 2)
        self.dy = pyxel.rndf(-2, 2)
        self.life = 10
    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.life -= 1
    def draw(self):
        if self.life > 0:
            pyxel.pset(int(self.x), int(self.y), 10 if self.life > 5 else 9)
```

### Screen Shake

```python
# Trigger: self.shake_mag, self.shake_dur = magnitude, frames
# In update():
if self.shake_dur > 0:
    ox = pyxel.rndi(-int(self.shake_mag), int(self.shake_mag))
    oy = pyxel.rndi(-int(self.shake_mag), int(self.shake_mag))
    self.shake_mag *= 0.7
    self.shake_dur -= 1
    pyxel.camera(ox, oy)
else:
    pyxel.camera()

# Magnitudes: dash/land 1-2px 2-3f | hit 2-3px 3-5f | explosion 3-5px 5-8f | boss 5-8px 10-15f
```

### Hitstop (Freeze Frames)

```python
# On impact: self.hitstop = 2  (light) or 4 (heavy)
# In update():
if self.hitstop > 0:
    self.hitstop -= 1
    return  # skip physics, keep drawing effects
```

## Sound Effects Cookbook

Copy-paste sound definitions for common game events. \
All SE on ch3 via `pyxel.play(3, N)`. BGM on ch0-2.

Design rules:
- Use square (`"s"`) or pulse (`"p"`) for melodic SE — noise (`"n"`) only for impacts
- SE speed 3-10 (fast, snappy), BGM speed 16-25 (slower, musical)
- SE volume 5-7 to cut through BGM (volume 3-5)
- Ascending notes = positive (collect, power-up, level clear)
- Descending notes = negative (damage, death, game over)

### Jump

```python
pyxel.sounds[0].set(
    notes="c2e2g2c3", tones="s", volumes="7776", effects="nnnn", speed=8,
)
```

### Coin / Collect

```python
pyxel.sounds[1].set(
    notes="c3e3g3c4c4", tones="s", volumes="44444",
    effects="nnnnf", speed=7,
)
```

### Hit / Damage

```python
pyxel.sounds[2].set(
    notes="g3c3", tones="s", volumes="74", effects="nn", speed=5,
)
```

### Explosion

```python
pyxel.sounds[3].set(
    notes="c4d4e3f3g3a3b2c2d2e1f1g1",
    tones="n",
    volumes="776655443210",
    effects="nnnnnnnnnnnn",
    speed=5,
)
```

### Game Over

```python
pyxel.sounds[4].set(
    notes="f3b2f2b1f1f1f1f1", tones="p",
    volumes="44444321", effects="nnnnnnnf", speed=9,
)
```

### Level Clear

```python
pyxel.sounds[5].set(
    notes="c2e2g2c3e3g3c4", tones="s",
    volumes="7777777", effects="nnnnnnn", speed=8,
)
```

### Menu Select / Cursor

```python
pyxel.sounds[6].set(
    notes="e3", tones="s", volumes="5", effects="f", speed=10,
)
```

### Power-Up

```python
pyxel.sounds[7].set(
    notes="c1c2c3c4", tones="s",
    volumes="5567", effects="nnnn", speed=6,
)
```

### Landing

```python
pyxel.sounds[8].set(
    notes="c1", tones="n", volumes="5", effects="f", speed=3,
)
```

### Shoot / Laser

```python
pyxel.sounds[9].set(
    notes="a3a2c1a1", tones="p", volumes="7", effects="s", speed=5,
)
```

## Game Patterns

### Platformer

```python
# Gravity + jump (see Game Feel Constants for tuned variants)
GRAVITY = 0.35
JUMP_VEL = -4.5
vy = min(vy + GRAVITY, 3.5)  # terminal velocity
if on_ground and pyxel.btnp(pyxel.KEY_SPACE):
    vy = JUMP_VEL
y += vy

# Tilemap collision for solid ground
dx, dy = pyxel.tilemaps[0].collide(x, y, w, h, dx, dy, wall_tiles)
```

### Shooter (top-down / side-scroll)

```python
# Bullet management
if pyxel.btnp(pyxel.KEY_SPACE):
    bullets.append({"x": player_x, "y": player_y})
for b in list(bullets):
    b["y"] -= BULLET_SPEED
    if b["y"] < 0:
        bullets.remove(b)

# Enemy-bullet collision
for e in list(enemies):
    for b in list(bullets):
        if abs(e["x"] - b["x"]) < 8 and abs(e["y"] - b["y"]) < 8:
            enemies.remove(e)
            bullets.remove(b)
            break
```

### Scene Management

```python
# Simple state machine for title/game/gameover
SCENE_TITLE, SCENE_GAME, SCENE_GAMEOVER = 0, 1, 2
scene = SCENE_TITLE

def update(self):
    if self.scene == SCENE_TITLE:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.scene = SCENE_GAME
    elif self.scene == SCENE_GAME:
        self.update_game()
    elif self.scene == SCENE_GAMEOVER:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.scene = SCENE_TITLE

def draw(self):
    pyxel.cls(0)
    if self.scene == SCENE_TITLE:
        self.draw_title()   # see Title Screen Design
    elif self.scene == SCENE_GAME:
        self.draw_game()
    elif self.scene == SCENE_GAMEOVER:
        pyxel.text(60, 40, "GAME OVER", 8)
        t = f"SCORE: {self.score}"
        pyxel.text((pyxel.width - len(t) * 4) // 2, 55, t, 7)
        if pyxel.frame_count % 40 < 28:
            pyxel.text(44, 80, "PRESS ENTER", 13)
```

## Game Feel Constants

Tested physics values. At 30fps, 1 frame = 33ms. At 60fps, 1 frame = 16ms. \
Pyxel defaults to 30fps. Values below are for 30fps unless noted.

### Platformer Physics

```python
# Tight / responsive (Celeste-style)
GRAVITY = 0.35
JUMP_VEL = -4.5
MAX_FALL = 3.5
WALK_SPEED = 1.5
RUN_SPEED = 2.5
ACCEL = 0.5           # frames to top speed: ~5
DECEL = 0.8           # frames to stop: ~2

# Floaty / momentum (Mario-style)
GRAVITY = 0.25
JUMP_VEL = -3.5
MAX_FALL = 3.0
WALK_SPEED = 1.0
RUN_SPEED = 2.0
ACCEL = 0.15          # frames to top speed: ~13
DECEL = 0.1           # frames to stop: ~20 (slippery)
```

### Variable Jump Height

```python
if on_ground and pyxel.btnp(pyxel.KEY_SPACE):
    vy = JUMP_VEL
    jump_hold = JUMP_HOLD_MAX  # e.g., 8

if pyxel.btn(pyxel.KEY_SPACE) and jump_hold > 0:
    vy += JUMP_HOLD_BOOST  # e.g., -0.25
    jump_hold -= 1

if pyxel.btnr(pyxel.KEY_SPACE):
    jump_hold = 0

vy = min(vy + GRAVITY, MAX_FALL)
```

### Forgiveness Mechanics (Critical)

```python
COYOTE_FRAMES = 3          # jump after leaving edge
JUMP_BUFFER_FRAMES = 4     # pre-land jump input

# Coyote time
if on_ground:
    coyote = COYOTE_FRAMES
else:
    coyote = max(0, coyote - 1)

can_jump = on_ground or coyote > 0

# Jump buffer
if pyxel.btnp(pyxel.KEY_SPACE):
    jump_buffer = JUMP_BUFFER_FRAMES

if jump_buffer > 0:
    jump_buffer -= 1
    if can_jump:
        vy = JUMP_VEL
        jump_buffer = 0
```

### Knockback and Invincibility

```python
KNOCKBACK_VX = 2.0         # horizontal push
KNOCKBACK_VY = -2.0        # upward bounce
KNOCKBACK_DUR = 6          # frames
INVINCIBLE_FRAMES = 60     # 2 seconds at 30fps
I_BLINK_RATE = 3           # toggle visibility every 3 frames
HIT_PAUSE = 2              # freeze frames on impact
```

### Shooter Constants

```python
PLAYER_SPEED = 2.0
BULLET_SPEED = 4.0
ENEMY_BULLET_SPEED = 2.0
FIRE_RATE = 5              # frames between shots
MAX_PLAYER_BULLETS = 8
ENEMY_SPEED = 1.0
SPAWN_INTERVAL = 30        # frames between spawns
```

### Puzzle / Tetris Constants

```python
DROP_FRAMES = [30, 27, 24, 21, 18, 15, 12, 10, 8, 6, 5, 4, 3, 2, 1]
SOFT_DROP_MULT = 5
LOCK_DELAY = 20            # frames after landing before lock
DAS_INITIAL = 8            # frames before auto-repeat starts
DAS_REPEAT = 3             # frames between repeats
LINE_CLEAR_ANIM = 15       # frames for clear animation
```

### Hitbox Design

- **Hazards**: hitbox **smaller** than sprite (forgiving)
- **Rewards/Stomp targets**: hitbox matches sprite (accurate)
- Player: use 60-75% of sprite size as hitbox (e.g., 6x6 for 8x8 sprite)
- `abs(a.x - b.x) < HIT_W and abs(a.y - b.y) < HIT_H`

### Timing Constants

```python
GET_READY_DURATION = 60      # 2s at 30fps
GAME_OVER_DURATION = 90      # 3s
STAGE_CLEAR_DURATION = 90    # 3s
TITLE_BLINK_RATE = 40        # frame_count % 40 < 28 for blink
```

### Camera (Side-Scroller)

```python
# Smooth follow (lerp)
camera_x += (player_x - camera_x - pyxel.width // 2) * 0.1
# 0.1 = smooth, 0.2 = responsive, 0.05 = cinematic

# Look-ahead: offset camera in movement direction
if facing_right:
    target = player_x - pyxel.width // 3
else:
    target = player_x - pyxel.width * 2 // 3
```

## Animation Timing

Recommended frame counts for common animations:

| Animation | Frames | Speed (frames/update) |
|-----------|--------|-----------------------|
| Idle breathing | 2-4 | 20-30 |
| Walk cycle | 4-6 | 4-6 |
| Run cycle | 4-6 | 2-3 |
| Attack | 3-5 | 2-4 |
| Jump | 3-4 | 3-5 |
| Explosion | 4-8 | 3-4 |
| Coin spin | 4 | 5-8 |

```python
# Standard animation pattern
ANIM_FRAMES = 4
ANIM_SPEED = 5  # change sprite every 5 game frames
frame = pyxel.frame_count // ANIM_SPEED % ANIM_FRAMES
u = frame * SPRITE_W  # offset into sprite sheet
pyxel.blt(x, y, 0, u, v, SPRITE_W, SPRITE_H, colkey=0)
```

## Quality Checklist

Quick-reference of common mistakes. See linked sections for details.

| Category | Don't | Do |
|----------|-------|----|
| Code | Hardcode pixel positions | Calculate from `width`/`height` |
| Code | Forget `cls()` in `draw()` | Always call `pyxel.cls(col)` first |
| Code | Use radians with `sin()`/`cos()` | Pyxel trig uses degrees |
| Code | `btn()` for one-shot action | Use `btnp()` for press-once events |
| Code | Modify list while iterating | Iterate over a copy: `for e in list(enemies):` |
| Drawing | Draw UI before sprites | Draw order: bg → objects → UI |
| Drawing | Omit `colkey` in `blt()` | Add `colkey=0` for transparency |
| Drawing | Static animation frame | See Animation Timing |
| Visual | Plain black background | See Background Design |
| Visual | No title screen | See Title Screen Design |
| Visual | No visual feedback on actions | See Visual Feedback |
| Visual | Player blends into bg | See Color Palette & Hierarchy |
| Audio | `play()` on BGM channel | SE on ch3, BGM on ch0-2 |
| Audio | Noise tone for melodic SE | Square or pulse, vol 5-7 |
| Audio | Skip SE for core actions | SE for every player event |

Before release, verify: BGM present, distinct SE for all events, \
title screen with animation, game over with score, \
non-solid background, HUD with score/lives.
"""

mcp = FastMCP("pyxel-mcp", instructions=_INSTRUCTIONS)


@mcp.tool()
async def run_and_capture(
    script_path: str,
    frames: int = 60,
    scale: int = 2,
    timeout: int = 10,
) -> list:
    """Run a Pyxel script and capture a screenshot after N frames.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Number of frames to render before capturing (default: 60).
        scale: Screenshot scale multiplier (default: 2).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return ["Error: Pyxel is not installed. Run: pip install pyxel-mcp"]

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return [f"Error: script not found: {script_path}"]

    frames = max(1, min(frames, 1800))
    scale = max(1, min(scale, 10))
    timeout = max(1, min(timeout, 60))

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        output_path = tmp.name

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, HARNESS_PATH,
            script_path, output_path, str(frames), str(scale),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            error_msg = _decode_stderr(stderr) or "Unknown error"
            return [f"Capture failed (exit code {proc.returncode}): {error_msg}"]

        with open(output_path, "rb") as f:
            image_data = f.read()
        result = [Image(data=image_data, format="png")]
        info = f"Captured at frame {frames}, scale {scale}x"
        stderr_text = _decode_stderr(stderr)
        if stderr_text:
            info += f"\nstderr: {stderr_text}"
        result.append(info)
        return result

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return [f"Timeout: script did not finish within {timeout}s"]
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


@mcp.tool()
def pyxel_info() -> str:
    """Get Pyxel installation info: package location, examples path, and API stubs path."""
    pyxel_dir = _pyxel_dir()
    if not pyxel_dir:
        return (
            "Pyxel is not installed.\n"
            "Install it with: pip install pyxel-mcp\n"
            "See https://github.com/kitao/pyxel for details."
        )
    examples = os.path.join(pyxel_dir, "examples")
    pyi = os.path.join(pyxel_dir, "__init__.pyi")
    lines = [
        f"Pyxel package: {pyxel_dir}",
        f"API type stubs: {pyi}" + (" (found)" if os.path.isfile(pyi) else " (not found)"),
        f"Examples dir: {examples}" + (" (found)" if os.path.isdir(examples) else " (not found)"),
    ]
    if os.path.isdir(examples):
        files = sorted(glob.glob(os.path.join(examples, "*.py")))
        lines.append(f"Examples: {', '.join(os.path.basename(f) for f in files)}")
    return "\n".join(lines)


# --- Audio analysis ---

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Major and minor scale templates (pitch class sets)
_SCALE_TEMPLATES = {
    "major": {0, 2, 4, 5, 7, 9, 11},
    "minor": {0, 2, 3, 5, 7, 8, 10},
    "penta": {0, 2, 4, 7, 9},
}


def _freq_to_note(freq):
    """Convert frequency (Hz) to note name like C5, A4."""
    if freq < 20:
        return "~"
    midi = 69 + 12 * math.log2(freq / 440.0)
    idx = round(midi) % 12
    octave = (round(midi) // 12) - 1
    return f"{NOTE_NAMES[idx]}{octave}"


def _freq_to_midi(freq):
    """Convert frequency to MIDI note number."""
    if freq < 20:
        return -1
    return round(69 + 12 * math.log2(freq / 440.0))


def _estimate_freq(samples, sample_rate):
    """Estimate fundamental frequency using autocorrelation.

    Uses a "first peak after dip" approach: the autocorrelation naturally
    starts high at small lags (adjacent samples are correlated) and decays.
    The true fundamental shows up as the first significant peak *after* this
    initial decay, not as the global maximum (which is often at min_lag for
    smooth waveforms like triangle waves, causing ~2000 Hz artifacts).
    """
    n = len(samples)
    min_lag = max(1, sample_rate // 2000)  # up to 2000 Hz
    max_lag = min(sample_rate // 50, n // 2)  # down to 50 Hz
    if max_lag <= min_lag:
        return 0

    # Remove DC offset
    mean = sum(samples) / n
    centered = [s - mean for s in samples]

    energy = sum(s * s for s in centered)
    if energy == 0:
        return 0

    # Compute normalized autocorrelation for the lag range
    num_lags = max_lag - min_lag
    corrs = [0.0] * num_lags
    for idx in range(num_lags):
        lag = min_lag + idx
        corrs[idx] = sum(centered[i] * centered[i + lag] for i in range(n - lag)) / energy

    # Find where correlation first drops below threshold (end of initial decay)
    dip_idx = None
    for i in range(num_lags):
        if corrs[i] < 0.2:
            dip_idx = i
            break

    if dip_idx is None:
        # Correlation never dipped — either genuinely high frequency or noise.
        # Fall back to global max with a strict threshold.
        best_i = max(range(num_lags), key=lambda i: corrs[i])
        return sample_rate / (min_lag + best_i) if corrs[best_i] > 0.6 else 0

    # Find first peak after the dip (the true fundamental period)
    for i in range(max(1, dip_idx), num_lags - 1):
        if corrs[i] > 0.3 and corrs[i] >= corrs[i - 1] and corrs[i] >= corrs[i + 1]:
            return sample_rate / (min_lag + i)

    return 0


def _detect_key(midi_notes):
    """Detect musical key from a list of MIDI note numbers."""
    if not midi_notes:
        return "unknown"
    # Build pitch class histogram
    pc_hist = [0] * 12
    for m in midi_notes:
        pc_hist[m % 12] += 1

    best_score = -1
    best_key = "C major"
    for root in range(12):
        for scale_name, template in _SCALE_TEMPLATES.items():
            score = sum(pc_hist[(root + pc) % 12] for pc in template)
            if score > best_score:
                best_score = score
                best_key = f"{NOTE_NAMES[root]} {scale_name}"
    return best_key


def _analyze_intervals(midi_notes):
    """Classify intervals between consecutive notes."""
    if len(midi_notes) < 2:
        return {}
    counts = {"step (1-2)": 0, "skip (3-4)": 0, "leap (5-7)": 0, "jump (8+)": 0}
    for i in range(1, len(midi_notes)):
        diff = abs(midi_notes[i] - midi_notes[i - 1])
        if diff <= 2:
            counts["step (1-2)"] += 1
        elif diff <= 4:
            counts["skip (3-4)"] += 1
        elif diff <= 7:
            counts["leap (5-7)"] += 1
        else:
            counts["jump (8+)"] += 1
    return counts


def _suggest_role(midi_notes, durations_ms):
    """Suggest channel role based on pitch range and rhythm."""
    if not midi_notes:
        return "silent"
    lo = min(midi_notes)
    hi = max(midi_notes)
    avg = sum(midi_notes) / len(midi_notes)
    unique_durs = len(set(durations_ms))

    if avg < 48:  # below C3
        return "bass"
    if avg < 60:  # C3-B3
        if unique_durs <= 2:
            return "bass"
        return "bass/accompaniment"
    if avg < 72:  # C4-B4
        if unique_durs >= 3:
            return "melody"
        return "accompaniment"
    return "melody (high)"


def _analyze_wav(wav_path):
    """Analyze WAV file and return frequency/amplitude report with musical analysis."""
    with wave.open(wav_path, "r") as wf:
        n_channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if n_frames == 0:
        return "Empty audio (0 samples)"

    samples = list(struct.unpack(f"<{n_frames * n_channels}h", raw))
    if n_channels > 1:
        samples = [
            sum(samples[i : i + n_channels]) // n_channels
            for i in range(0, len(samples), n_channels)
        ]

    duration = n_frames / sample_rate
    peak = max(abs(s) for s in samples)
    rms = math.sqrt(sum(s * s for s in samples) / len(samples))

    # Time-windowed analysis (100ms windows)
    window_size = sample_rate // 10
    segments = []
    for start in range(0, len(samples), window_size):
        w = samples[start : start + window_size]
        if len(w) < 50:
            break
        w_rms = math.sqrt(sum(s * s for s in w) / len(w))
        if w_rms < 50:
            segments.append(("~", 0, w_rms))
            continue
        freq = _estimate_freq(w, sample_rate)
        note = _freq_to_note(freq) if freq > 0 else "~"
        segments.append((note, freq, w_rms))

    # Group consecutive identical notes
    grouped = []
    for note, freq, w_rms in segments:
        if grouped and grouped[-1][0] == note:
            grouped[-1] = (
                note,
                freq,
                max(grouped[-1][2], w_rms),
                grouped[-1][3] + 100,
            )
        else:
            grouped.append((note, freq, w_rms, 100))

    lines = [
        f"Duration: {duration:.2f}s | Peak: {peak / 327.67:.0f}%"
        f" | RMS: {rms / 327.67:.0f}%",
        "",
        "Note sequence:",
    ]
    time_ms = 0
    for note, freq, w_rms, dur_ms in grouped:
        if note == "~":
            lines.append(f"  {time_ms / 1000:.1f}s [{dur_ms}ms] rest")
        else:
            lines.append(
                f"  {time_ms / 1000:.1f}s [{dur_ms}ms] {note}"
                f" (~{freq:.0f}Hz) vol={w_rms / 327.67:.0f}%"
            )
        time_ms += dur_ms

    # --- Musical analysis ---
    played = [(n, f, r, d) for n, f, r, d in grouped if n != "~"]
    if played:
        midi_notes = [_freq_to_midi(f) for _, f, _, _ in played if f > 0]
        durations = [d for _, _, _, d in played]

        if midi_notes:
            lo_note = _freq_to_note(min(f for _, f, _, _ in played if f > 0))
            hi_note = _freq_to_note(max(f for _, f, _, _ in played if f > 0))
            semitone_range = max(midi_notes) - min(midi_notes)

            lines.append("")
            lines.append("Musical analysis:")
            lines.append(
                f"  Pitch range: {lo_note} - {hi_note}"
                f" ({semitone_range} semitones)"
            )

            # Note frequency (most common)
            note_counts = {}
            for n, _, _, _ in played:
                note_counts[n] = note_counts.get(n, 0) + 1
            top_notes = sorted(note_counts.items(), key=lambda x: -x[1])[:6]
            lines.append(
                "  Top notes: "
                + " ".join(f"{n}({c}x)" for n, c in top_notes)
            )

            # Key detection
            key = _detect_key(midi_notes)
            lines.append(f"  Key estimate: {key}")

            # Interval analysis
            intervals = _analyze_intervals(midi_notes)
            if intervals:
                total = sum(intervals.values())
                parts = []
                for label, count in intervals.items():
                    if count > 0:
                        pct = count * 100 // total
                        parts.append(f"{label}:{pct}%")
                lines.append(f"  Intervals: {' '.join(parts)}")

            # Rhythm pattern
            dur_counts = {}
            for d in durations:
                dur_counts[d] = dur_counts.get(d, 0) + 1
            top_durs = sorted(dur_counts.items(), key=lambda x: -x[1])[:4]
            lines.append(
                "  Rhythm: "
                + " ".join(f"{d}ms({c}x)" for d, c in top_durs)
            )

            # Role suggestion
            role = _suggest_role(midi_notes, durations)
            lines.append(f"  Suggested role: {role}")

    return "\n".join(lines)


@mcp.tool()
async def render_audio(
    script_path: str,
    sound_index: int = 0,
    duration_sec: float = 0,
    timeout: int = 10,
) -> str:
    """Render a Pyxel sound to WAV and return waveform analysis.

    Runs the script to set up sounds (without starting the game loop),
    then renders the specified sound to WAV and analyzes the audio.
    Returns note sequence with timing, frequency, and volume data.

    Args:
        script_path: Absolute path to the .py script to run.
        sound_index: Sound slot to render, 0-63 (default: 0).
        duration_sec: Duration in seconds. 0 = auto-detect from sound length.
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    sound_index = max(0, min(sound_index, 63))
    timeout = max(1, min(timeout, 60))
    if duration_sec > 0:
        duration_sec = min(duration_sec, 30.0)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        output_path = tmp.name

    try:
        args = [
            sys.executable,
            AUDIO_HARNESS_PATH,
            script_path,
            output_path,
            str(sound_index),
        ]
        if duration_sec > 0:
            args.append(str(duration_sec))

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            error_msg = _decode_stderr(stderr) or "Unknown error"
            return f"Render failed (exit code {proc.returncode}): {error_msg}"

        meta = {}
        if stdout:
            try:
                meta = json.loads(stdout.decode(errors="replace").strip())
            except json.JSONDecodeError:
                pass

        try:
            analysis = await asyncio.to_thread(_analyze_wav, output_path)
        except Exception as e:
            analysis = f"WAV analysis failed: {e}"
        result = (
            f"Sound {sound_index} rendered"
            f" ({meta.get('duration_sec', '?')}s,"
            f" speed={meta.get('speed', '?')})\n\n{analysis}"
        )
        stderr_text = _decode_stderr(stderr)
        if stderr_text:
            result += f"\n\nstderr: {stderr_text}"
        return result

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return f"Timeout: script did not finish within {timeout}s"
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


# --- Sprite analysis ---

_PALETTE_NAMES = {
    0: "black", 1: "navy", 2: "purple", 3: "green",
    4: "brown", 5: "dark_blue", 6: "light_blue", 7: "white",
    8: "red", 9: "orange", 10: "yellow", 11: "lime",
    12: "cyan", 13: "gray", 14: "pink", 15: "peach",
}


def _format_sprite_report(data):
    """Format sprite inspection JSON into a readable report."""
    pixels = data["pixels"]
    region = data["region"]
    w, h = region["w"], region["h"]

    lines = [
        f"Sprite at image[{data['image']}] ({region['x']},{region['y']}) {w}x{h}",
        "",
        "Pixels (hex):",
    ]
    for row in pixels:
        hex_row = "".join(f"{c:x}" for c in row)
        lines.append(f"  {hex_row}")

    lines.append("")

    # Symmetry info
    lines.append(f"H-symmetry: {'yes' if data['symmetric_h'] else 'no'}")
    lines.append(f"V-symmetry: {'yes' if data['symmetric_v'] else 'no'}")

    # Color usage
    lines.append("")
    lines.append("Colors:")
    color_count = data["color_count"]
    for c_str, count in sorted(color_count.items(), key=lambda x: -x[1]):
        c = int(c_str) if isinstance(c_str, str) else c_str
        name = _PALETTE_NAMES.get(c, "?")
        lines.append(f"  {c:x}({name}): {count}px")

    return "\n".join(lines)


@mcp.tool()
async def inspect_sprite(
    script_path: str,
    image: int = 0,
    x: int = 0,
    y: int = 0,
    w: int = 8,
    h: int = 8,
    timeout: int = 10,
) -> str:
    """Inspect sprite pixel data from a Pyxel image bank.

    Reads pixel data, checks horizontal/vertical symmetry, and reports
    color usage. Use this to verify sprite quality and find asymmetries.

    Args:
        script_path: Absolute path to the .py script to run.
        image: Image bank index, 0-2 (default: 0).
        x: X position in the image bank (default: 0).
        y: Y position in the image bank (default: 0).
        w: Width of the region to inspect (default: 8).
        h: Height of the region to inspect (default: 8).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    image = max(0, min(image, 2))
    x = max(0, min(x, 255))
    y = max(0, min(y, 255))
    w = max(1, min(w, 256 - x))
    h = max(1, min(h, 256 - y))
    timeout = max(1, min(timeout, 60))

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, SPRITE_HARNESS_PATH,
            script_path, str(image), str(x), str(y), str(w), str(h),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        if proc.returncode != 0:
            error_msg = _decode_stderr(stderr) or "Unknown error"
            return f"Inspect failed (exit code {proc.returncode}): {error_msg}"

        data = json.loads(stdout.decode(errors="replace").strip())
        report = _format_sprite_report(data)

        stderr_text = _decode_stderr(stderr)
        if stderr_text:
            report += f"\n\nstderr: {stderr_text}"
        return report

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return f"Timeout: script did not finish within {timeout}s"
    except json.JSONDecodeError as e:
        return f"Failed to parse sprite data: {e}"


# --- Multi-frame capture ---


@mcp.tool()
async def capture_frames(
    script_path: str,
    frames: str = "1,15,30,60",
    scale: int = 2,
    timeout: int = 30,
) -> list:
    """Capture screenshots at multiple frame points for animation verification.

    Returns multiple images captured at specified frame numbers.
    Useful for verifying animations, transitions, and time-based effects.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Comma-separated frame numbers to capture (default: "1,15,30,60").
        scale: Screenshot scale multiplier (default: 2).
        timeout: Maximum seconds to wait for the script (default: 30).
    """
    if not _pyxel_dir():
        return ["Error: Pyxel is not installed. Run: pip install pyxel-mcp"]

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return [f"Error: script not found: {script_path}"]

    try:
        frame_list = [max(1, min(int(f.strip()), 1800)) for f in frames.split(",")]
    except ValueError:
        return ["Error: frames must be comma-separated integers (e.g. '1,15,30,60')"]

    frame_list = sorted(set(frame_list))
    if not frame_list:
        return ["Error: no valid frame numbers provided"]

    scale = max(1, min(scale, 10))
    timeout = max(1, min(timeout, 120))

    output_dir = tempfile.mkdtemp(prefix="pyxel_frames_")

    try:
        frame_csv = ",".join(str(f) for f in frame_list)
        proc = await asyncio.create_subprocess_exec(
            sys.executable, FRAMES_HARNESS_PATH,
            script_path, output_dir, frame_csv, str(scale),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        result = []
        for frame_num in frame_list:
            png_path = os.path.join(output_dir, f"frame_{frame_num:04d}.png")
            if os.path.isfile(png_path) and os.path.getsize(png_path) > 0:
                with open(png_path, "rb") as f:
                    result.append(Image(data=f.read(), format="png"))
                result.append(f"Frame {frame_num}")

        if not result:
            # Check for show-based capture
            show_path = os.path.join(output_dir, "frame_show.png")
            if os.path.isfile(show_path):
                with open(show_path, "rb") as f:
                    result.append(Image(data=f.read(), format="png"))
                result.append("Captured via pyxel.show()")

        if not result:
            error_msg = _decode_stderr(stderr) or "No frames captured"
            return [f"Capture failed (exit code {proc.returncode}): {error_msg}"]

        stderr_text = _decode_stderr(stderr)
        info = f"Captured {len([r for r in result if isinstance(r, Image)])} frames"
        if stderr_text:
            info += f"\nstderr: {stderr_text}"
        result.append(info)
        return result

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return [f"Timeout: script did not finish within {timeout}s"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


# --- Layout analysis ---


def _format_layout_report(data):
    """Format layout analysis JSON into a readable report."""
    screen = data["screen"]
    bg = data["bg_color"]
    lines = [
        f"Screen: {screen['w']}x{screen['h']}  bg_color: {bg}"
        f" ({_PALETTE_NAMES.get(bg, '?')})",
    ]

    bbox = data.get("content_bbox")
    if bbox:
        cx = bbox["x"] + bbox["w"] / 2
        screen_cx = screen["w"] / 2
        offset = cx - screen_cx
        lines.append(
            f"Content bbox: ({bbox['x']},{bbox['y']})"
            f" {bbox['w']}x{bbox['h']}"
            f"  center_x={cx:.0f} (offset {offset:+.0f}px from screen center)"
        )

    fg = data["fg_pixels"]
    bal = data["h_balance"]
    lines.append(
        f"H-balance: {bal:.1%}"
        f"  (left:{fg['left']}px right:{fg['right']}px)"
    )
    if bal < 0.7:
        lines.append("  Note: significant left/right imbalance")

    text_lines = data.get("text_lines", [])
    if text_lines:
        lines.append("")
        lines.append(f"Text lines detected: {len(text_lines)}")
        screen_cx = screen["w"] / 2
        for tl in text_lines:
            color_name = _PALETTE_NAMES.get(tl["color"], "?")
            off = tl["offset_from_center"]
            align = "centered" if abs(off) <= 2 else f"offset {off:+.0f}px"
            lines.append(
                f"  y={tl['y']:3d}  x={tl['x']:3d}  w={tl['w']:3d}px"
                f"  color={tl['color']:x}({color_name})"
                f"  {align}"
            )

        # Check if texts are consistently aligned
        offsets = [tl["offset_from_center"] for tl in text_lines]
        if offsets:
            spread = max(offsets) - min(offsets)
            if spread > 20:
                lines.append(
                    f"  Note: text alignment varies by {spread:.0f}px"
                    f" across lines"
                )

    return "\n".join(lines)


@mcp.tool()
async def inspect_layout(
    script_path: str,
    frames: int = 5,
    timeout: int = 10,
) -> str:
    """Analyze screen layout, text alignment, and visual balance.

    Detects text positions, checks horizontal balance, and identifies
    centering issues. Use this to verify UI layout quality.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Frame number to analyze (default: 5).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    frames = max(1, min(frames, 1800))
    timeout = max(1, min(timeout, 60))

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, LAYOUT_HARNESS_PATH,
            script_path, str(frames),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        if proc.returncode != 0:
            error_msg = _decode_stderr(stderr) or "Unknown error"
            return f"Layout analysis failed (exit code {proc.returncode}): {error_msg}"

        data = json.loads(stdout.decode(errors="replace").strip())
        report = _format_layout_report(data)

        stderr_text = _decode_stderr(stderr)
        if stderr_text:
            report += f"\n\nstderr: {stderr_text}"
        return report

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return f"Timeout: script did not finish within {timeout}s"
    except json.JSONDecodeError as e:
        return f"Failed to parse layout data: {e}"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
