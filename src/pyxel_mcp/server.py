"""MCP server for Pyxel, a retro game engine for Python."""

import asyncio
import glob
import json
import os
import shutil
import sys
import tempfile
from importlib.util import find_spec

from mcp.server.fastmcp import FastMCP, Image

from pyxel_mcp._audio import analyze_wav
from pyxel_mcp._errors import decode_stderr, extract_stdout
from pyxel_mcp._format import (
    format_sprite_report,
    format_layout_report,
    format_state_report,
    format_state_timeline,
)
from pyxel_mcp._palette import color_name, color_contrast
from pyxel_mcp._validate import validate_source

HARNESS_PATH = os.path.join(os.path.dirname(__file__), "harness.py")
AUDIO_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "audio_harness.py")
SPRITE_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "sprite_harness.py")
FRAMES_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "frames_harness.py")
LAYOUT_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "layout_harness.py")
INPUT_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "input_harness.py")
STATE_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "state_harness.py")
SCREEN_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "screen_harness.py")
TILEMAP_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "tilemap_harness.py")
BANK_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "bank_harness.py")

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


_INSTRUCTIONS = """\
# Pyxel App Development

## Workflow

1. Call `pyxel_info` to locate API stubs and examples.
2. Read stubs for API details. Read examples for coding patterns (01-19, 99).
3. Write code.
4. Verify with tools:
   - `run_and_capture` after every visual change.
   - `render_audio` for each sound channel separately.
   - `play_and_capture` to test input-dependent logic (menus, movement).
   - `inspect_state` to debug logic bugs by inspecting variable values.
   - `validate_script` before running to catch syntax errors and anti-patterns.
   - `inspect_palette` to check color usage and contrast issues.
   - `inspect_tilemap` to verify tilemap content and detect (0,0) trap.
   - `inspect_bank` to see all sprites/tiles in an image bank.
   - `compare_frames` for visual regression testing between frames.
   - `inspect_screen` for compact color grid (no image tokens).
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
- **`inspect_layout` margin warnings**: Content not centered. Adjust screen size to \
match content, or reposition content to center it. Margins should be symmetric.
- **`validate_script` false positive**: Anti-pattern checks are heuristic. If a warning \
seems wrong, it's safe to ignore and run the script.
- **`inspect_tilemap` all zeros**: Tilemap not populated. Ensure `tilemaps[N].set()` runs \
before the game loop. Check `imgsrc` matches the image bank with tile data.

### Reading Tool Output

- **`run_and_capture`**: Returns a screenshot image. Visually verify layout, colors, \
and sprite positions.
- **`render_audio`**: Returns note sequence with timing/frequency. Check that notes \
match the intended melody and rhythm feels correct.
- **`inspect_sprite`**: Returns a pixel grid + symmetry report. Asymmetric pixels \
are listed by row — fix those coordinates in `images[N].set()`.
- **`inspect_layout`**: Returns margins, horizontal/vertical balance, quadrant \
density, center of mass, and text positions. Check margins for symmetry, \
balance > 70%, and quadrant distribution. Warnings (⚠) flag specific issues.
- **`capture_frames`**: Returns multiple screenshots. Compare frames to verify \
animation progresses smoothly without jumps or flicker.
- **`play_and_capture`**: Returns screenshots with simulated input. Verify that \
input causes expected state changes (player moved, menu changed, bullet spawned).
- **`inspect_state`**: Returns game object attributes at a specific frame. \
Check that variable values match expectations (score, position, game state). \
Use comma-separated frames for timeline diff: `frames="10,30,60"`.
- **`validate_script`**: Returns syntax errors and anti-pattern warnings. \
Run before `run_and_capture` to catch issues without Pyxel execution overhead.
- **`inspect_screen`**: Returns screen as hex color grid. \
Compact token usage. Good for programmatic comparison.
- **`compare_frames`**: Returns changed pixel count, percentage, and region \
between two frames. Use to verify only intended areas changed.
- **`inspect_palette`**: Returns color distribution and contrast warnings. \
Check that foreground colors have sufficient contrast against background.
- **`inspect_tilemap`**: Returns tile grid, usage stats, and bounding box. \
Check `imgsrc` matches your image bank. Verify (0,0) tiles are empty.
- **`inspect_bank`**: Returns image bank as screenshot (up to 256x256). \
Verify sprite/tile placement and find available space.

### Testing Input-Dependent Logic

Use `play_and_capture` to test input-dependent logic by simulating key presses:

```python
# Press SPACE at frame 30, release at frame 50, capture at frames 29,31,51
play_and_capture("game.py",
    inputs='[{"frame":30,"keys":["KEY_SPACE"]},{"frame":50,"keys":[]}]',
    frames="29,31,51")
```

Input events persist until changed by a later entry. Use this for:
- Menu navigation (KEY_RETURN to start, verify game screen)
- Movement (KEY_LEFT/RIGHT held for multiple frames)
- Shooting (KEY_SPACE press, check bullet spawns)
- Mouse clicks (set mouse_x/mouse_y with MOUSE_BUTTON_LEFT)

For simple one-shot tests, the frame-based trigger approach also works:
```python
# Original:  if pyxel.btnp(pyxel.KEY_SPACE): jump()
# Test:      if pyxel.frame_count == 30: jump()
```

### Debugging Game Logic

Use `inspect_state` to read variable values at a specific frame:

```python
inspect_state("game.py", frames="60", attributes="score,lives,player_x,player_y")
```

This captures the App instance (the class calling `pyxel.run()`) and dumps its \
attributes. Useful for:
- Physics bugs: check position/velocity values
- Score/state bugs: verify counter values
- Collision issues: check object positions relative to each other

Note: `inspect_state` does not support input simulation. It captures state at a \
given frame without any key presses. To test input-dependent logic, temporarily \
replace input conditions with frame-based triggers in the script, then revert.

### Letting the User Play

When suggesting the user run a script directly, check for a virtual environment \
(`.venv/bin/python` or similar) and include the full path in the command. \
Users may not have Pyxel installed globally.

## Pyxel Reference

Official docs (fetch for API details, usage guides, and syntax):
- API reference: https://raw.githubusercontent.com/kitao/pyxel/main/docs/api-reference.md
- User guide: https://raw.githubusercontent.com/kitao/pyxel/main/docs/user-guide.md
- MML commands: https://raw.githubusercontent.com/kitao/pyxel/main/docs/mml-commands.md
- Resource format: https://raw.githubusercontent.com/kitao/pyxel/main/docs/pyxres-format.md
- Local stubs and examples: call `pyxel_info`.
- User-created games: https://github.com/kitao/pyxel/wiki/Pyxel-User-Examples

## Essential Tips

Common gotchas not obvious from the API reference:

- `colkey`: transparent color index (e.g., `colkey=0` treats black as transparent)
- Negative `w` flips horizontally, negative `h` flips vertically in `blt()`
- Animation: `u = pyxel.frame_count // 4 % frame_count * SPRITE_W`
- `sin()`/`cos()` use **degrees**, not radians
- Font size: `FONT_WIDTH=4`, `FONT_HEIGHT=6`
- Use `btnp()` for one-shot actions, `btn()` for continuous hold
- Always call `pyxel.cls(col)` at the start of `draw()`
- Iterate over a copy when removing: `for e in list(enemies):`

### Beyond Defaults

Pyxel's default resource slots (3 images, 8 tilemaps, 64 sounds, etc.) are \
starting points, not hard limits. All global lists (`images`, `tilemaps`, \
`sounds`, `musics`, `channels`, `tones`, `colors`) support `append()` and \
slice assignment to grow beyond defaults.

| Feature | How | Example |
|---------|-----|---------|
| Custom-size images | `Image(w, h)`, `Image.from_image(file)` | Offscreen rendering (ex. 11) |
| Custom-size tilemaps | `Tilemap(w, h, img)`, `Tilemap.from_tmx(file, layer)` | Large maps, Tiled editor (ex. 15) |
| More sounds/musics | `Sound()`, `Music()` as standalone instances | Beyond 64/8 slot limit |
| More channels | `Channel()` with gain/detune, append to `pyxel.channels` | Polyphony expansion (ex. 14) |
| Custom waveforms | `Tone()` with wavetable, append to `pyxel.tones` | Synth sounds (ex. 14) |
| Extended palette | `pyxel.colors.append(0xRRGGBB)` — up to 256 colors | Richer color range (ex. 05) |
| Custom fonts | `Font(file, size)` — BDF/OTF/TTF/TTC | Japanese text, styled text (ex. 13) |
| Audio file playback | `Sound.pcm("file.wav")` — WAV/OGG | BGM from audio files (ex. 18) |
| Rotation & scaling | `blt(..., rotate=deg, scale=n)` | Sprite transforms (ex. 16) |
| 3D perspective | `blt3d()`, `bltm3d()` with camera pos/rot/fov | Pseudo-3D rendering (ex. 19) |

Suggest these when users hit default limits or need features like \
multilingual text, richer audio, larger worlds, or visual effects. \
See the referenced examples for working code.

### Audio Channel Management

Pyxel defaults to 4 audio channels (0-3), but more can be added via \
`pyxel.channels.append(Channel())`. `playm()` assigns music tracks to channels \
starting from ch0. `play(ch, snd)` on the same channel **interrupts** the music \
on that channel. Plan channel allocation to avoid BGM/SE conflicts:

- **BGM on ch0-2, SE on ch3**: Use 3-channel music so SE never interrupts BGM.
- **Title/menu screens**: Can safely use all 4 channels for BGM (no frequent SE).
- Use `resume=True` for non-critical SE to avoid cutting off other sounds.

### Tilemap Gotchas

**Important**: All tilemap cells default to tile (0, 0). Keep position (0, 0) in the \
image bank empty (transparent) — if you place a visible tile there, it fills the \
entire tilemap as background.

If tiles are in a different image bank than sprites, set `imgsrc`:

```python
pyxel.tilemaps[0].imgsrc = 1  # draw tiles from image bank 1
```

### MML Composition Guide

Structure BGM as 3 channels: melody (ch0), bass (ch1), harmony/arpeggio (ch2). \
Reserve ch3 for SE. Use `render_audio` to verify each channel separately.

**3-channel template:**

```python
# Ch0: Melody — carries the theme
pyxel.sounds[10].mml("T120 @1 V80 L8 O4 [CEGC>C<BAGFEDC R4]2")
# Ch1: Bass — root notes, steady rhythm
pyxel.sounds[11].mml("T120 @0 V60 L4 O2 [CC8C8 GG8G8 AA8A8 FF8F8]2")
# Ch2: Arpeggio — fills space, adds texture
pyxel.sounds[12].mml("T120 @1 V40 L16 O4 [CEGCEGCEGCEG <B>DG<B>DG<B>DG<B>DG]2")
pyxel.musics[0].set([10], [11], [12])
```

**Genre moods by key and tempo:**

| Genre | Key | Tempo | Tones | Tips |
|-------|-----|-------|-------|------|
| Action/Gothic | A- minor, C minor | T100-120 | @1 melody, @0 bass | Use E-/A-/B- for dark feel, 8th note arpeggios |
| Adventure | C major, G major | T120-140 | @1 melody, @0 bass | Ascending phrases for heroic mood |
| Puzzle/Calm | F major | T80-100 | @0 melody, @1 harmony | Dotted notes, gentle tempo |
| Horror | B- minor | T60-80 | @2 melody, @3 accents | Half notes, chromatic movement, sparse |
| Boss battle | E minor | T140-160 | @1 melody, @0 bass | Driving 16th bass, syncopated melody |

### Quick BGM

`gen_bgm` generates procedural music — great for rapid iteration, but all outputs \
share a similar flavor. Combine with hand-written MML for variety.

```python
# See API reference for gen_bgm preset/instr details
# Returns 4 MML strings — drop ch3 if you need it for SE

# Example: 3-channel BGM (reserve ch3 for SE)
mml = pyxel.gen_bgm(7, 1, seed=42)
for i in range(3):
    pyxel.sounds[10 + i].mml(mml[i])
pyxel.musics[0].set([10], [11], [12])

# Quick play (uses all 4 channels — good for title screens)
pyxel.gen_bgm(preset, instr, seed=42, play=True)

# Scene-specific BGM — vary preset/seed per scene for distinct moods
def play_bgm(self, scene):
    BGM = {
        "title":    (0, 1, 100),  # title/departure, melody+bass+drums
        "game":     (4, 2, 200),  # field/adventure, melody+sub+bass
        "boss":     (7, 1, 300),  # battle/crisis, melody+bass+drums
        "gameover": (2, 0, 400),  # town/peaceful, melody+reverb+bass
    }
    preset, instr, seed = BGM[scene]
    mml = pyxel.gen_bgm(preset, instr, seed=seed)
    for i in range(3):
        pyxel.sounds[60 + i].mml(mml[i])
    pyxel.musics[0].set([60], [61], [62])
    pyxel.playm(0, loop=True)
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

### Sprite Design Process

Never use a single static frame for the player. Follow this minimum standard:

1. **Silhouette first**: Draw the outline in black (0). The shape must read clearly at 1x zoom.
2. **Fill base color**: One color per material region (skin, armor, cloth).
3. **Add shadow/highlight**: Using the 3-color-per-material table above.
4. **Required sprite images** (minimum distinct images to draw per state):

| Character | Required States | Images Each |
|-----------|----------------|-------------|
| Player (platformer) | idle, walk, jump, attack | idle:1, walk:2, jump:1, attack:1 = **5 min** |
| Player (shmup) | idle, bank-left, bank-right | 1 each = **3 min** |
| Player (RPG) | idle, walk-down, walk-side | idle:1, walk:2 each = **5 min** |
| Enemy (ground) | walk | 2 frames min |
| Enemy (flying) | flap | 2 frames min |

Place animation frames adjacent horizontally in the image bank. Use `inspect_sprite` after each sprite to verify quality.

Design **original** sprites for each game — never reuse the same design across projects.

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

### Genre Background Recipes

Each recipe builds atmosphere with layered elements. Implement at least 2 layers.

**Castle/Dungeon interior:**
- cls(1) navy base
- Far layer (1/3 speed): window rectangles with warm glow (color 5 frame, 9 inner)
- Mid layer: torch brackets (sprite) with flickering flame (pset, alternate 9/10)
- Tile layer: varied wall tiles (stone + brick + dark stone), pillar decorations
- Atmosphere: chain sprites on walls, occasional dripping particle

**Forest/Outdoor:**
- cls(1) or cls(5) sky
- Far layer (1/4 speed): mountain silhouettes (tri, color 1)
- Mid layer (1/2 speed): tree canopy shapes (circ clusters, color 3)
- Near layer: bushes, grass detail tiles
- Atmosphere: leaf particles drifting down, birds (small sprites)

**Space/Shmup:**
- cls(0) black
- Star field: 30+ pset at random positions, 3 brightness tiers
- Twinkling: `if (sx + frame_count) % 60 < 5: brighter`
- Nebula: dither(0.3) + large circ in color 2 or 5

### Parallax Scrolling

Draw layers back-to-front with different scroll speeds:

```python
# Layer speeds (general principle)
# Layer 1 (far):    offset = scroll // 4   (or frame_count // 4 for auto-scroll)
# Layer 2 (mid):    offset = scroll // 2
# Layer 3 (near):   offset = scroll        (1:1 with camera)

# Parallax with camera offset (side-scroller)
far_offset = camera_x // 3
mid_offset = camera_x // 2
# Draw far objects at (x + far_offset % spacing - spacing, y)
# Draw mid objects at (x + mid_offset % spacing - spacing, y)

# Auto-scroll parallax (shmup / title screen)
for i in range(20):
    x = (i * 40 - pyxel.frame_count // 2) % (pyxel.width + 20) - 10
    pyxel.circ(x, 20, 6, 1)   # far clouds (slow)
for i in range(10):
    x = (i * 50 - pyxel.frame_count) % (pyxel.width + 20) - 10
    pyxel.circ(x, 40, 10, 5)  # near clouds (fast)

# Seamless wrap for tilemap-based parallax:
for i in range(2):
    pyxel.blt(i * pyxel.width - offset % pyxel.width, y,
              0, u, v, pyxel.width, h, colkey=0)
```

## Screen & Text Layout

**Derive screen size from content — never start with a fixed size like 160x120.** \
Calculate the play area, panels, and margins first, then set `pyxel.init(SCR_W, SCR_H)`.

```python
# Step 1: Define content dimensions
CELL = 6
COLS, ROWS = 10, 20
BOARD_W = COLS * CELL          # 60px
BOARD_H = ROWS * CELL          # 120px
PANEL_W = 48
MARGIN = 4
GAP = 6

# Step 2: Derive screen size from content
SCR_W = MARGIN + BOARD_W + GAP + PANEL_W + MARGIN   # content drives size
SCR_H = MARGIN + BOARD_H + MARGIN

# Step 3: Position regions
BOARD_X = MARGIN
BOARD_Y = MARGIN
PANEL_X = BOARD_X + BOARD_W + GAP

pyxel.init(SCR_W, SCR_H, title="My Game")
```

Layout rules:
- **Content-first sizing**: Define game area, panels, margins as constants. Derive \
screen size from their sum. Never pick an arbitrary screen size and try to fit content.
- **Center the play area**: For games without side panels, center both axes: \
`GAME_X = (SCR_W - GAME_W) // 2; GAME_Y = (SCR_H - GAME_H) // 2`.
- **Symmetric margins**: Left ≈ right, top ≈ bottom. Compute with `(SCR_W - content_w) // 2`.
- **No overlap**: HUD must not intrude into the play area.
- **Verify with `inspect_layout`**: Fix all ⚠ warnings. Margins should be symmetric \
(ratio < 2x), balance > 70% on both axes, no near-empty quadrants.

### Text Positioning

Always **calculate** text positions. Font: `FONT_WIDTH=4`, `FONT_HEIGHT=6`.

```python
# Horizontal centering
x = (pyxel.width - len(text) * pyxel.FONT_WIDTH) // 2

# Vertical centering of N lines
block_h = N * pyxel.FONT_HEIGHT + (N - 1) * spacing
y = (pyxel.height - block_h) // 2

# Text shadow for readability
pyxel.text(x + 1, y + 1, s, 1)  # shadow
pyxel.text(x, y, s, 7)          # foreground
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

### Game Over

```python
pyxel.sounds[4].set(
    notes="f3b2f2b1f1f1f1f1", tones="p",
    volumes="44444321", effects="nnnnnnnf", speed=9,
)
```

Design other SE (explosion, menu, power-up, landing, shoot) using the rules above.

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

### Level Design

Never place platforms, enemies, or items randomly. Every placement serves a purpose.

**Zone-based structure** — divide the map into 3-5 zones with escalating challenge:

| Zone | Purpose | Elements |
|------|---------|----------|
| 1 (Start) | Teach mechanics safely | Wide platforms, 1 weak enemy, first item |
| 2 (Build) | Introduce combinations | Narrower gaps, 2 enemy types, vertical platforms |
| 3 (Challenge) | Test skill | Enemies on platforms, timed jumps, fewer items |
| 4 (Climax) | Peak difficulty | Multiple hazards at once, tight spacing |
| 5 (Reward) | Resolution | Boss or clear condition, generous items |

**Pacing rules:**
- After a hard section, add a brief safe zone (empty platform, health item)
- First enemy encounter should be solvable without jumping
- Candles/items near new mechanics hint at the correct approach
- Place checkpoints (candles/hearts) before difficult jumps, not after

**Enemy placement:**
- Ground enemies on flat ground (never floating in air)
- Flying enemies in open vertical space (not crammed in corridors)
- Never place enemies where the player spawns or lands from a required jump
- Pair enemies with terrain: skeleton patrols platform edges, bats guard gaps

### Enemy Design

Every enemy needs: a **behavior pattern**, **visual distinction** from the player, \
and at least **2 animation frames**.

| Pattern | Movement | Good For | Example |
|---------|----------|----------|---------|
| Patrol | Walk left/right, turn at edges | Ground enemies | Skeleton, Slime |
| Sine float | Sinusoidal Y + X orbit around base | Flying enemies | Bat, Ghost |
| Chase | Move toward player when in range | Aggressive enemies | Ghost, Dog |
| Stationary | Fixed position, fires projectiles | Turrets, traps | Cannon, Spike |
| Swoop | Hover, then dive at player | Air enemies | Eagle, Demon |

```python
# Patrol: turn at platform edges
e["x"] += e["vx"]
if not tile_solid(edge_x, below_y):  # no ground ahead
    e["vx"] = -e["vx"]              # reverse

# Chase: drift toward player within range
if abs(player_x - e["x"]) < 100:
    e["x"] += (player_x - e["x"]) * 0.01

# Sine float: orbit around base position (never use += for x/y)
e["x"] = e["base_x"] + pyxel.sin(pyxel.frame_count * 2) * 16
e["y"] = e["base_y"] + pyxel.sin(pyxel.frame_count * 4) * 12
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

### Hitbox Design

- **Hazards**: hitbox **smaller** than sprite (forgiving)
- **Rewards/Stomp targets**: hitbox matches sprite (accurate)
- Player: use 60-75% of sprite size as hitbox (e.g., 6x6 for 8x8 sprite)
- `abs(a.x - b.x) < HIT_W and abs(a.y - b.y) < HIT_H`

### Camera (Side-Scroller)

```python
# Smooth follow (lerp)
camera_x += (player_x - camera_x - pyxel.width // 2) * 0.1
# 0.1 = smooth, 0.2 = responsive, 0.05 = cinematic
```

## Animation Timing

Recommended sprite image counts for smooth animation (ideal targets; \
see Sprite Design Process for minimums):

| Animation | Sprite Images | Speed (game frames per image) |
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

### State-Based Animator

For games with multiple character states (idle, walk, attack), use a state-machine \
animator instead of inline frame math:

```python
SPRITE_W, SPRITE_H = 8, 8  # adjust to match your sprite size

class Animator:
    ANIMS = {
        "idle":   {"u": 0,  "frames": 2, "speed": 20, "loop": True},
        "walk":   {"u": 16, "frames": 4, "speed": 5,  "loop": True},
        "attack": {"u": 48, "frames": 3, "speed": 4,  "loop": False},
        "jump":   {"u": 72, "frames": 2, "speed": 6,  "loop": False},
    }

    def __init__(self):
        self.state = "idle"
        self.tick = 0
        self.flip = False  # True = face left

    def set(self, state):
        if state != self.state:
            self.state = state
            self.tick = 0

    def update(self):
        anim = self.ANIMS[self.state]
        self.tick += 1
        if self.tick >= anim["frames"] * anim["speed"]:
            if anim["loop"]:
                self.tick = 0
            else:
                self.tick = anim["frames"] * anim["speed"] - 1

    def draw(self, x, y):
        anim = self.ANIMS[self.state]
        frame = self.tick // anim["speed"]
        u = anim["u"] + frame * SPRITE_W
        w = -SPRITE_W if self.flip else SPRITE_W
        pyxel.blt(x, y, 0, u, 0, w, SPRITE_H, colkey=0)
```

Usage: call `animator.set("walk")` on state change, `animator.update()` every frame, \
`animator.draw(x, y)` in draw. Set `animator.flip = True` to face left.

## Quality Checklist

Quick-reference of common mistakes. See linked sections for details.

| Category | Don't | Do |
|----------|-------|----|
| Layout | Pick screen size first, then fit content | Derive screen size from content + margins |
| Layout | Ignore inspect_layout warnings | Fix all ⚠ warnings before proceeding |
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
| Audio | Only gen_bgm, no MML | Mix gen_bgm with hand-written MML for variety |
| Sprite | Single static player frame | Min 5 images (idle/walk:2/jump/attack) |
| Sprite | Single static enemy frame | Min 2 animation frames per enemy |
| Level | Random platform placement | Zone-based progression (see Level Design) |
| Level | Enemies floating in void | Ground enemies on ground, flyers in open space |

Before release, verify: BGM present (MML or gen_bgm), distinct SE for all events, \
title screen with animation, game over with score, non-solid background, \
HUD with score/lives, player has walk animation, enemies have 2+ frames.
"""

mcp = FastMCP("pyxel-mcp", instructions=_INSTRUCTIONS)


@mcp.tool()
async def run_and_capture(
    script_path: str,
    frames: int = 60,
    scale: int = 1,
    timeout: int = 10,
) -> list:
    """Run a Pyxel script and capture a screenshot after N frames.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Number of frames to render before capturing (default: 60).
        scale: Screenshot scale multiplier (default: 1).
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
            error_msg = decode_stderr(stderr) or "Unknown error"
            return [f"Capture failed (exit code {proc.returncode}): {error_msg}"]

        with open(output_path, "rb") as f:
            image_data = f.read()
        result = [Image(data=image_data, format="png")]
        info = f"Captured at frame {frames}, scale {scale}x"
        stderr_text = decode_stderr(stderr)
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


@mcp.tool()
async def render_audio(
    script_path: str,
    sound_index: int = 0,
    duration_sec: float = 0,
    timeout: int = 10,
    music_index: int = -1,
) -> str:
    """Render a Pyxel sound or music to WAV and return waveform analysis.

    Runs the script to set up sounds (without starting the game loop),
    then renders the specified sound or music to WAV and analyzes the audio.
    Returns note sequence with timing, frequency, and volume data.

    Args:
        script_path: Absolute path to the .py script to run.
        sound_index: Sound slot index (default: 0). Default range 0-63,
            but lists can be extended via append(). Ignored when music_index is set.
        duration_sec: Duration in seconds. 0 = auto-detect from sound length (10s for music).
        timeout: Maximum seconds to wait for the script (default: 10).
        music_index: Music slot index. Default range 0-7, extendable.
            When set (>=0), renders the full multi-channel music mix instead of a single sound.
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    sound_index = max(0, sound_index)
    music_index = max(-1, music_index)
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
            str(duration_sec) if duration_sec > 0 else "0",
        ]
        if music_index >= 0:
            args.append(str(music_index))

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
            error_msg = decode_stderr(stderr) or "Unknown error"
            return f"Render failed (exit code {proc.returncode}): {error_msg}"

        meta = {}
        user_output = ""
        if stdout:
            try:
                json_str, user_output = extract_stdout(stdout)
                meta = json.loads(json_str) if json_str else {}
            except (json.JSONDecodeError, ValueError):
                pass

        try:
            analysis = await asyncio.to_thread(analyze_wav, output_path)
        except Exception as e:
            analysis = f"WAV analysis failed: {e}"

        if music_index >= 0:
            result = (
                f"Music {music_index} rendered"
                f" ({meta.get('duration_sec', '?')}s,"
                f" {meta.get('num_channels', '?')} channels)\n\n{analysis}"
            )
        else:
            result = (
                f"Sound {sound_index} rendered"
                f" ({meta.get('duration_sec', '?')}s,"
                f" speed={meta.get('speed', '?')})\n\n{analysis}"
            )
        if user_output:
            result = f"Script output:\n{user_output}\n\n{result}"
        stderr_text = decode_stderr(stderr)
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
        image: Image bank index (default: 0). Default range 0-2, extendable.
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

    image = max(0, image)
    x = max(0, x)
    y = max(0, y)
    w = max(1, w)
    h = max(1, h)
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
            error_msg = decode_stderr(stderr) or "Unknown error"
            return f"Inspect failed (exit code {proc.returncode}): {error_msg}"

        json_str, user_output = extract_stdout(stdout)
        data = json.loads(json_str)
        report = format_sprite_report(data)

        if user_output:
            report = f"Script output:\n{user_output}\n\n{report}"
        stderr_text = decode_stderr(stderr)
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
    scale: int = 1,
    timeout: int = 30,
) -> list:
    """Capture screenshots at multiple frame points for animation verification.

    Returns multiple images captured at specified frame numbers.
    Useful for verifying animations, transitions, and time-based effects.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Comma-separated frame numbers to capture (default: "1,15,30,60").
        scale: Screenshot scale multiplier (default: 1).
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
            error_msg = decode_stderr(stderr) or "No frames captured"
            return [f"Capture failed (exit code {proc.returncode}): {error_msg}"]

        stderr_text = decode_stderr(stderr)
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


# --- Input simulation ---


@mcp.tool()
async def play_and_capture(
    script_path: str,
    inputs: str,
    frames: str = "1,30,60",
    scale: int = 1,
    timeout: int = 30,
) -> list:
    """Play a game by sending simulated input and capture screenshots.

    Simulates keyboard/mouse input at specific frames and captures screenshots
    at specified frame points. Use this to test input-dependent game logic
    (menus, movement, shooting) without manual play.

    Args:
        script_path: Absolute path to the .py script to run.
        inputs: JSON array of input events. Each event:
            {"frame": N, "keys": ["KEY_SPACE", ...], "mouse_x": X, "mouse_y": Y}
            Keys are held from their frame until a later entry changes them.
            Default state: no keys pressed, mouse at (0,0).
        frames: Comma-separated frame numbers to capture screenshots (default: "1,30,60").
        scale: Screenshot scale multiplier (default: 1).
        timeout: Maximum seconds to wait for the script (default: 30).
    """
    if not _pyxel_dir():
        return ["Error: Pyxel is not installed. Run: pip install pyxel-mcp"]

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return [f"Error: script not found: {script_path}"]

    try:
        input_data = json.loads(inputs)
        if not isinstance(input_data, list):
            return ["Error: inputs must be a JSON array"]
    except json.JSONDecodeError as e:
        return [f"Error: invalid inputs JSON: {e}"]

    try:
        frame_list = [max(1, min(int(f.strip()), 1800)) for f in frames.split(",")]
    except ValueError:
        return ["Error: frames must be comma-separated integers (e.g. '1,30,60')"]

    frame_list = sorted(set(frame_list))
    if not frame_list:
        return ["Error: no valid frame numbers provided"]

    scale = max(1, min(scale, 10))
    timeout = max(1, min(timeout, 120))

    output_dir = tempfile.mkdtemp(prefix="pyxel_input_")
    input_tmp = None

    try:
        # Write input schedule to temp file
        fd, input_tmp = tempfile.mkstemp(prefix="pyxel_input_", suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(input_data, f)

        frame_csv = ",".join(str(f) for f in frame_list)
        proc = await asyncio.create_subprocess_exec(
            sys.executable, INPUT_HARNESS_PATH,
            script_path, output_dir, frame_csv, str(scale), input_tmp,
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
            show_path = os.path.join(output_dir, "frame_show.png")
            if os.path.isfile(show_path):
                with open(show_path, "rb") as f:
                    result.append(Image(data=f.read(), format="png"))
                result.append("Captured via pyxel.show()")

        if not result:
            error_msg = decode_stderr(stderr) or "No frames captured"
            return [f"Capture failed (exit code {proc.returncode}): {error_msg}"]

        stderr_text = decode_stderr(stderr)
        info = f"Captured {len([r for r in result if isinstance(r, Image)])} frames"
        n_inputs = len(input_data)
        info += f" with {n_inputs} input event{'s' if n_inputs != 1 else ''}"
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
        if input_tmp and os.path.isfile(input_tmp):
            os.unlink(input_tmp)


# --- Layout analysis ---


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
            error_msg = decode_stderr(stderr) or "Unknown error"
            return f"Layout analysis failed (exit code {proc.returncode}): {error_msg}"

        json_str, user_output = extract_stdout(stdout)
        data = json.loads(json_str)
        report = format_layout_report(data)

        if user_output:
            report = f"Script output:\n{user_output}\n\n{report}"
        stderr_text = decode_stderr(stderr)
        if stderr_text:
            report += f"\n\nstderr: {stderr_text}"
        return report

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return f"Timeout: script did not finish within {timeout}s"
    except json.JSONDecodeError as e:
        return f"Failed to parse layout data: {e}"


# --- State inspection ---


@mcp.tool()
async def inspect_state(
    script_path: str,
    frames: str = "60",
    attributes: str = "",
    timeout: int = 10,
) -> str:
    """Read game object attributes at specific frames for debugging.

    Captures the App instance (the class that calls pyxel.run()) and
    dumps its attributes as JSON. Supports single frame or comma-separated
    multi-frame timeline with automatic diff between frames.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Frame number(s) to inspect, comma-separated (default: "60").
            Use multiple frames for timeline diff: "10,30,60"
        attributes: Comma-separated attribute names to inspect (default: all).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    try:
        frame_list = [max(1, min(int(f.strip()), 1800)) for f in frames.split(",")]
    except ValueError:
        return "Error: frames must be comma-separated integers"

    frame_list = sorted(set(frame_list))
    timeout = max(1, min(timeout, 60))

    frame_csv = ",".join(str(f) for f in frame_list)
    args = [sys.executable, STATE_HARNESS_PATH, script_path, frame_csv]
    if attributes.strip():
        attr_list = [a.strip() for a in attributes.split(",") if a.strip()]
        args.append(json.dumps(attr_list))

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        if proc.returncode != 0:
            error_msg = decode_stderr(stderr) or "Unknown error"
            return f"State inspection failed (exit code {proc.returncode}): {error_msg}"

        json_str, user_output = extract_stdout(stdout)
        data = json.loads(json_str)

        if isinstance(data, list):
            report = format_state_timeline(data)
        else:
            report = format_state_report(data)

        if user_output:
            report = f"Script output:\n{user_output}\n\n{report}"

        stderr_text = decode_stderr(stderr)
        if stderr_text:
            report += f"\n\nstderr: {stderr_text}"
        return report

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return f"Timeout: script did not finish within {timeout}s"
    except json.JSONDecodeError as e:
        return f"Failed to parse state data: {e}"


# --- Script validation ---


@mcp.tool()
async def validate_script(script_path: str) -> str:
    """Validate a Pyxel script without running it.

    Performs AST parsing and checks for common Pyxel anti-patterns.
    Much faster than run_and_capture for catching syntax errors and
    obvious mistakes before execution.

    Args:
        script_path: Absolute path to the .py script to validate.
    """
    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    try:
        with open(script_path) as f:
            source = f.read()
    except Exception as e:
        return f"Error reading file: {e}"

    return validate_source(source, os.path.basename(script_path))


# --- Screen analysis ---


async def _run_screen_harness(script_path, frame_csv, timeout=10):
    """Run screen_harness and return parsed JSON + user output."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, SCREEN_HARNESS_PATH,
        script_path, frame_csv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=os.path.dirname(script_path),
    )
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(), timeout=timeout
    )
    if proc.returncode != 0:
        error_msg = decode_stderr(stderr) or "Unknown error"
        raise RuntimeError(
            f"Screen capture failed (exit code {proc.returncode}): {error_msg}"
        )
    json_str, user_output = extract_stdout(stdout)
    data = json.loads(json_str)
    return data, user_output, decode_stderr(stderr)


@mcp.tool()
async def inspect_screen(
    script_path: str,
    frames: int = 5,
    timeout: int = 10,
) -> str:
    """Capture screen as a compact color index grid.

    Returns the screen contents as a 2D array of Pyxel palette indices
    (0-15 for default palette, higher with extended colors). Much smaller
    than a screenshot image and enables programmatic comparison.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Frame number to capture (default: 5).
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
        data, user_output, stderr_text = await _run_screen_harness(
            script_path, str(frames), timeout
        )
    except (RuntimeError, json.JSONDecodeError) as e:
        return str(e)
    except asyncio.TimeoutError:
        return f"Timeout: script did not finish within {timeout}s"

    snap = data[0] if isinstance(data, list) else data
    w, h = snap["width"], snap["height"]
    grid = snap["grid"]

    lines = [f"Screen {w}x{h} at frame {snap['frame']}"]
    lines.append("")
    has_extended = any(c > 15 for row in grid for c in row)
    for row in grid:
        if has_extended:
            lines.append(" ".join(f"{c:02x}" for c in row))
        else:
            lines.append("".join(f"{c:x}" for c in row))

    result = "\n".join(lines)
    if user_output:
        result = f"Script output:\n{user_output}\n\n{result}"
    if stderr_text:
        result += f"\n\nstderr: {stderr_text}"
    return result


@mcp.tool()
async def compare_frames(
    script_path: str,
    frame_a: int = 1,
    frame_b: int = 30,
    timeout: int = 15,
) -> str:
    """Compare screenshots at two frames and report pixel differences.

    Captures the screen as color grids at two frames and computes a diff.
    Returns changed pixel count, percentage, and which screen regions changed.
    Use this for visual regression testing.

    Args:
        script_path: Absolute path to the .py script to run.
        frame_a: First frame number (default: 1).
        frame_b: Second frame number (default: 30).
        timeout: Maximum seconds to wait for the script (default: 15).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    frame_a = max(1, min(frame_a, 1800))
    frame_b = max(1, min(frame_b, 1800))
    if frame_a == frame_b:
        return "Error: frame_a and frame_b must be different"
    timeout = max(1, min(timeout, 60))

    frame_csv = f"{frame_a},{frame_b}"

    try:
        data, user_output, stderr_text = await _run_screen_harness(
            script_path, frame_csv, timeout
        )
    except (RuntimeError, json.JSONDecodeError) as e:
        return str(e)
    except asyncio.TimeoutError:
        return f"Timeout: script did not finish within {timeout}s"

    if len(data) < 2:
        return "Error: could not capture both frames"

    snap_a, snap_b = data[0], data[1]
    w, h = snap_a["width"], snap_a["height"]
    grid_a, grid_b = snap_a["grid"], snap_b["grid"]

    # Compute diff
    changed = 0
    total = w * h
    min_x, min_y = w, h
    max_x, max_y = -1, -1
    changed_colors = {}

    for y in range(h):
        for x in range(w):
            if grid_a[y][x] != grid_b[y][x]:
                changed += 1
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
                key = f"{grid_a[y][x]:x}->{grid_b[y][x]:x}"
                changed_colors[key] = changed_colors.get(key, 0) + 1

    pct = changed / total * 100 if total > 0 else 0
    lines = [
        f"Frame {snap_a['frame']} vs {snap_b['frame']} ({w}x{h})",
        f"Changed pixels: {changed}/{total} ({pct:.1f}%)",
    ]

    if changed == 0:
        lines.append("Frames are identical.")
    else:
        lines.append(
            f"Changed region: ({min_x},{min_y}) to ({max_x},{max_y})"
            f" = {max_x - min_x + 1}x{max_y - min_y + 1}px"
        )
        lines.append("")
        lines.append("Color transitions (top 10):")
        for trans, count in sorted(changed_colors.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  {trans}: {count}px")

    result = "\n".join(lines)
    if user_output:
        result = f"Script output:\n{user_output}\n\n{result}"
    if stderr_text:
        result += f"\n\nstderr: {stderr_text}"
    return result


@mcp.tool()
async def inspect_palette(
    script_path: str,
    frames: int = 5,
    timeout: int = 10,
) -> str:
    """Analyze color usage and contrast in a Pyxel screenshot.

    Captures the screen and reports which colors are used, their
    distribution, background color, and potential contrast issues.
    Supports both default 16-color and extended palettes.

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
        data, user_output, stderr_text = await _run_screen_harness(
            script_path, str(frames), timeout
        )
    except (RuntimeError, json.JSONDecodeError) as e:
        return str(e)
    except asyncio.TimeoutError:
        return f"Timeout: script did not finish within {timeout}s"

    snap = data[0] if isinstance(data, list) else data
    w, h = snap["width"], snap["height"]
    grid = snap["grid"]
    total = w * h

    # Count colors
    counts = {}
    for row in grid:
        for c in row:
            counts[c] = counts.get(c, 0) + 1

    # Detect background (most common color)
    bg_color = max(counts, key=counts.get)
    bg_name = color_name(bg_color)
    fg_colors = {c for c in counts if c != bg_color}

    lines = [
        f"Palette analysis at frame {snap['frame']} ({w}x{h})",
        f"Background: {bg_color:x} ({bg_name}) — {counts[bg_color]}/{total} pixels"
        f" ({counts[bg_color] / total * 100:.0f}%)",
        f"Colors used: {len(counts)}",
        "",
        "Color distribution:",
    ]

    for c in sorted(counts, key=counts.get, reverse=True):
        name = color_name(c)
        pct = counts[c] / total * 100
        bar = "#" * max(1, int(pct / 2))
        lines.append(f"  {c:x} ({name:10s}): {counts[c]:6d}px ({pct:5.1f}%) {bar}")

    # Contrast warnings
    warnings = []
    for c in fg_colors:
        ratio = color_contrast(c, bg_color)
        if ratio < 1.5:
            name = color_name(c)
            warnings.append(
                f"  Low contrast: {c:x}({name}) on {bg_color:x}({bg_name})"
                f" — ratio {ratio:.1f}:1"
            )

    unused = [c for c in range(16) if c not in counts]
    if unused:
        lines.append(f"\nUnused colors: {', '.join(f'{c:x}' for c in unused)}")

    if warnings:
        lines.append("\nContrast warnings:")
        lines.extend(warnings)

    result = "\n".join(lines)
    if user_output:
        result = f"Script output:\n{user_output}\n\n{result}"
    if stderr_text:
        result += f"\n\nstderr: {stderr_text}"
    return result


# --- Tilemap inspection ---


@mcp.tool()
async def inspect_tilemap(
    script_path: str,
    tilemap: int = 0,
    frames: int = 1,
    timeout: int = 10,
) -> str:
    """Inspect tilemap content, tile usage, and layout.

    Reads tilemap data and reports tile grid, usage statistics,
    bounding box of non-empty tiles, and imgsrc setting.

    Args:
        script_path: Absolute path to the .py script to run.
        tilemap: Tilemap index (default: 0). Default range 0-7, extendable.
        frames: Frame at which to read tilemap (default: 1).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    tilemap = max(0, tilemap)
    frames = max(1, min(frames, 1800))
    timeout = max(1, min(timeout, 60))

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, TILEMAP_HARNESS_PATH,
            script_path, str(tilemap), str(frames),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        if proc.returncode != 0:
            error_msg = decode_stderr(stderr) or "Unknown error"
            return f"Tilemap inspection failed (exit code {proc.returncode}): {error_msg}"

        json_str, user_output = extract_stdout(stdout)
        data = json.loads(json_str)

        lines = [
            f"Tilemap {data['tilemap_index']} ({data['width']}x{data['height']} tiles)",
            f"Image source: {data['imgsrc']}" if not isinstance(data['imgsrc'], int) else f"Image source: bank {data['imgsrc']}",
            f"Non-zero tiles: {data['non_zero_tiles']}/{data['total_scanned']}"
            f" ({data['unique_tiles']} unique)",
        ]

        bbox = data.get("bbox")
        if bbox:
            lines.append(
                f"Content bounds: ({bbox['x']},{bbox['y']})"
                f" {bbox['w']}x{bbox['h']} tiles"
            )
            lines.append("")
            lines.append("Tile grid (within bounds):")
            for row in data["tiles"]:
                cells = []
                for tile in row:
                    if tile == [0, 0]:
                        cells.append("  . ")
                    else:
                        cells.append(f"{tile[0]:2d},{tile[1]:<1d}")
                lines.append("  " + " ".join(cells))
        else:
            lines.append("Tilemap is empty (all tiles are (0,0)).")

        lines.append("")
        lines.append("Tile usage (top entries):")
        for key, count in list(data["tile_usage"].items())[:15]:
            lines.append(f"  ({key}): {count} tiles")

        result = "\n".join(lines)
        if user_output:
            result = f"Script output:\n{user_output}\n\n{result}"
        stderr_text = decode_stderr(stderr)
        if stderr_text:
            result += f"\n\nstderr: {stderr_text}"
        return result

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return f"Timeout: script did not finish within {timeout}s"
    except json.JSONDecodeError as e:
        return f"Failed to parse tilemap data: {e}"


# --- Image bank visualization ---


@mcp.tool()
async def inspect_bank(
    script_path: str,
    bank: int = 0,
    scale: int = 1,
    timeout: int = 10,
) -> list:
    """Visualize a Pyxel image bank as a single screenshot.

    Renders up to 256x256 pixels of an image bank, showing sprites and
    tiles at once. Useful for verifying sprite sheet organization and
    finding available space. Custom images larger than 256x256 are cropped.

    Args:
        script_path: Absolute path to the .py script to run.
        bank: Image bank index (default: 0). Default range 0-2, extendable.
        scale: Screenshot scale multiplier (default: 1).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return ["Error: Pyxel is not installed. Run: pip install pyxel-mcp"]

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return [f"Error: script not found: {script_path}"]

    bank = max(0, bank)
    scale = max(1, min(scale, 4))
    timeout = max(1, min(timeout, 60))

    output_dir = tempfile.mkdtemp(prefix="pyxel_bank_")
    output_path = os.path.join(output_dir, "bank.png")

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, BANK_HARNESS_PATH,
            script_path, output_path, str(bank), str(scale),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        result = []
        if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
            with open(output_path, "rb") as f:
                result.append(Image(data=f.read(), format="png"))
            result.append(f"Image bank {bank} (up to 256x256 pixels)")
        else:
            error_msg = decode_stderr(stderr) or "No output captured"
            return [f"Bank capture failed (exit code {proc.returncode}): {error_msg}"]

        stderr_text = decode_stderr(stderr)
        if stderr_text:
            result.append(f"stderr: {stderr_text}")
        return result

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return [f"Timeout: script did not finish within {timeout}s"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
