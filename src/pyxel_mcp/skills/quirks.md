# Pyxel Quirks — gotchas not obvious from API docs

**Read this before writing gameplay code.** Each item below has bitten
real implementations and shows up as ambiguous bugs.

## Coordinates and drawing

- Origin (0, 0) is **top-left**. Y increases downward.
- `pyxel.cls(col)` must be the first call inside `draw()`. Missing
  `cls` → previous frame bleeds through.
- Draw order is paint order: background first, sprites next, UI on
  top.
- `blt()` without `colkey=` makes the sprite's transparent color
  opaque. Always `blt(x, y, img, u, v, w, h, colkey=0)` (or whatever
  your transparent index is).
- Negative `w` in `blt()` flips horizontally; negative `h` flips
  vertically. Use this for direction-facing instead of duplicating
  sprites.

## Trig is in degrees

`pyxel.sin(deg)` and `pyxel.cos(deg)` take degrees, not radians.
Importing Python's `math` module and using `math.sin(rad)` works but
mixes conventions; pick one and stick with it.

## Input

- `pyxel.btnp(KEY)` fires once on press (use for jumps, menu
  selections).
- `pyxel.btn(KEY)` fires every frame the key is held (use for
  walking, climbing).
- Mouse coordinates `pyxel.mouse_x/y` are window-space; if your
  scale > 1, they're already in game-pixel coordinates.
- Headless mode (used by MCP harnesses) uses `pyxel.set_btn` and
  `pyxel.set_btnv` for input simulation. Production code reads via
  `btn()`/`btnp()` as normal.

## Image bank gotchas

- `pyxel.images[N].set(x, y, [hex_strings])` writes pixels. Each
  hex digit = 1 pixel = 1 palette index.
- The width is determined by string length, height by list length.
  Mismatched line lengths cause partial sprites.
- Setting must happen *before* `pyxel.run()`. Inside `update/draw`
  is too late for the first frames and wasteful.
- Image bank is 256x256. Plan a layout in ASSETS.md so sprites
  don't overlap.

## Tilemap (0,0) trap

Every tilemap cell defaults to tile (0, 0). Keep position (0, 0) of
the source image bank empty (transparent). If you place a real tile
at (0, 0), every uninitialized cell renders that tile, flooding the
tilemap with it.

To set tilemap source explicitly: `pyxel.tilemaps[N].imgsrc = M`
where M is the image bank holding tile graphics.

## Audio quirks

- 4 channels: ch0–ch3.
- Convention: BGM on ch0–ch2, SE on ch3. Calling `play(0, ...)` on
  the BGM melody channel interrupts BGM.
- SE volume must be 5–7 to cut through BGM. Volume 1–4 SE is usually
  inaudible.
- Square (`s`) and pulse (`p`) tones are good for SE. Noise (`n`)
  is too quiet over BGM for melodic SE; reserve it for percussion
  or hits.
- `pyxel.gen_bgm(preset, transp, instr, seed, play=False)` — first 4
  args **required** as of Pyxel 2.9.0. Returns 4 MML strings (one
  per channel). Drop ch3 string if you need ch3 for SE.
- MML volumes are V0–V100; `set()` API volumes are 0–7. Different
  scales — `V7` in MML is very quiet, not the same as `7` in `set`.
- Headless mode (MCP) uses `SDL_AUDIODRIVER=dummy` — sounds *render*
  in `render_audio` but you don't hear them when running headless.

## Animation timing

Standard pattern for 2-frame walk cycle:

```python
frame = pyxel.frame_count // 4 % 2  # change every 4 game frames
u = frame * 16  # walk_1 at u=0, walk_2 at u=16
```

Avoid `frame_count % 2` directly — alternates every frame, way too
fast.

## Performance

- Headless mode forces `fps=1_000_000` in the MCP harness, so frame
  budget isn't enforced. But your game's normal `fps=30` or `fps=60`
  applies when the user runs it.
- Per-frame allocations in `update`/`draw` cause GC stutters.
  Reuse lists; iterate with `for e in list(enemies):` to avoid
  modifying-while-iterating bugs.
- `inspect_state` reads the App instance's attributes; deep nesting
  (e.g., `app.world.player.physics.velocity.y`) doesn't auto-expand.
  Flatten state to top-level App attributes for testability.

## Common Pyxel API confusion

- `pyxel.run(update, draw)` blocks until exit. There's no
  separate "start" — calling `run()` IS starting.
- `pyxel.flip()` is for non-interactive scripts (animated demos).
  Games use `pyxel.run()`.
- `pyxel.quit()` requests exit; the loop ends after current frame.
  In Pyxel 2.8+ it does **not** force-exit, so a `while True:` loop
  inside update will hang.
- `pyxel.screenshot(filename)` and `pyxel.screencast(filename)` save
  to disk. Both append the appropriate extension automatically;
  pass the basename without `.png` / `.gif`.
- `pyxel.frame_count` is monotonic from start; reset it manually if
  scenes need their own clocks (e.g., `self.scene_frame = 0` on
  scene change).

## Color hierarchy fail-fast

If `inspect_palette` reports `Hierarchy score: <2`, your color
choices likely look uniform — typically too many similar mid-tones
without distinct interactive accents. Rebalance per the 3-layer
table in `pyxel://skills/asset-planner`.

## When in doubt

Read `pyxel://api-reference` for authoritative API behavior.
Read `pyxel://examples/<name>` for working patterns. Both are
faster than guessing.
