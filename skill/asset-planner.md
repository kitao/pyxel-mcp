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
  (96,  0)–(127, 15):   pickup or tool states (2 × 16x16)
  (128, 0)–(159, 31):   large enemy / boss if requested (32x32)
  (160, 0)–(175, 23):   goal or NPC if requested (16x24)
  (0,  32)–(31,  47):   hazard animation (2 × 16x16)
  (0,  48)–(7,   55):   score digit "0" through (72, 48)–(79, 55) digit "9"
  ...
```

Pack tightly. Reserve a clearly-marked "free" region for additions. **Avoid placing visible content at (0, 0)** — Pyxel tilemap cells default to tile (0, 0) and will flood the tilemap with that content if it is visible.

## Identity contract per asset

For every named asset, write:

```markdown
### player_walk_1

- **bank/region:** 0 / (0, 0, 16, 16)
- **represents:** "red-jacket explorer, mid-stride, facing right. Visible: head, eye dot, backpack shape, two arms, two separated legs."
- **palette:** [0 outline, 8 jacket, 12 pants, 14 skin, 15 highlight, 7 backpack]
- **min distinct color regions:** 5 (head / jacket / pants / arms-or-legs / outline)
- **silhouette:** non-transparent pixels < 95% of 16x16 box, > 15% of box
- **frame relations:** paired with `player_walk_2`; paired-frame diff must be 5–50% of pixels
```

The `represents:` field is the asset-gen identity contract. After implementation, a stranger shown the rendered sprite without the label must be able to identify the subject and action. Stage 5 verifies each sprite with `read_image` (color count, fill ratio, rendered PNG) and animation pairs with `read_animation` (per-frame diff via `region_count` + `direction` matching the bank layout). The final gate re-checks recognizability in check #11 by reading the proof-bundle frames against ASSETS.md.

## Palette discipline per asset

Each sprite uses 3–6 colors from the global palette. Patterns from `knowledge/pixel-art.md` "3-Color-Per-Material Rule":

| Material        | Shadow | Base    | Highlight |
|-----------------|--------|---------|-----------|
| Skin            | 4 (brown) | 15 (peach) | 7 (white) |
| Green creature  | 3 (green) | 11 (lime)  | 10 (yellow) |
| Blue creature   | 1 (navy)  | 6 (light blue) | 12 (cyan) |
| Red creature    | 2 (purple)| 8 (red)    | 9 (orange) |
| Metal           | 5 (dark blue) | 13 (gray) | 7 (white) |
| Wood            | 4 (brown) | 9 (orange) | 15 (peach) |
| Foliage         | 3 (green) | 11 (lime)  | 7 (white) |

Single-color sprites ("a brown rectangle") FAIL the identity contract.

**Palette budget — runtime, not pre-loop.** `read_palette` only sees colours that appear in **image-bank pixels** at the pre-loop checkpoint. It does not see colours emitted by `pyxel.text`, `pyxel.rect`, `pyxel.line`, or any drawing call inside `update`/`draw`. Many games use 3-4 colours in `_build_assets()` for sprites and another 5-7 only via runtime drawing (HUD, scoreboards, scene overlays). The "10-14 of 16 colours" budget recorded in STRUCTURE.md is the **runtime** total, so verify it against a `screen_grid` snapshot from a representative gameplay frame, not against `read_palette`'s `used_indices` alone.

Practical recipe during final visual review:

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

The agent has to construct the merged `used_indices` set explicitly at gate time: take `read_palette`'s `used_indices` (pre-loop image-bank indices) and union with the runtime `screen_grid` indices (which see HUD / overlay drawing). The agent then judges hierarchy / contrast against this merged set — count distinct dark-layer indices (0,1,5), mid (3,4,13), bright (8,10,11); at least 2 layers should be present, and visual contrast between adjacent indices is judged by reading the rendered PNG, not by a numerical threshold. Without the merge, the assessment reflects sprite-bank colours only and misses the HUD / overlay layer entirely.

## Required asset categories

Choose categories from the current game's PLAN.md. Do not force a single-genre manifest onto shooters, puzzlers, runners, or toys.

```markdown
## Player

- player_idle (16x16)
- player_walk_1 (16x16)
- player_walk_2 (16x16)
- player_action_or_hit (16x16) — jump, shoot, push, bank, or damage state

## Enemy / Hazard

- enemy_idle_or_move_1 (16x16)
- enemy_idle_or_move_2 (16x16)
- projectile_or_hazard_1 (8x8 or 16x16)
- projectile_or_hazard_2 (optional animation frame)

## Goal / Pickup / NPC

- goal_or_exit (16x16 or 16x24)
- pickup_1 (8x8 or 16x16)

## Tool / Power-up (optional)

- tool_idle (16x16)
- tool_active (16x16)

## HUD

- life_icon (8x8)
- digit_0 .. digit_9 (8x8) — only if drawing custom score font

## Environment (optional, can be `pyxel.rect()` if intentionally procedural)

- terrain_tile (8x8 tileable)
- obstacle_tile (8x8 tileable)
- background_detail (8x8 or 16x16)
```

The required set is whatever the design promises. A shooter may need ship/enemy/projectile/explosion frames; a puzzle game may need board tiles, cursor, pieces, and feedback states. Declared sprites must be drawn and verified; intentionally procedural geometry is allowed when ASSETS.md says so.

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
- **Listing assets without `represents:`.** Stage 5 has no acceptance criterion. The agent visual review (quality-gate.md check #11) needs the `represents:` string as the anchor to verbalize against — without it, the verbalization has nothing to compare to and the review devolves into "looks fine".
- **Listing assets without palette plan.** Result: every sprite is gray.
- **Reusing the same sprite for "walking" and "idle" without saying so.** Animation diff check FAILs.
- **Skipping outline color.** Sprites blend into background; contrast warnings trip in `read_palette`.

## When this stage is done

- `ASSETS.md` has full manifest with at least Player / Antagonist / Goal / Hazard / HUD sections populated.
- Each entry has `bank/region`, `represents`, `palette`, `min distinct color regions`, `silhouette`, `frame relations`.
- No two entries claim overlapping bank regions.
- Move to Stage 5 (read `asset-gen.md`).
