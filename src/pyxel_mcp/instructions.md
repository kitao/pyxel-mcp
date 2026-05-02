# pyxel-mcp

pyxel-mcp is an MCP server that lets AI agents run, verify, and iterate on
Pyxel retro-game programs without a display. It exposes nine tools that span
the full development loop: static validation, dynamic execution with snapshot
collection, asset inspection (palette, image, animation, tilemap, audio), and
visual regression. Each tool call runs in a fresh subprocess so state cannot
leak between calls.

## Tools at a glance

**`run(script, frames, inputs=[], snapshots=[], random_seed=None, timeout=10)`**
Drive the script through `frames` game frames. Collects snapshots
(`screen_image`, `screen_grid`, `state`, `layout`, `video`) and console
assertions. Returns `exit_status`, `snapshots`, `assertions`, and `errors`.
See `pyxel://run-snapshots-schema` for the full snapshot grammar.

**`validate(script)`**
Static analysis: syntax check plus 10 anti-pattern detectors
(`cls_missing`, `update_in_draw`, `btn_one_shot`, `missing_colkey`,
`palette_animation`, `tilemap_zero_zero`, `iter_modify`, `assets_in_update`,
`degree_radian_mix`). Returns `{ok: bool, issues: [...]}`. No Pyxel process
is started; this is cheap and should run before every first `run`.

**`pyxel_info()`**
Discovery: report Pyxel version, Python version, stub paths, example script
paths, and resource URIs. No script required.

**`inspect_palette(script)`**
Read palette state at the script's pre-loop checkpoint. Returns colors,
`extended_palette` flag, `hierarchy_score` (3-layer: background / environment
/ interactive), and WCAG contrast warnings.

**`inspect_image(script, image, x=0, y=0, w=None, h=None, render_path=None)`**
Read pixels from an image-bank region (banks 0–2). Returns `color_count`,
`fill_ratio`, `symmetry`, `edge_density`. Pixel grid is `null` when the
region exceeds 4096 px. Pass `render_path` to save a PNG.

**`inspect_animation(script, image, x, y, w, h, region_count, direction)`**
Read N adjacent regions in horizontal or vertical direction. Returns
`palette_consistency` (Jaccard), `silhouette_stability` (avg pairwise
Jaccard), and per-pair `region_diffs`. Useful for verifying that sprite
frames share a consistent palette and silhouette.

**`inspect_tilemap(script, tilemap, render_path=None)`**
Read tilemap N data. Returns tile usage counter, `region` (bounding box of
non-empty tiles, dict-shape `{x, y, w, h}`), and `trap_warning` (true when
the tilemap uses source tile `(0, 0)` and that tile is non-empty — the
blank-tile trap).

**`render_audio(script, target, output_path)`**
Render a sound or music slot to WAV. `target` is `{"sound": int}` or
`{"music": int}` (exactly one). Returns `duration_seconds`, `peak_amplitude`,
`notes` list, and `warnings`.

**`compare_frames(frame_a, frame_b)`**
Pixel-wise diff between two PNG paths. Returns `identical`, `size_match`,
`changed_pixels`, `total_pixels`, `ratio`, and `region` (bounding box of
differences). No script required.

## Workflow patterns

### Milestone verification with `run`

Combine `state` and `screen_image` snapshots in a single `run` call. The
`state` snapshot reads the App's Python attributes (e.g. `player.x`, `score`)
at frame F; `screen_image` captures the rendered pixels at the same frame.
Together they confirm that the game's internal state matches what the screen
shows.

```json
{
  "snapshots": [
    {"kind": "state",        "frame": 60, "paths": ["player.x", "score"]},
    {"kind": "screen_image", "frame": 60, "output_path": "/tmp/frame60.png"}
  ]
}
```

### Pre-flight static check with `validate`

Always run `validate` before the first `run`. It catches syntax errors and the
10 common anti-patterns without starting a Pyxel process. Cheaper than
discovering a `crashed` exit_status mid-implementation.

### Sprite quality chain

1. `inspect_palette` — confirm color hierarchy score and WCAG contrast.
2. `inspect_image` — read sprite pixels; check fill ratio and symmetry.
3. `inspect_animation` — verify per-frame palette consistency and silhouette
   stability across all animation frames.

### Audio asset spot-check

Run `render_audio` immediately after populating a sound slot. Assert
`peak_amplitude > 0` and inspect the `notes` list before relying on the slot
during gameplay.

### Visual regression

Capture a golden screenshot with `run` + `screen_image`. In subsequent runs,
use `compare_frames` against the golden file and assert `identical: true` or
`ratio < 0.01`.

### Multi-frame snapshot syntax

Pass `frames` as a list of ints or as a range string (`"0:60:10"` for every
10th frame from 0 to 60) inside a snapshot entry. See
`pyxel://run-snapshots-schema` for the full grammar.

### Determinism

Pass `random_seed: int` to `run`. The harness seeds both Python's `random`
module and Pyxel's `rseed` together so the same frame sequence is reproducible
across calls.

## Quirks

### `btn` vs `btnp`

`pyxel.btn(K)` returns `True` while a key is held.
`pyxel.btnp(K)` returns `True` only on the first frame of a press.

Use `btnp` for one-shot action triggers (jump, shoot, menu confirm) and `btn`
for continuous movement. The harness's `inputs` simulation models this
correctly via post-flip set_btn calls. `validate` flags `btnp`-in-loop misuse
as `btn_one_shot`.

### `cls()` placement

Call `pyxel.cls(bg_color)` at the **start** of `draw()` to clear the screen
before drawing anything. Forgetting it causes each frame's content to overlay
the previous frame's content. `validate` flags the absence of `cls()` as
`cls_missing`.

### Tilemap `(0, 0)` trap

In `pyxel.tilemaps[N].pset(tx, ty, (u, v))`, the tile at source coordinates
`(0, 0)` is conventionally "empty". If the source image bank's top-left tile
is actually visible (non-transparent pixels), every "empty" cell in the map
will display that tile. `inspect_tilemap` flags this case as
`trap_warning: true`. `validate` detects the pattern as `tilemap_zero_zero`.

### Palette mutation

`pyxel.colors[i] = 0xff8800` (or `.append(...)`) mutates the global palette
and may disable `inspect_palette`'s hierarchy analysis. Stick to the default
16-color palette unless you are intentionally extending it. `validate` flags
runtime palette writes as `palette_animation`.

### One `init()` per process

`pyxel.init()` may only be called once per OS process. The harness wraps this
transparently in `headless_pyxel()`; user scripts should call it once in their
App `__init__`. Calling it again (e.g. in a second test) will crash the
subprocess — each tool call already runs in a fresh subprocess, so this is
handled automatically.

## Determinism and isolation

- Each tool call runs in a fresh subprocess. Per-call state cannot leak across
  calls.
- The script's working directory inside the subprocess is its parent directory,
  so relative asset paths (`load("assets/game.pyxres")`) resolve naturally.
- Pass `random_seed: int` to `run` for reproducible output.
- Pyxel's GUI and audio output are suppressed in headless mode via
  `SDL_VIDEODRIVER=dummy`.

## Resources

- **`pyxel://run-snapshots-schema`** — Full schema for the five snapshot kinds
  (`screen_image`, `screen_grid`, `state`, `layout`, `video`) and the
  multi-frame range syntax. Read this before constructing complex snapshot
  lists.
- **`pyxel://anti-patterns`** — Catalog of detector categories surfaced by
  `validate`, with severity, rationale, and canonical fix per category. Read
  when an issue's `category` string is unfamiliar.
- **`pyxel-skill` repo** (https://github.com/kitao/pyxel-skill) — Production
  workflow that uses pyxel-mcp tools end-to-end: visual target → decomposition
  → scaffold → asset generation → task execution → quality gate.
- **`pyxel://api-reference`** — Full Pyxel API reference (palette, drawing,
  input, sound, tilemap). Cross-link for the quirks listed above.
