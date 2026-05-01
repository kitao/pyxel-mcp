# Asset Planner — ASSETS.md authoring

**Phase 4.** Inventory every sprite the game needs, with its size,
color budget, and identity description. Catches "I'll add it later"
before it becomes a missing asset bug.

## Output

`ASSETS.md` at the project root. Manifest of every sprite with its
image bank coordinates, palette plan, and identity contract.

## Image bank layout

Pyxel default has 3 image banks, each 256x256, storing
8-bit (palette index) pixels. Layout sprites in bank 0 in a grid
pattern:

```
ASSETS.md format:

Image bank 0 layout (256x256):
  (0, 0)–(95, 15):    player walk cycle (6 × 16x16)
  (96, 0)–(127, 15):  hammer states (2 × 16x16)
  (128, 0)–(159, 31): boss (32x32)
  (160, 0)–(175, 23): princess (16x24)
  (0, 32)–(31, 47):   barrel rolling (2 × 16x16)
  (0, 48)–(7, 55):    score digit "0" through (72, 48)–(79, 55) digit "9"
  ...
```

Pack tightly. Reserve a clearly-marked "free" region for additions.

## Identity contract per asset

For every named asset, write:

```markdown
### player_walk_1
- bank/region: 0 / (0, 0, 16, 16)
- represents: "Mario in red cap and blue overalls, mid-stride, facing right. Visible: cap, eye dot, mustache silhouette, two arms (one extended), two legs (one forward)."
- palette: [0 outline, 8 cap, 12 overalls, 14 skin, 15 highlight, 7 buttons]
- min distinct color regions: 5 (cap / face / overalls / arms-or-legs / outline)
- silhouette: bounded; non-transparent pixels < 70% of 16x16
- frame relations: paired with player_walk_2 (must differ in 5–50% of pixels)
```

The `represents` field is the asset-gen identity contract. After
implementation, a stranger shown the rendered sprite without the
label must be able to identify it as "Mario walking". The
quality-gate verify_assets check tests against this constraint via
heuristics (color-region count, silhouette boundedness, frame
diff against paired frames).

## Palette discipline per asset

Each sprite uses 3–6 colors from the global palette. Patterns that
work:

| Material | Layer | Palette example |
|----------|-------|----------------|
| Character (warm) | shadow / base / highlight | 4 / 14 / 15 |
| Character (cool) | shadow / base / highlight | 5 / 12 / 6 |
| Outline | always | 0 (or 1 on bright bg) |
| Metal | shadow / base / highlight | 5 / 13 / 7 |
| Wood / barrel | shadow / base / highlight | 4 / 9 / 10 |
| Foliage | shadow / base / highlight | 3 / 11 / 7 |

Single-color sprites ("a brown rectangle") FAIL the identity contract.

## Required asset categories

For an arcade-style platformer like Donkey Kong:

```markdown
## Player
- player_idle (16x16)
- player_walk_1 (16x16)
- player_walk_2 (16x16)
- player_jump (16x16)
- player_climb_1 (16x16)
- player_climb_2 (16x16)
- player_dead (16x16) — optional spinning frame

## Antagonist (boss)
- boss_idle (32x32)
- boss_throw_1 (32x32) — optional, animation when spawning hazard
- boss_throw_2 (32x32)

## Damsel/goal
- princess (16x24)

## Hazard (barrel)
- barrel_1 (16x16)
- barrel_2 (16x16)  — second roll frame, must differ from _1

## Power-up
- hammer_carry (16x16)  — when held above player's head
- hammer_swing (16x16)  — alternate frame

## HUD
- life_icon (8x8) — mini-Mario for lives display
- digit_0 .. digit_9 (8x8) — score digits if drawing custom font

## Environment (optional, can be `pyxel.rect()` if hand-drawn)
- girder_tile (8x8 tileable)
- ladder_tile (8x8 tileable)
- rivet (4x4)
```

The princess and barrel are minimums; without them the game isn't
the genre. Hammer can be deferred to v2 (mark optional in PLAN.md).

## Generation strategy: hex strings

Pyxel sprites are defined via:

```python
pyxel.images[0].set(x, y, [
    "0888880000000000",
    "8888888800000000",
    ...
])
```

Each character is a hex digit (0–f) representing palette index.
Width must match the line length; height = list length. The 0 here
is treated as palette color 0 unless `colkey=0` is passed in `blt`,
in which case 0 = transparent.

For the asset-gen phase: write strings line-by-line, verifying
incrementally with `inspect_sprite`.

## Anti-patterns in this phase

- "I'll figure out the sprites while coding" — leads to last-minute
  rectangle blobs.
- Listing assets without `represents:`. asset-gen has no acceptance
  criterion.
- Listing assets without palette plan. Result: every sprite is gray.
- Reusing the same sprite for "walking" and "idle" without saying so.
  Animation diff check FAILs.
- Skipping outline color. Sprites blend into background; contrast
  warnings trip in `inspect_palette`.

## When this phase is done

`ASSETS.md` exists with full manifest. Each entry has bank region,
represents, palette, color-region count. Move to `asset-gen` (read
`pyxel://skills/asset-gen`).
