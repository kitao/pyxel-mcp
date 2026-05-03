# pyxel-mcp

pyxel-mcp is an MCP server that lets AI agents run, verify, and iterate on
Pyxel retro-game programs without a display. It exposes 9 observation tools.

Each tool call runs in a fresh subprocess so per-call state cannot leak. The
tools return raw observations (palette, pixels, snapshots, audio metadata,
diff stats); the agent decides whether the observation is acceptable for the
current task.

## Tools at a glance

**`run(script, frames, inputs=[], snapshots=[], random_seed=None, timeout=10, stall_window_frames=None)`**
Drive the script through `frames` game frames. Collects snapshots
(`screen_image`, `screen_grid`, `state`, `layout`, `video`) and console
assertions. The full result dict includes:

- `ok` — boolean shortcut: `exit_status == "ok"` and no fatal errors
- `exit_status` — `"ok"`, `"crashed"`, `"timeout"`, or `"stalled"`
- `snapshots` — captured snapshots, one entry per requested frame/range
- `assertions` — `ASSERT PASS` / `ASSERT FAIL` lines parsed from stdout
- `frame_count` — actual frame count reached (may be `< frames` on early break)
- `elapsed_seconds` — wall time of the run
- `log` — concatenated stdout + stderr from the script
- `seeded` — whether `random_seed` was supplied (consumed by gates that require determinism)
- `errors` — structured records when `exit_status != "ok"`

**Always read `log` alongside snapshots.** A clean `exit_status: "ok"` paired
with warnings, `Failed to open file`, `Traceback`, or unexpected `print`
output in `log` is a yellow flag — runtime warnings do not change
`exit_status` but often signal latent bugs (missing assets, wrong colkey,
slot underrun, etc.). Scan `log` for `WARN`, `ERROR`, `Failed`, and
`Traceback` even on success.

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

**`read_palette(script)`**
Read palette state at the script's pre-loop checkpoint. Returns colors,
`extended_palette` flag, `hierarchy_score` (3-layer: background / environment
/ interactive — derived from `used_indices`, the union of indices touched
across image banks), `used_indices`, and WCAG contrast warnings.

**`read_image(script, image, x=0, y=0, w=None, h=None, render_path=None)`**
Read pixels from an image-bank region (banks 0–2). Returns `color_count`,
`fill_ratio`, `symmetry`, `edge_density`. Pixel grid is `null` when the
region exceeds 4096 px. Pass `render_path` to save a PNG for direct visual
inspection by the agent (`Read` tool).

**`read_animation(script, image, x, y, w, h, region_count, direction)`**
Read N adjacent regions in horizontal or vertical direction. Returns
`palette_consistency` (Jaccard), `silhouette_stability` (avg pairwise
Jaccard), and per-pair `region_diffs`. Useful for verifying that sprite
frames share a consistent palette and silhouette.

**`read_tilemap(script, tilemap, render_path=None)`**
Read tilemap N data. Returns tile usage counter, `region` (bounding box of
non-empty tiles, dict-shape `{x, y, w, h}`), and `trap_warning` (true when
the tilemap uses source tile `(0, 0)` and that tile is non-empty — the
blank-tile trap).

**`read_audio(script, target, output_path)`**
Render a sound or music slot to WAV. `target` is `{"sound": int}` or
`{"music": int}` (exactly one). Returns `duration_seconds`, `peak_amplitude`,
`notes` list, and `warnings`. **`target={"sound": N}` populates the `notes`
list; `target={"music": N}` returns `notes: []` (Pyxel's music object is a
list-of-channel-sound-IDs, not a note sequence).** Render BGM by walking the
music slot's constituent sound IDs and rendering each as a sound.

**`diff_frames(frame_a, frame_b)`**
Pixel-wise diff between two PNG paths. Returns `identical`, `size_match`,
`changed_pixels`, `total_pixels`, `ratio`, and `region` (bounding box of
differences). No script required.

## Quality verification is the agent's job

This MCP server intentionally has no `judge_*` tools and no numerical
default thresholds. Encoding "good game" as universal numerical predicates
proved structurally brittle — every game type surfaced a default that
fought a legitimate idiom (3-material palette ↔ contrast-warning budget;
flame-pulse animation ↔ palette-consistency floor; 4×4 sprite ↔
distinct-color minimum). The recurring tuning was unbounded.

Quality verification is the agent's responsibility:

1. Capture observations via the 9 tools above (state snapshots, rendered
   PNGs, audio peaks, palette index sets, frame diffs).
2. Assert predicates **directly in Python** against the returned values.
   No tool wraps the predicate; use any Python you need (`abs`, `len`,
   list comprehensions, helpers).
3. **Read** rendered PNGs with the host's `Read` tool. The Pyxel canvas
   is small (≤ 256×256), so the multimodal LLM reads every pixel —
   verbalize sprite identity, scene state, HUD content, animation state,
   background and hazard placement against PLAN.md / ASSETS.md anchors.
4. When code-asserted state and visual observation disagree, **trust the
   visual observation**.

The Layer 3 workflow skill (`pyxel://workflow`) drives this end-to-end
across a 7-stage pipeline; see its `quality-gate.md` for the 11 stop
conditions an agent runs before declaring "done".

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
    {"kind": "state",        "frame": 60, "attrs": ["player.x", "score"]},
    {"kind": "screen_image", "frame": 60, "output": "/tmp/frame60.png"}
  ]
}
```

Then in the agent:

```python
result = run(script="main.py", frames=120, snapshots=[...])
snaps = {(s["kind"], s["frame"]): s for s in result["snapshots"]}
v = lambda f, a: snaps[("state", f)]["values"][a]

assert v(60, "score") == 0
assert v(60, "player.x") > 10
# Then Read /tmp/frame60.png and verbalize.
```

### Pre-flight static check with `validate`

Always run `validate` before the first `run`. It catches syntax errors and the
10 common anti-patterns without starting a Pyxel process. Cheaper than
discovering a `crashed` exit_status mid-implementation.

### Sprite identity verification

1. `read_palette(script)` — capture the palette + hierarchy score (derived
   from indices actually drawn into image banks).
2. `read_image(script, image=N, x=..., y=..., w=..., h=..., render_path="/tmp/sprite.png")`
   — capture pixel stats AND save a PNG.
3. `Read /tmp/sprite.png` — agent verbalizes against the ASSETS.md
   `represents:` string for that row. Reject blob / placeholder /
   wrong-subject sprites.

For paired animations, `read_animation(..., region_count=2)` plus `Read` of
each rendered frame.

### Audio asset spot-check

Run `read_audio(target={"sound": N}, output_path="...")` immediately after
populating a sound slot. Assert `peak_amplitude >= 0.02` and inspect the
`notes` list (must be non-empty for sound targets) before relying on the
slot during gameplay.

### Visual regression and dead-time detection

Capture a golden screenshot with `run` + `screen_image`. In subsequent runs,
use `diff_frames` against the golden file and assert `identical: true` or
`ratio < 0.01`.

Use `diff_frames` also for **dead-time detection**: capture frames spanning
the full bundle window and compute the maximum pairwise diff. A bundle whose
all-pairs diff is < 5% indicates a stall (frozen entity, frozen camera,
broken state) even when the final scene reaches WIN. Alphabetical
first-vs-mid pairs are unreliable — pick the max across all pairs.

### Multimodal frame review

The result PNGs from `screen_image` snapshots are agent-readable artifacts.
Open them with the host's `Read` tool (Claude Code, Codex, etc.) and verbalize
observations directly — at typical Pyxel resolutions (≤ 256×256) the
multimodal LLM can read every pixel. This complements `read_image`
aggregate fields (`color_count`, `fill_ratio`): aggregates certify mechanics
("5 colors used, 40% fill"), the Read certifies recognizability ("Mario in
red cap, mid-stride"). Both are needed for an honest pass.

### Multi-frame snapshot syntax

Pass `frames` as a list of ints or as a range string (`"0:60:10"` for every
10th frame from 0 to 60) inside a snapshot entry. See
`pyxel://run-snapshots-schema` for the full grammar.

### Determinism

Pass `random_seed: int` to `run`. The harness seeds both Python's `random`
module and Pyxel's `rseed` together so the same frame sequence is reproducible
across calls. Quality-gate playthroughs must be seeded — an unseeded run
that happens to pass this attempt may not pass the next.

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
will display that tile. `read_tilemap` flags this case as
`trap_warning: true`. `validate` detects the pattern as `tilemap_zero_zero`.

### Palette mutation

`pyxel.colors[i] = 0xff8800` (or `.append(...)`) mutates the global palette
and may disable `read_palette`'s hierarchy analysis. Stick to the default
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
- **`pyxel://workflow`** — Layer 3 workflow skill (entry point: SKILL.md).
  Sub-paths follow the on-disk layout: `pyxel://workflow/<stage>` for the
  7 pipeline stages, `pyxel://workflow/knowledge/<topic>` for topical
  knowledge files. Read this when the task is "build a complete Pyxel
  game" rather than "verify a single sprite".
- **`pyxel://api-reference`** — Full Pyxel API reference (palette, drawing,
  input, sound, tilemap). Cross-link for the quirks listed above.
