# pyxel-mcp

pyxel-mcp is an MCP server that lets AI agents run, verify, and iterate on
Pyxel retro-game programs without a display. It exposes 17 tools across two
layers:

- **Layer 1 — observe (9 tools).** Run the script, inspect Pyxel state,
  diff frames. Returns raw observations (palette, pixels, snapshots, audio
  metadata). Each call runs in a fresh subprocess so state cannot leak.
- **Layer 2 — judge (8 tools).** Pure functions that score a Layer 1
  observation against a contract dict (typically sourced from PLAN.md /
  ASSETS.md milestones and manifests). Returns
  `{ok, verdict ('pass'|'warn'|'fail'), evidence, fail_route, details}`.
  No subprocess; in-process and side-effect free.

Layer 1 answers "what is happening in Pyxel"; Layer 2 answers "is the
observed state acceptable per the contract." Combine them: call a Layer 1
tool, pass its result as `observation` to the matching Layer 2 tool with the
contract entry the agent extracted from PLAN.md / ASSETS.md.

## Tools at a glance — Layer 1 (observe)

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

## Tools at a glance — Layer 2 (judge)

Each `judge_*` is a pure function: `(observation, contract=None) -> verdict`.
Pass the result of the matching Layer 1 tool as `observation`; pass a dict
extracted from PLAN.md / ASSETS.md (or omit to use the module default) as
`contract`. All return the same shape:

```
{
  "ok": bool,                 // True iff verdict in {pass, warn}
  "verdict": "pass"|"warn"|"fail",
  "evidence": str,            // human-readable one-line reason
  "fail_route": str|None,     // 'asset-planning'|'sprite-quality'|
                              //  'playthrough'|'spec'|'scaffolding'|
                              //  'bundle' — only set when verdict == fail
  "details": dict             // intermediate values for debugging
}
```

`fail_route` tells the agent which workflow stage to revisit when a check
fails — it is the bridge from "what failed" to "what to do next."

**`judge_palette(observation, contract=None)`**
Verdict on `inspect_palette` against `{min_hierarchy_score, max_contrast_warnings}`.
Routes failures to `asset-planning` (low hierarchy) or `sprite-quality` (too
many close-color pairs).

**`judge_sprite(observation, contract=None)`**
Verdict on `inspect_image` against `{min_distinct_colors, silhouette: [lo, hi]}`.
A `represents` string in the contract is carried into `details` for
traceability against ASSETS.md. Failures route to `sprite-quality`.

**`judge_animation(observation, contract=None)`**
Verdict on `inspect_animation` against `{diff_band: [lo, hi], min_palette_consistency}`.
Every adjacent-region diff must fall within the band; palette Jaccard must
meet the threshold. Failures route to `sprite-quality`.

**`judge_milestone(observation, contract=None)`** (Pattern D)
Evaluate PLAN.md frame-keyed predicates against a `run()` result. Snapshots
are indexed by `(kind, frame)`; each `asserts` entry
(`{frame, kind, predicate}`) names the snapshot to evaluate against. The
predicate is a sandboxed Python expression — comparisons, boolean ops,
attribute / subscript access. Dotted state keys (`player.x`) auto-promote to
nested attribute access. Failures route to `playthrough` (predicate False or
snapshot missing) or `spec` (predicate parse / name error).

**`judge_genre(observation, contract=None)`**
Evaluate PLAN.md `## Genre Identity` rules (`{name, verify}`) against a
`run()` result. The `verify` namespace exposes `exit_status`, `frame_count`,
`ok`, `elapsed_seconds`, `log`, `assertions_passed`, `assertions_failed`. An
empty `rules` list is itself a `spec` failure — genre identity must be
explicit.

**`judge_bundle(observation, contract=None)`** (Pattern G)
`observation = {"bundle_dir": "/path"}`. Verifies required GIFs (default:
`win-path.gif`, `lose-path.gif`), `frames/` PNG count ≥ `min_frames`, audio
files per `audio_manifest`, and a dead-time check (`compare_frames` between
the first and middle PNG must show `ratio > min_dead_time_diff`). Failures
route to `bundle`.

**`judge_audio(observation, contract=None)`**
Verdict on `render_audio` against `{min_peak, min_notes}`. Empty slot
(warning + zero peak / notes) routes to `sprite-quality`; under-spec audio
routes to `scaffolding`.

**`judge_layout(observation, contract=None)`**
Verdict on the first `layout` snapshot in a `run()` result against
`{min_h_balance, min_quadrant_density}`. Failures route to `scaffolding`.

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

1. `inspect_palette` → `judge_palette` — confirm color hierarchy score and WCAG contrast.
2. `inspect_image` → `judge_sprite` — read sprite pixels; verify against ASSETS.md
   manifest entry (distinct colors, silhouette band).
3. `inspect_animation` → `judge_animation` — verify per-frame palette consistency
   and silhouette stability across animation frames.

The Layer 2 verdict converts a numeric observation into a routed pass/fail
the agent can act on without re-implementing the threshold logic.

### Milestone evaluation chain (Pattern D)

1. `run(snapshots=[...])` — capture state / layout snapshots at the frames
   PLAN.md milestones reference.
2. `judge_milestone(run_result, milestone_contract)` — evaluate every
   per-frame predicate against the matching snapshot. Failures with
   `fail_route == "playthrough"` mean the run did not reach the milestone;
   `fail_route == "spec"` means the predicate itself is malformed.

### Bundle handoff check (Pattern G)

After the win-path / lose-path GIFs and per-frame PNGs are written:

```
judge_bundle({"bundle_dir": "/path"}, asset_manifest)
```

This is the last gate before declaring the deliverable complete — it
catches missing artifacts and silently-stuck playthroughs in one call.

### Audio asset spot-check

Run `render_audio` immediately after populating a sound slot. Assert
`peak_amplitude > 0` and inspect the `notes` list before relying on the slot
during gameplay.

### Visual regression

Capture a golden screenshot with `run` + `screen_image`. In subsequent runs,
use `compare_frames` against the golden file and assert `identical: true` or
`ratio < 0.01`. Use `compare_frames` also for **dead-time detection**: capture
two `screen_image` frames in the visually-active middle of a playthrough and
assert `identical: false` AND `ratio > 0.05`. Identical mid-bundle frames
indicate a stall (frozen entity, frozen camera, broken state) even when the
final scene reaches WIN.

### Multimodal frame review

The result PNGs from `screen_image` snapshots are agent-readable artifacts.
Open them with the host's `Read` tool (Claude Code, Codex, etc.) and verbalize
observations directly — at typical Pyxel resolutions (≤ 256×256) the
multimodal LLM can read every pixel. This complements `inspect_image`
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
