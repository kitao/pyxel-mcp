# Knowledge: Background and Layout

Used by Stage 1 (visual-target — screen size derivation), Stage 3 (scaffold — text layout), and Stage 7 (quality-gate threshold reference for layout balance).

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

## Screen and Text Layout

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
- **Verify with a `layout` snapshot from `run`**: margins should be symmetric (ratio < 2x), balance should be roughly above 70% on both axes for static screens, and no quadrant should be near-empty unless the game intentionally uses empty space.

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

## Quality gate connection

The quality gate (#11) requires a `layout` snapshot inside `run` to report `h_balance ≥ 0.70` on the TITLE scene. For TITLE scenes that lack text (logo-only), the gate falls back to a `screen_grid` snapshot on a representative frame and asserts no quadrant of the returned `grid` is empty.

## Reference

- For title-screen-specific composition, see `knowledge/patterns.md` "Title Screen Design".
