# Knowledge: Pixel Art

Used by Stage 4 (asset-planner), Stage 5 (asset-gen), and Stage 7 (quality-gate threshold reference).

## 16-color default palette

0:black 1:navy 2:purple 3:green 4:brown 5:dark_blue 6:light_blue 7:white
8:red 9:orange 10(a):yellow 11(b):lime 12(c):cyan 13(d):gray 14(e):pink 15(f):peach

## 3-Layer Color Hierarchy

Establish clear visual layers in every game:

1. **Background** (dark): 0 (black), 1 (navy), 5 (dark_blue) — recedes visually
2. **Environment** (mid-tones): 3 (green), 4 (brown), 13 (gray) — terrain, walls
3. **Interactive** (bright): 8 (red), 10 (yellow), 11 (lime) — player, items, danger

Use 10-14 of the 16 colors. Restrict each sprite to 3-4 colors for readability. The player sprite should use a unique color not shared with enemies.

The quality gate (#8) requires the palette tool to report `Hierarchy score: 2/2`. The hierarchy layers are:
1. Background (dark): 0, 1, 5
2. Environment (mid): 3, 4, 13
3. Interactive (bright): 8, 10, 11

Score 2/2 means all three layers are represented. Score 1/2 = two layers; score 0/2 = one layer (uniform tone). The gate also enforces low-contrast warnings ≤ 1 (check #9).

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

Player/item sprites should be **horizontally symmetric**. Enemy sprites can be asymmetric for organic/alien look. The sprite-inspection tool reports `color_count` (number of distinct colors) and `fill_ratio` (non-zero pixels / total) — verify them after each sprite. The quality gate (#4) asserts `len(color_count.keys()) ≥ ASSETS.md minimum` and `0.15 ≤ fill_ratio ≤ 0.95`.

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

Place animation frames adjacent horizontally in the image bank. Inspect each sprite at its bank coordinates after creation — verify `color_count` ≥ minimum and `fill_ratio` is within 0.15-0.95 (gate check #4). For paired frames, the animation-inspection tool reports per-frame pixel diff; the gate requires 5-50%.

Design **original** sprites for each game — never reuse the same design across projects.

### Sprite Sheet Organization

Pack sprites in image bank 0 at 8px intervals:
- (0,0): Player | (8,0): Enemy1 | (16,0): Item1 | (24,0): Item2
- (0,8): Player walk frame 2 | (8,8): Enemy2 | etc.
- Animation frames: adjacent horizontally `u = pyxel.frame_count // speed % frame_count * 8`

## Reference

- Pyxel default palette URI: `pyxel://palette/default` (MCP resource).
- For animated sprite frame counts, see `knowledge/patterns.md` "Animation Timing".
