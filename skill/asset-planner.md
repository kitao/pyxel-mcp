# Stage 4: Asset Planner

Inventory every sprite the game needs, with image bank coordinates, palette plan, and identity contract. Catches "I'll add it later" before it becomes a missing-asset bug.

## Inputs

- `STRUCTURE.md` "Vision → Objects" (from Stage 1).
- `STRUCTURE.md` "Modules" (from Stage 3) — class names map to sprite categories.
- `PLAN.md` "Main Build → Modules" (from Stage 2).
- `knowledge/pixel-art.md` — 16-color palette, 3-layer hierarchy, 3-color-per-material rule, sprite size guidelines, sprite design process.

## Output

`ASSETS.md` at project root, **appended to** (do not overwrite the `**Art direction:**` line written by Stage 1). Add the sprite manifest sections below.

## Image bank layout

Pyxel's default has 3 image banks, each 256x256, storing 8-bit (palette index) pixels. Layout sprites in bank 0 in a grid pattern:

```
Image bank 0 layout (256x256):
  (0,   0)–(95,  15):   player walk cycle (6 × 16x16)
  (96,  0)–(127, 15):   hammer states (2 × 16x16)
  (128, 0)–(159, 31):   boss (32x32)
  (160, 0)–(175, 23):   princess (16x24)
  (0,  32)–(31,  47):   barrel rolling (2 × 16x16)
  (0,  48)–(7,   55):   score digit "0" through (72, 48)–(79, 55) digit "9"
  ...
```

Pack tightly. Reserve a clearly-marked "free" region for additions. **Avoid placing visible content at (0, 0)** — Pyxel tilemap cells default to tile (0, 0) and will flood the tilemap with that content if it is visible.

## Identity contract per asset

For every named asset, write:

```markdown
### player_walk_1

- **bank/region:** 0 / (0, 0, 16, 16)
- **represents:** "Mario in red cap and blue overalls, mid-stride, facing right. Visible: cap, eye dot, mustache silhouette, two arms (one extended), two legs (one forward)."
- **palette:** [0 outline, 8 cap, 12 overalls, 14 skin, 15 highlight, 7 buttons]
- **min distinct color regions:** 5 (cap / face / overalls / arms-or-legs / outline)
- **silhouette:** non-transparent pixels < 95% of 16x16 box, > 15% of box
- **frame relations:** paired with `player_walk_2`; paired-frame diff must be 5–50% of pixels
```

The `represents:` field is the asset-gen identity contract. After implementation, a stranger shown the rendered sprite without the label must be able to identify it as "Mario walking". The quality gate (#4) tests against this constraint via `read_image` (color count, fill ratio) and `read_animation` (per-frame diff via `region_count` + `direction` matching the bank layout).

## Palette discipline per asset

Each sprite uses 3–6 colors from the global palette. Patterns from `knowledge/pixel-art.md` "3-Color-Per-Material Rule":

| Material        | Shadow | Base    | Highlight |
|-----------------|--------|---------|-----------|
| Skin            | 4 (brown) | 15 (peach) | 7 (white) |
| Green creature  | 3 (green) | 11 (lime)  | 10 (yellow) |
| Blue creature   | 1 (navy)  | 6 (light blue) | 12 (cyan) |
| Red creature    | 2 (purple)| 8 (red)    | 9 (orange) |
| Metal           | 5 (dark blue) | 13 (gray) | 7 (white) |
| Wood / barrel   | 4 (brown) | 9 (orange) | 15 (peach) |
| Foliage         | 3 (green) | 11 (lime)  | 7 (white) |

Single-color sprites ("a brown rectangle") FAIL the identity contract.

**Palette budget — runtime, not pre-loop.** `read_palette` only sees colours that appear in **image-bank pixels** at the pre-loop checkpoint. It does not see colours emitted by `pyxel.text`, `pyxel.rect`, `pyxel.line`, or any drawing call inside `update`/`draw`. Many games use 3-4 colours in `_build_assets()` for sprites and another 5-7 only via runtime drawing (HUD, scoreboards, scene overlays). The "10-14 of 16 colours" budget recorded in STRUCTURE.md is the **runtime** total, so verify it against a `screen_grid` snapshot from a representative gameplay frame, not against `read_palette`'s `used_indices` alone.

Practical recipe at quality-gate time (#8 "Palette hierarchy"):

```python
# 1. Pre-loop palette state — covers sprite-bank colours.
palette_obs = read_palette(script="main.py")

# 2. A mid-game runtime sample — covers HUD / overlay / runtime drawing.
run_result = run(
    script="main.py",
    frames=120, random_seed=42, inputs=[...],
    snapshots=[{"frame": 60, "kind": "screen_grid", "bbox": [0, 0, W, H]}],
)
runtime_indices = set(i for row in run_result["snapshots"][0]["grid"] for i in row)

# 3. Combine and check the budget.
all_used = set(palette_obs["used_indices"]) | runtime_indices
assert 9 <= len(all_used) <= 14, f"palette budget out of band: {len(all_used)}"
```

`judge_palette` works on whatever `observation` it is handed — it does not fetch a runtime sample on its own. The orchestration at gate time has to construct a merged observation: take the `read_palette` result, replace its `used_indices` with the union of pre-loop and runtime `screen_grid` indices, and only then pass it to `judge_palette`. Without that merge step, the gate's hierarchy verdict reflects sprite-bank colours only and misses the HUD / overlay layer entirely.

## Required asset categories

For an arcade-style platformer like Donkey Kong, minimum manifest:

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

## Goal (princess)

- princess (16x24)

## Hazard (barrel)

- barrel_1 (16x16)
- barrel_2 (16x16) — second roll frame, must differ from barrel_1

## Power-up (optional)

- hammer_carry (16x16)
- hammer_swing (16x16)

## HUD

- life_icon (8x8)
- digit_0 .. digit_9 (8x8) — only if drawing custom score font

## Environment (optional, can be `pyxel.rect()` if hand-drawn)

- girder_tile (8x8 tileable)
- ladder_tile (8x8 tileable)
- rivet (4x4)
```

The princess and barrel are minimums; without them the game isn't the genre. Hammer can be deferred.

## Generation strategy: hex strings

Pyxel sprites are defined via:

```python
pyxel.images[0].set(x, y, [
    "0888880000000000",
    "8888888800000000",
    ...
])
```

Each character is a hex digit (0–f) representing palette index. Width = line length; height = list length. The `0` here is treated as palette color 0 unless `colkey=0` is passed in `blt()`, in which case 0 = transparent.

For Stage 5 (asset-gen), write strings line-by-line and verify incrementally with `read_image`.

## Anti-patterns in this stage

- **"I'll figure out the sprites while coding"** — leads to last-minute rectangle blobs.
- **Listing assets without `represents:`.** Stage 5 has no acceptance criterion; the gate FAILs check #4.
- **Listing assets without palette plan.** Result: every sprite is gray.
- **Reusing the same sprite for "walking" and "idle" without saying so.** Animation diff check FAILs.
- **Skipping outline color.** Sprites blend into background; contrast warnings trip in `read_palette`.

## When this stage is done

- `ASSETS.md` has full manifest with at least Player / Antagonist / Goal / Hazard / HUD sections populated.
- Each entry has `bank/region`, `represents`, `palette`, `min distinct color regions`, `silhouette`, `frame relations`.
- No two entries claim overlapping bank regions.
- Move to Stage 5 (read `asset-gen.md`).
