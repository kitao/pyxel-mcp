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
   - `capture_frames` for multi-frame animation and transition verification.
   - `inspect_animation` for sprite animation consistency (palette, silhouette, frame diffs).
5. Fix and re-verify.

### Error Recovery

- **`run_and_capture` timeout**: Script has an infinite loop or heavy computation. Check `update()`/`draw()` for blocking logic. Reduce `frames` parameter to test earlier.
- **`run_and_capture` black screen**: `cls()` called but nothing drawn, or drawing with the same color as background. Check draw coordinates are within screen bounds.
- **`render_audio` empty output**: Sound slot not populated. Verify the script calls `pyxel.sounds[N].set()` or `.mml()` before the game loop.
- **`inspect_sprite` all zeros**: Image bank not populated. Ensure `pyxel.images[N].set()` or `.load()` runs before the game loop starts.
- **`inspect_layout` no text detected**: Text may be too small, overlapping, or same color as background. Try a different frame number.
- **`inspect_layout` margin warnings**: Content not centered. Adjust screen size to match content, or reposition content to center it. Margins should be symmetric.
- **`validate_script` false positive**: Anti-pattern checks are heuristic. If a warning seems wrong, it's safe to ignore and run the script.
- **`inspect_tilemap` all zeros**: Tilemap not populated. Ensure `tilemaps[N].set()` runs before the game loop. Check `imgsrc` matches the image bank with tile data.

### Reading Tool Output

- **`run_and_capture`**: Returns a screenshot image. Visually verify layout, colors, and sprite positions.
- **`render_audio`**: Returns note sequence with timing/frequency. Check that notes match the intended melody and rhythm feels correct.
- **`inspect_sprite`**: Returns a pixel grid + symmetry report. Asymmetric pixels are listed by row — fix those coordinates in `images[N].set()`.
- **`inspect_layout`**: Returns margins, horizontal/vertical balance, quadrant density, center of mass, and text positions. Check margins for symmetry, balance > 70%, and quadrant distribution. Warnings (⚠) flag specific issues.
- **`capture_frames`**: Returns multiple screenshots. Compare frames to verify animation progresses smoothly without jumps or flicker.
- **`play_and_capture`**: Returns screenshots with simulated input. Verify that input causes expected state changes (player moved, menu changed, bullet spawned).
- **`inspect_state`**: Returns game object attributes at a specific frame. Check that variable values match expectations (score, position, game state). Use comma-separated frames for timeline diff: `frames="10,30,60"`.
- **`validate_script`**: Returns syntax errors and anti-pattern warnings. Run before `run_and_capture` to catch issues without Pyxel execution overhead.
- **`inspect_screen`**: Returns screen as hex color grid. Compact token usage. Good for programmatic comparison.
- **`compare_frames`**: Returns changed pixel count, percentage, and region between two frames. Use to verify only intended areas changed.
- **`inspect_palette`**: Returns color distribution and contrast warnings. Check that foreground colors have sufficient contrast against background.
- **`inspect_tilemap`**: Returns tile grid, usage stats, and bounding box. Check `imgsrc` matches your image bank. Verify (0,0) tiles are empty.
- **`inspect_bank`**: Returns image bank as screenshot (up to 256x256). Verify sprite/tile placement and find available space.
- **`inspect_animation`**: Returns per-frame pixel diffs, palette consistency, and silhouette stability. Check that frames share a consistent outline and palette — large diffs between adjacent frames indicate flickering or misaligned sprites.

### Output Format

Analysis tools (`inspect_sprite`, `inspect_layout`, `inspect_palette`,
`inspect_animation`, `validate_script`) output two sections:
- **=== Analysis ===**: Objective data and measurements
- **=== Suggestions ===**: Actionable improvements (`Fix:` for critical issues, `Tip:` for recommendations)

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

This captures the App instance (the class calling `pyxel.run()`) and dumps its attributes. Useful for:
- Physics bugs: check position/velocity values
- Score/state bugs: verify counter values
- Collision issues: check object positions relative to each other

Note: `inspect_state` does not support input simulation. It captures state at a given frame without any key presses. To test input-dependent logic, temporarily replace input conditions with frame-based triggers in the script, then revert.

### Letting the User Play

When suggesting the user run a script directly, check for a virtual environment (`.venv/bin/python` or similar) and include the full path in the command. Users may not have Pyxel installed globally.

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

Pyxel's default resource slots (3 images, 8 tilemaps, 64 sounds, etc.) are starting points, not hard limits. All global lists (`images`, `tilemaps`, `sounds`, `musics`, `channels`, `tones`, `colors`) support `append()` and slice assignment to grow beyond defaults.

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

Suggest these when users hit default limits or need features like multilingual text, richer audio, larger worlds, or visual effects. See the referenced examples for working code.

### Audio Channel Management

Pyxel defaults to 4 audio channels (0-3), but more can be added via `pyxel.channels.append(Channel())`. `playm()` assigns music tracks to channels starting from ch0. `play(ch, snd)` on the same channel **interrupts** the music on that channel. Plan channel allocation to avoid BGM/SE conflicts:

- **BGM on ch0-2, SE on ch3**: Use 3-channel music so SE never interrupts BGM.
- **Title/menu screens**: Can safely use all 4 channels for BGM (no frequent SE).
- Use `resume=True` for non-critical SE to avoid cutting off other sounds.

### Tilemap Gotchas

**Important**: All tilemap cells default to tile (0, 0). Keep position (0, 0) in the image bank empty (transparent) — if you place a visible tile there, it fills the entire tilemap as background.

If tiles are in a different image bank than sprites, set `imgsrc`:

```python
pyxel.tilemaps[0].imgsrc = 1  # draw tiles from image bank 1
```

### MML Composition Guide

Structure BGM as 3 channels: melody (ch0), bass (ch1), harmony/arpeggio (ch2). Reserve ch3 for SE. Use `render_audio` to verify each channel separately.

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

**Volume scales:** MML uses `V0`-`V100` (e.g., `V80` = 80%). The `set()` API uses a `volumes` string with single-digit values `0`-`7` (e.g., `"7776"`). These are independent scales — `V7` in MML is very quiet, not the same as `7` in `set()`.

**Genre moods by key and tempo:**

| Genre | Key | Tempo | Tones | Tips |
|-------|-----|-------|-------|------|
| Action/Gothic | A- minor, C minor | T100-120 | @1 melody, @0 bass | Use E-/A-/B- for dark feel, 8th note arpeggios |
| Adventure | C major, G major | T120-140 | @1 melody, @0 bass | Ascending phrases for heroic mood |
| Puzzle/Calm | F major | T80-100 | @0 melody, @1 harmony | Dotted notes, gentle tempo |
| Horror | B- minor | T60-80 | @2 melody, @3 accents | Half notes, chromatic movement, sparse |
| Boss battle | E minor | T140-160 | @1 melody, @0 bass | Driving 16th bass, syncopated melody |

### Quick BGM

`gen_bgm` generates procedural music — great for rapid iteration, but all outputs share a similar flavor. Combine with hand-written MML for variety.

```python
# gen_bgm(preset, transp, instr, seed, play=False) — first 4 args required
# Returns 4 MML strings — drop ch3 if you need it for SE

# Example: 3-channel BGM (reserve ch3 for SE)
mml = pyxel.gen_bgm(preset=7, transp=0, instr=1, seed=42)
for i in range(3):
    pyxel.sounds[10 + i].mml(mml[i])
pyxel.musics[0].set([10], [11], [12])

# Quick play (uses all 4 channels — good for title screens)
pyxel.gen_bgm(preset=7, transp=0, instr=3, seed=42, play=True)

# Scene-specific BGM — vary preset/seed per scene for distinct moods
def play_bgm(self, scene):
    BGM = {
        # (preset, transp, instr, seed)
        "title":    (0, 0, 1, 100),  # title/departure, melody+bass+drums
        "game":     (4, 0, 2, 200),  # field/adventure, melody+sub+bass
        "boss":     (7, 0, 1, 300),  # battle/crisis, melody+bass+drums
        "gameover": (2, 0, 0, 400),  # town/peaceful, melody+reverb+bass
    }
    preset, transp, instr, seed = BGM[scene]
    mml = pyxel.gen_bgm(preset, transp, instr, seed)
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

Use 10-14 of the 16 colors. Restrict each sprite to 3-4 colors for readability. The player sprite should use a unique color not shared with enemies.

## Pixel Art Rules

### 3-Color-Per-Material Rule

Every surface in a sprite uses 3 colors: base, shadow, highlight. Shift hue slightly between them (not just brightness) for richer results.

| Material | Shadow | Base | Highlight |
|----------|--------|------|-----------|
| Skin | 4 (brown) | 15 (peach) | 7 (white) |
| Green | 3 (green) | 11 (lime) | 10 (yellow) |
| Blue | 1 (navy) | 6 (light_blue) | 12 (cyan) |
| Red | 2 (purple) | 8 (red) | 9 (orange) |
| Metal | 5 (dark_blue) | 13 (gray) | 7 (white) |
| Wood | 4 (brown) | 9 (orange) | 15 (peach) |

### Outline Strategy

Use **black outlines** (color 0) for maximum readability at small sizes. At 8x8, outlines define the silhouette — draw silhouette first, then fill.

### Sprite Size Guidelines

| Size | Use Case | Colors |
|------|----------|--------|
| 8x8 | Tiles, items, bullets, small enemies | 3-4 colors |
| 16x16 | Player, main enemies, NPCs | 5-6 colors |
| 24x24 | RPG characters, detailed sprites | 5-7 colors |

Player/item sprites should be **horizontally symmetric**. Enemy sprites can be asymmetric for organic/alien look. Use `inspect_sprite` to verify symmetry after creation.

### Anti-Patterns

- **Pillow shading**: Shadow around edges, highlight in center — looks puffy. Shadow goes on bottom/right, highlight on top/left.
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
- Animation frames: adjacent horizontally `u = pyxel.frame_count // speed % frame_count * 8`

## Background Design

Background quality is the single biggest factor in visual polish. Never leave the background as a plain solid color.

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

**Derive screen size from content — never start with a fixed size like 160x120.** Calculate the play area, panels, and margins first, then set `pyxel.init(SCR_W, SCR_H)`.

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
- **Content-first sizing**: Define game area, panels, margins as constants. Derive screen size from their sum. Never pick an arbitrary screen size and try to fit content.
- **Center the play area**: For games without side panels, center both axes: `GAME_X = (SCR_W - GAME_W) // 2; GAME_Y = (SCR_H - GAME_H) // 2`.
- **Symmetric margins**: Left ≈ right, top ≈ bottom. Compute with `(SCR_W - content_w) // 2`.
- **No overlap**: HUD must not intrude into the play area.
- **Verify with `inspect_layout`**: Fix all ⚠ warnings. Margins should be symmetric (ratio < 2x), balance > 70% on both axes, no near-empty quadrants.

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

Copy-paste sound definitions for common game events. All SE on ch3 via `pyxel.play(3, N)`. BGM on ch0-2.

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

Every enemy needs: a **behavior pattern**, **visual distinction** from the player, and at least **2 animation frames**.

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

Tested physics values. At 30fps, 1 frame = 33ms. At 60fps, 1 frame = 16ms. Pyxel defaults to 30fps. Values below are for 30fps unless noted.

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

Recommended sprite image counts for smooth animation (ideal targets; see Sprite Design Process for minimums):

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

For games with multiple character states (idle, walk, attack), use a state-machine animator instead of inline frame math:

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

Usage: call `animator.set("walk")` on state change, `animator.update()` every frame, `animator.draw(x, y)` in draw. Set `animator.flip = True` to face left.

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

Before release, verify: BGM present (MML or gen_bgm), distinct SE for all events, title screen with animation, game over with score, non-solid background, HUD with score/lives, player has walk animation, enemies have 2+ frames.
