# Asset Generation — implement and verify each sprite

**Phase 5.** For every entry in `ASSETS.md`, write the
`pyxel.images[N].set()` call and verify the rendered sprite reads as
its `represents` description.

## Loop per asset

For each asset in ASSETS.md:

1. Write the hex-string sprite data into `_build_assets()` (or a
   helper called from it).
2. Run `validate_script` to catch syntax errors in the hex strings.
3. Run `inspect_sprite` at the asset's bank coordinates to dump pixels.
4. **Look at the pixels**. Does the silhouette match the
   `represents:` description? Are color regions distinguishable?
5. If FAIL: rewrite the hex strings. Don't move on.

Concretely for one asset:

```bash
# After editing main.py to add player_walk_1:
validate_script main.py                            # syntax
inspect_sprite main.py --image_index=0 \
                        --x=0 --y=0 --w=16 --h=16   # pixels
# Look at the output grid. Is it Mario, or a blob?
```

## Sprite identity heuristics (what `inspect_sprite` lets you check)

`inspect_sprite` returns a hex grid plus a symmetry / asymmetry
report. After capturing the grid, check yourself:

- **Color region count**: count distinct non-transparent palette
  indices in the grid. ASSETS.md declares the minimum (e.g., 5 for
  player). Below that → single-blob → FAIL.
- **Bounding box density**: count non-transparent pixels divided by
  total. Above 95% → too dense, no silhouette → FAIL. Below 15% →
  sprite has too few visible pixels → FAIL.
- **Edge contrast**: perimeter non-transparent pixels should differ
  from interior majority color (for "outlined" sprites). Helpers in
  `_common/format.py` flag this as a warning.
- **Frame pair diff**: for paired frames (walk_1/walk_2), count
  pixels that differ between them. Below 5% → frames are nearly
  identical → animation will look static → FAIL. Above 50% → frames
  are unrelated → animation will flicker → FAIL.

## Concrete pattern: player_walk_1 (16x16, 6+ colors)

```python
# Inside _build_assets():
pyxel.images[0].set(0, 0, [
    "0008888880000000",   #     ████
    "0088888888000000",   #    ██████
    "008f44ff44f00000",   #   skin/face with outline & mouth
    "008f4ff4ff4f0000",   #   eye details
    "0008f4444f000000",   #
    "0008cccccccc0000",   #   overalls (12=cyan)
    "008c87887878c000",   #   buttons (8=red dots)
    "008cccccccccc000",   #
    "0088cc8800cc8800",   #   arms swing forward
    "008c08000080cc00",   #
    "0080000000000000",   #
    "00cccc0000cccc00",   #   legs separated (one fwd, one bk)
    "00cccc0000cccc00",   #
    "0044440000444400",   #   shoes (4=brown)
    "0044440000444400",   #
    "0000000000000000",
])
```

This is illustrative — exact pixels depend on art direction. The
point is: 16x16 is enough room for cap, face, eyes, mustache hint,
overalls with two buttons, arm in distinguishable position, two
separated legs, and shoes. A "Mario-shaped blob" with one or two
colors does not satisfy the contract.

## Bank organization tips

Use the constant region pattern declared in ASSETS.md:

```python
def _build_assets(self):
    img = pyxel.images[0]
    # Player walk cycle
    img.set(0,  0, [...])  # walk_1
    img.set(16, 0, [...])  # walk_2
    img.set(32, 0, [...])  # walk_3 (idle if 3-frame; or jump)
    img.set(48, 0, [...])
    img.set(64, 0, [...])
    img.set(80, 0, [...])
    # Hammer
    img.set(96, 0, [...])
    img.set(112, 0, [...])
    # Boss (32x32)
    img.set(128, 0, [...])
    # ...
```

Helpers may compute regions from a layout dict to avoid magic numbers
matching ASSETS.md by hand.

## Verification at the end of the phase

Run `inspect_bank --image_index=0`. Visually scan: every sprite
slot should contain its declared asset, no empty regions where ASSETS
says there should be data, no sprite spilling into a neighbor's
region.

Run `inspect_animation` for each animation pair (walk_1/walk_2,
barrel_1/barrel_2, etc.). Frames should differ but share palette
and silhouette outline.

## Anti-patterns in this phase

- Generating sprites in `update()` instead of `_build_assets()`.
  Either runs every frame (perf disaster) or runs after `pyxel.run()`
  starts and is invisible to `inspect_sprite` for the first few
  frames.
- "Add it later" placeholders: `pyxel.rect(x, y, 8, 8, 8)` in draw()
  instead of `pyxel.blt(x, y, 0, u, v, 8, 8, colkey=0)`. The asset
  manifest declares a sprite; the draw call must `blt` from it.
- Editing all sprites before running `inspect_sprite` once. Catch
  one bad sprite before writing 10 of them.
- Forgetting `colkey=0` in `blt()` calls. Background of sprite
  becomes opaque. `validate_script` warns about missing colkey.

## When this phase is done

Every asset in ASSETS.md is implemented; `inspect_sprite` per asset
shows distinguishable features matching `represents`;
`inspect_animation` for paired frames passes. Move to
`task-execution` (read `pyxel://skills/task-execution`).
