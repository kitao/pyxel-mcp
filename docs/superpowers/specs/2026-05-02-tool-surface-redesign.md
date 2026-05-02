# pyxel-mcp 0.9.3 Tool Surface Redesign

- **Date:** 2026-05-02
- **Author:** Takashi Kitao (drafted with Claude Opus 4.7)
- **Status:** Draft for review
- **Target:** `pyxel-mcp` 0.9.3 (working version label; final number revisable based on actual scope)
- **Companion document:** `pyxel-skill` v0.1.0+ stage files (separate repo) require coordinated updates

## 1. Goal

Redesign the `pyxel-mcp` MCP tool surface so that an AI agent can verify Pyxel scripts coherently across the dimensions Pyxel actually exposes — **scripted input, frame execution, state observation, screen capture, audio rendering, static asset inspection** — without the artificial fragmentation that the current 16-tool surface exhibits.

The redesign closes a concrete gap discovered during DK validation in 2026-05-01: state observation (`inspect_state`) and input simulation (`play_and_capture`) are split across two tools, so agents cannot run a scripted input schedule and probe `App` instance state at the same frame in a single call. That gap is symptomatic of a tool surface that grew organically rather than systematically.

The new surface has **9 tools**, designed from first principles, justified on merit (not on continuity with the existing surface).

### Validation criterion

The redesign is successful when:

1. The DK validation prompt ("Make a Donkey Kong style platformer in Pyxel") drives `pyxel-skill` end-to-end through the 7-stage pipeline using the new 9-tool surface, and the resulting game passes all 12 stop conditions of `quality-gate.md`.
2. Each gate check (#1–#12) is implementable with at most one new-tool call per check, using natively returned fields (no caller-side post-processing of structured outputs).
3. The agent never needs to chain two tool calls just to observe state and screen at the same frame.

## 2. Non-goals

- **Backward compatibility with current 16-tool surface.** The MCP server is consumed by AI agents, not humans; agents adapt to new tool descriptions. Old tool names will be removed, not deprecated.
- **External asset generation** (Gemini/Grok image gen, Tripo3D 3D, etc.). Pyxel sprites are hex-string palette-indexed pixel data; AI image generation does not produce well-aligned output for this format. This is a deliberate scope difference from `htdt/godogen`.
- **Conditional / interactive run loop.** `run` is stateless and deterministic: agent specifies an input schedule and snapshot schedule upfront, gets all observations back. Iterative verification is achieved by chaining multiple `run` calls (cheap because Pyxel headless runs at `fps=1_000_000`).
- **Stateful pyxel-mcp server.** Each tool invocation spawns a fresh subprocess. State leaks between calls are prevented by process boundaries, not by reset logic.
- **Animation / live audio capture during a run.** Mid-run dynamic palette / image / tilemap / audio-channel state is out of v0.9.3 scope. Static inspectors operate on post-`_build_assets()` state. Live-during-game observation is a future enhancement (`run` snapshot kinds for these are reserved namespace).
- **MP4 as primary video output.** Pyxel's native screencast emits GIF; the redesign uses GIF as the default `video` snapshot output. MP4 is supported via post-process when ffmpeg is available; absent ffmpeg, falls back to GIF cleanly. (godogen mandates MP4; we accept this engine-shape difference as a Pyxel-native tradeoff.)

## 3. Background

### 3.1 The fragmentation problem

The current 16-tool surface evolved feature-by-feature. The latest PyPI release is 0.9.2; 0.9.3 was previously planned as an `instructions.md`-only trim release (`feat/v0.9.3-trim-instructions` branch in this repo, work-in-progress as of 2026-05-01). **This spec supersedes that previously-planned 0.9.3 scope**: the version label is reused, but the scope is broadened to a full tool-surface redesign. The `0.9.3` label is provisional; the user may bump to `0.10.0` or `1.0.0` at release time depending on judgment of breaking-change magnitude.

The 16 tools today are:

```
pyxel_info, validate_script,
run_and_capture, play_and_capture, capture_frames, record_gameplay,
inspect_state, inspect_screen, inspect_layout,
inspect_palette, inspect_bank, inspect_sprite, inspect_animation, inspect_tilemap,
compare_frames, render_audio
```

Four orthogonal concerns are entangled:

1. **Dynamic vs static.** Some tools run the game loop; others read pre-loop config.
2. **Input simulation.** Some dynamic tools accept scheduled inputs; others run "no input".
3. **Observation kind.** Screen pixels, state attrs, palette, bank pixels, tilemap, audio output, layout analysis, frame-pair diffs.
4. **Output format.** Image (PNG), text grid, structured JSON, GIF, WAV.

The existing 16 tools cover the cross-product imperfectly. For example:
- `run_and_capture` (dynamic, no input, screen, PNG) and `play_and_capture` (dynamic, with input, screen, PNG) differ only in axis 2.
- `inspect_state` (dynamic, no input, state) lacks the input axis entirely; combined with `inspect_screen` (dynamic, no input, grid) and `inspect_layout` (dynamic, no input, layout analysis), there is no way to run scripted inputs and observe state at the same frame.
- `inspect_bank` (static, full bank PNG) and `inspect_sprite` (static, region grid + analysis) are two views of the same underlying operation.

### 3.2 What "good" looks like

A well-designed tool surface for verification under MCP should:

- **Make the four axes explicit and orthogonal.** An agent should be able to combine "with inputs" and "observe state" without surprise.
- **Minimize tool count without conflating distinct concerns.** Output schemas should not be conditional on parameter values (it confuses agents reading the tool list).
- **Co-locate related observations.** State and screen at the same frame should arrive in one call so they are verifiably from the same execution.
- **Be deterministic by default.** Same inputs and seed → same outputs, byte-for-byte.
- **Isolate state.** Tool calls must not influence each other's results.

The 9-tool surface specified below was designed to these principles, then validated against `htdt/godogen`'s capability set (see §4.4).

## 4. Architecture

### 4.1 Tool list (9 tools)

```
Dynamic driver (1):
  run(script, frames, inputs=[], snapshots=[], random_seed=None, timeout=10)

Static inspectors (4):
  inspect_palette(script)
  inspect_image(script, image, x=0, y=0, w=None, h=None, render_path=None)
  inspect_animation(script, image, x, y, w, h, frame_count, direction="horizontal")
  inspect_tilemap(script, tilemap, render_path=None)

Audit / discovery / audio (3):
  validate(script)
  pyxel_info()
  render_audio(script, target, output_path)

Artifact analyzer (1):
  compare_frames(frame_a, frame_b)
```

### 4.2 Why 9 (not fewer, not more)

**Why not consolidate further to a single `run` primitive that swallows static inspection too?**

Static inspectors operate on post-`_build_assets()` state. Forcing them through `run` would mean either:
(a) running the game loop for 0 frames just to read a palette (wasteful and conceptually confused), or
(b) adding a `frames=0` / `static_only` mode to `run` (special-cases the primitive).

Static inspectors are well-bounded operations with distinct output schemas (palette colors vs image pixels vs tilemap grid). They deserve their own tool identity.

**Why not split `run` into separate "drive", "snapshot", "render" tools?**

Because state and screen at the same frame must come from the same execution, they must be captured in the same process invocation. Splitting forces multiple `run` calls and re-execution; while Pyxel headless is fast, it sacrifices the single-source-of-truth guarantee.

**Why merge `inspect_bank` + `inspect_sprite` but keep `inspect_image` + `inspect_animation` separate?**

`inspect_bank` and `inspect_sprite` differed only in the size of the region read. Merging them under `inspect_image(image, x, y, w, h)` removes the artificial distinction. Visualization (full-bank PNG) is a `render_path` parameter; analytics (sprite identity heuristics) come back inline.

`inspect_animation` has cross-frame analysis fields (`palette_consistency`, `silhouette_stability`, `frame_diffs`) that are absent for single-region inspection. Merging would force a conditional output schema (presence of cross-frame fields depends on `frame_count`), making the tool's contract harder for agents to reason about.

**Why keep `screen_image` and `screen_grid` as two snapshot kinds in `run` rather than one with format parameter?**

Same reasoning as `inspect_image` vs `inspect_animation`: distinct output destinations (PNG file path vs inline JSON grid) and distinct downstream uses (visual review vs programmatic comparison). The agent's intent is clearer when expressed as the kind name.

### 4.3 Cross-axis matrix

```
                    │ no input     │ with input         │ static
────────────────────┼──────────────┼────────────────────┼─────────────────
screen as PNG       │ run+snap{    │ run(inputs=...)    │ inspect_image(
                    │   screen_im} │   +snap{screen_im} │   render_path=)
────────────────────┼──────────────┼────────────────────┼─────────────────
screen as grid      │ run+snap{    │ run(inputs=...)    │ inspect_image
                    │   screen_grd}│   +snap{screen_grd}│   (returns pixels)
────────────────────┼──────────────┼────────────────────┼─────────────────
App state attrs     │ run+snap{    │ run(inputs=...)    │ (no static state;
                    │   state}     │   +snap{state}     │  use Read on src)
────────────────────┼──────────────┼────────────────────┼─────────────────
layout analysis     │ run+snap{    │ run(inputs=...)    │ (uses screen ⇒
                    │   layout}    │   +snap{layout}    │  same as static
                    │              │                    │  inspect_image
                    │              │                    │  + analyze)
────────────────────┼──────────────┼────────────────────┼─────────────────
multi-frame video   │ run+snap{    │ run(inputs=...)    │ (n/a — dynamic
                    │   video}     │   +snap{video}     │  by definition)
────────────────────┼──────────────┼────────────────────┼─────────────────
palette             │ (n/a — dynamic palette mutation v0.9.3 OOS)│ inspect_palette
────────────────────┼──────────────┼────────────────────┼─────────────────
image bank pixels   │ (n/a — dynamic bank mutation v0.9.3 OOS)   │ inspect_image
────────────────────┼──────────────┼────────────────────┼─────────────────
sprite anim pairs   │ (n/a — animation analysis is static)       │ inspect_animation
────────────────────┼──────────────┼────────────────────┼─────────────────
tilemap             │ (n/a — dynamic tilemap mutation v0.9.3 OOS)│ inspect_tilemap
────────────────────┼──────────────┼────────────────────┼─────────────────
audio render        │ (live audio capture v0.9.3 OOS)            │ render_audio
                    │                                            │ (per slot)
```

This matrix is the spec at a glance: every axis is either covered by `run` (with or without `inputs`), by a static inspector, or explicitly out-of-scope for v0.9.3.

### 4.4 godogen capability mapping

Verification against `htdt/godogen` (Bevy/Godot harness, the reference for this redesign):

| godogen operation                                           | pyxel-mcp 0.9.3 equivalent                                                                                           |
|-------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| `cargo build` / `cargo check`                              | `validate(script)` (Pyxel needs no build)                                                                             |
| `cargo run` smoke test                                     | `run(frames=30)` (read `exit_status` and `log`)                                                                       |
| `Screenshot::image(...)` single still                      | `run(snapshots=[{frame: f, kind: "screen_image", output: ...}])`                                                      |
| Frame sequence capture                                     | `run(snapshots=[{frame: f, kind: "screen_image", ...} for f in range])`                                               |
| `ffmpeg` frames → mp4                                      | `run(snapshots=[{kind: "video", start_frame, end_frame, output, fps}])` (GIF native; MP4 if ffmpeg present)           |
| Final proof bundle layout                                  | Composition is `pyxel-skill`'s responsibility (capture.md); `run` produces the components                             |
| Headless render target (`RenderTarget::Image`, no winit)   | `run` harness uses `SDL_VIDEODRIVER=dummy` + Pyxel patched for headless                                               |
| `TimeUpdateStrategy::ManualDuration`                       | Pyxel headless `fps=1_000_000` advances frames per loop iteration, wall-clock independent                             |
| `set_btn` / `set_btnv` capture-time control                | `run(inputs=[{frame, buttons, axes, mouse_pos}])` — `set_btn` etc. injected by harness, no script modification needed |
| Runtime log reading                                        | `run() → {..., log}` returns stdout+stderr                                                                             |
| Visual verification (agent reads frames)                   | Agent reads PNG paths from `run` snapshot results                                                                      |
| Asset inspection (color, silhouette, palette)              | `inspect_image` + `inspect_animation` + `inspect_palette`                                                              |
| Tilemap inspection                                         | `inspect_tilemap`                                                                                                       |
| Audio                                                      | `render_audio` (godogen explicitly omits audio; pyxel-mcp supports it)                                                  |
| Frame regression diff                                      | `compare_frames`                                                                                                        |
| API documentation lookup                                   | `pyxel_info()` plus MCP Resources `pyxel://api-reference`, `pyxel://examples/<name>`, `pyxel://palette/default`        |

Coverage is complete. Intentional differences: (a) no asset-generation pipeline (Pyxel sprites are hex-string), (b) no multi-file build pipeline (Pyxel runs Python directly), (c) GIF as default video format (matches Pyxel screencast). These are engine-shape differences, not capability gaps.

## 5. Pyxel-mcp constraints (apply to all tools)

These are invariants every tool implementation must satisfy. They are stated as principles, not as continuity constraints.

### 5.1 Subprocess isolation per tool call

**Constraint:** Each tool invocation MUST run in a fresh subprocess.

**Why:** Pyxel exposes a global module state (`pyxel.images`, `pyxel.colors`, `pyxel.frame_count`, `pyxel.tilemaps`, `pyxel.sounds`, `pyxel.musics`, `pyxel.channels`, `pyxel.tones`). The library does not support multiple `pyxel.init()` calls in the same process. Running a second script in the same process leads to undefined behavior.

**Implementation:** The MCP server (`server.py`) handles each tool call by spawning `python -m pyxel_mcp._harnesses.main <subcommand> <args>` as a subprocess, capturing stdout (JSON) and stderr (logs).

### 5.2 CWD = script's parent directory

**Constraint:** Before importing the user script, the harness subprocess MUST `os.chdir(script.parent)`.

**Why:** Pyxel scripts can use relative imports (`from . import enemies`) and relative asset paths (`pyxel.images[0].load("assets/sprite.png")`). The script's behavior must not depend on where pyxel-mcp was invoked from.

**Implementation:** `_common/script_loader.py` resolves the absolute path of the script, chdir's to its parent, and imports it as a module by name.

### 5.3 Determinism

**Constraint:** `run(script, frames=N, inputs=I, random_seed=S)` MUST produce byte-for-byte identical snapshots across invocations, given the same `(script, N, I, S)`.

**Why:** Verification predicates (especially gate checks #5 and #6 for win/lose paths) require reproducibility. Without it, flaky verification undermines the gate's authority.

**Implementation:**
- The harness calls `pyxel.rseed(random_seed)` after `_build_assets()` returns and before `pyxel.run()` starts, if `random_seed` is given.
- If `random_seed=None`, the harness leaves the script's RNG behavior unchanged (it may or may not be deterministic depending on the script).
- The return value includes a `seeded: bool` field indicating whether `rseed` was injected.
- For `inspect_*` static tools, no run loop occurs, so RNG is not relevant; `seeded` is omitted.

### 5.4 External asset load failure handling

**Constraint:** When a script's `_build_assets()` calls `pyxel.images[N].load("file")`, `pyxel.tilemaps[N].load("file.tmx")`, or `Sound.pcm("file.wav")` and the file is missing/malformed, the harness MUST catch the exception and return a structured error.

**Why:** Asset load failures are a common real-world scenario (path typo, missing file). Agents need a structured signal, not a raw Python traceback.

**Implementation:** Every tool's return shape includes an optional `errors: list[ToolError]` field where:

```python
ToolError = {
    "phase": "asset_load" | "script_import" | "build_assets" | "game_loop" | "snapshot",
    "message": str,
    "path": str | None,    # for asset_load
    "frame": int | None,   # for game_loop, snapshot
    "traceback": str | None,
}
```

Tool calls return successfully (HTTP 200 / MCP success) even when errors occur during execution; the agent inspects `errors` to decide.

### 5.5 Output path conventions

**Constraint:** When a tool writes a file (PNG / GIF / WAV / etc.), the parent directory is created if missing (`mkdir -p`-equivalent), and existing files at the target path are silently overwritten.

**Why:** Agents construct output paths programmatically; requiring them to mkdir first adds noise. Overwriting matches typical scripted-test behavior.

**Implementation:** The harness uses `pathlib.Path.mkdir(parents=True, exist_ok=True)` on the parent before writing.

**Frame numbering:** When tools auto-generate filenames from a `output_pattern: "frames/{frame}.png"` template, the `{frame}` field is zero-padded to **5 digits** (`frames/00030.png`). 5 digits supports up to 99999 frames; Pyxel runs at 30 fps so this covers ~55 minutes of capture, far beyond any realistic test scenario.

### 5.6 Two distinct MCP context surfaces

The MCP protocol exposes pyxel-mcp to the agent via three layers, each with its own concise / detailed split. Spec terminology distinguishes these clearly so implementation does not conflate them:

| Layer                            | Where it lives                                  | What's in it                                                                                          | Length budget         |
|----------------------------------|-------------------------------------------------|-------------------------------------------------------------------------------------------------------|-----------------------|
| **A. Per-tool description**      | FastMCP `@mcp.tool()` decorator docstring       | One-paragraph purpose + signature summary + one canonical example. Returned in MCP `list_tools` query | ~10-30 lines per tool |
| **B. Server `instructions`**     | `src/pyxel_mcp/instructions.md` (loaded by FastMCP at server init, attached as the MCP `instructions` field) | Tool catalog overview + workflow guidance + Pyxel-API quirks. The agent reads this once at session start | ~150-200 lines total  |
| **C. MCP Resources (full schemas)** | `src/pyxel_mcp/_resources/*.md` files served as `pyxel://...` URIs | Full snapshot kind schemas, anti-pattern category enumeration, Pyxel API reference, examples list. The agent fetches on demand when extra detail is needed | Unbounded (per resource) |

**Constraint:** Layer A and Layer B together must give the agent enough information to call each tool correctly for common cases. Layer C is for edge cases and reference. Avoid duplicating content between layers (cross-link instead).

**Why:** Layer A's per-tool description is what the agent sees first when the tool list is queried; bloating it with full snapshot kind schemas would degrade tool selection. Layer B (instructions) is loaded once and is the right place for cross-tool workflow notes ("use `run` with state+screen snapshots together for milestone verification"). Layer C is fetched only when the agent needs full detail.

**Implementation:** Layer A docstrings are short, written in the tool registration code (`server.py`). Layer B is `instructions.md`, loaded via `FastMCP(instructions=Path("instructions.md").read_text())`. Layer C resources are served via FastMCP `@mcp.resource()` decorators reading from `_resources/`.

## 6. The `run` primitive

### 6.1 Signature

```python
run(
    script: str,                          # absolute or cwd-relative path to .py
    frames: int,                          # how many game frames to advance
    inputs: list[InputEvent] = [],        # scheduled input events
    snapshots: list[Snapshot] = [],       # what to capture and when
    random_seed: int | None = None,       # if given, pyxel.rseed(this) post-build
    timeout: int = 10,                    # max wall-clock seconds for the subprocess
) -> RunResult
```

### 6.2 Frame execution model

For each frame `F` in `[0, frames)`:

1. Set `pyxel.frame_count = F` (incremented to the new frame's value before logic runs, matching Pyxel's normal loop).
2. Apply any `InputEvent` with `frame == F`. The harness updates the held button set, axis values, and mouse position from the event.
3. Recompute `btnp` / `btnr` deltas against the previous frame's button state.
4. Run `pyxel.update()` — the script's update logic responds to current inputs.
5. Run `pyxel.draw()` — the script renders this frame.
6. **For single-frame snapshots** (`screen_image`, `screen_grid`, `state`, `layout`) with `frame == F`: capture and produce a `SnapshotResult` immediately.
7. **For `video` snapshots** whose `[start_frame, end_frame)` range contains F: write the post-draw frame to a temp PNG. The video is encoded into the final output file only after the run completes (step 8 below). This is accumulation, not per-frame capture.

**After the loop completes:** Encode any accumulated `video` snapshots from the temp PNG sequence into the requested output format (GIF or MP4). Emit one `SnapshotResult` per `video` input.

**Snapshot ordering within a single frame:** The order of snapshots in the input list is preserved in the output. Within a frame, all single-frame snapshots see the post-update + post-draw state. Two snapshots at the same frame with different kinds capture the same logical frame state.

**`pyxel.frame_count` semantics:** Set at the start of frame F (step 1), so during `update()` and `draw()` the script sees `pyxel.frame_count == F`. Snapshots captured at frame F therefore record `pyxel.frame_count == F`. This matches Pyxel's normal interactive-mode behavior.

### 6.3 InputEvent

```python
{
    "frame": int,                                    # at which frame to apply
    "buttons": list[str] | None,                     # held button set (state replacement)
    "axes": dict[str, int] | None,                   # held analog axis values
    "mouse_pos": [int, int] | None,                  # mouse position (game pixels)
}
```

**State replacement, not delta.** `buttons` represents the full set of buttons held from this frame onward until the next event.

**Field-omitted vs explicit-empty (CRITICAL distinction):**

| Value supplied                | Meaning                                                |
|-------------------------------|--------------------------------------------------------|
| `buttons` field omitted, or `null` | **No change** — preserve the previous frame's held button set. |
| `buttons: []` (empty list)    | **Release all** — no buttons are held from this frame onward. |
| `buttons: ["KEY_SPACE"]`      | Replace held set with exactly `{KEY_SPACE}`. Previously held buttons not in the new list are released. |

The same distinction applies to `axes` (omit / `null` = no change; `{}` = all axes reset to 0; explicit dict = replace) and `mouse_pos` (omit / `null` = no change; explicit `[x, y]` = move).

**Why explicit-empty is needed:** without `[]` semantics, releasing all buttons would require the agent to enumerate every previously-held button in the next event with the released ones omitted. That's error-prone for long-held inputs.

**Edge detection.** The harness internally tracks the previous frame's button state. `pyxel.btnp(K)` returns true at frame F when K was not in the previous frame's set but is in F's set. `pyxel.btnr(K)` returns true at frame F when K was in the previous frame's set but is not in F's set.

**Initial state.** Before any input event fires, all buttons are released, all axes are 0, mouse_pos is `(0, 0)`.

**Mouse position.** Pyxel exposes `mouse_x` / `mouse_y` as read-only globals. The harness uses Pyxel 2.9's `set_mouse_pos(x, y)` (or equivalent internal API) to drive these; if a Pyxel version lacks this API, harness manually patches the globals (see §13 open question).

**Button name namespace.** Strings match Pyxel's constant names: `"KEY_SPACE"`, `"KEY_LEFT"`, `"MOUSE_BUTTON_LEFT"`, `"GAMEPAD1_BUTTON_A"`, etc. Axes: `"GAMEPAD1_AXIS_LEFTX"`, etc. The harness translates strings to Pyxel int constants via `getattr(pyxel, name)`. Unknown names raise a validation error at tool call time.

### 6.4 Snapshot kinds (5)

#### 6.4.1 `screen_image`

Captures the rendered screen at a frame (or sequence of frames) as PNG file(s).

```python
Input (single-frame form):
{
    "frame": int,
    "kind": "screen_image",
    "output": str,          # absolute or run-cwd-relative path; parent dirs auto-created
    "scale": int = 1,       # upscaling factor; nearest-neighbor (no smoothing)
}

Input (multi-frame form, paired with §6.6 frames range syntax):
{
    "frames": list[int] | str,    # see §6.6
    "kind": "screen_image",
    "output_pattern": str,         # path with {frame} template (5-digit zero-padded)
    "scale": int = 1,
}

Output (per emitted SnapshotResult):
{
    "frame": int,
    "kind": "screen_image",
    "path": str,            # absolute path written
    "size": [int, int],     # [width, height] in pixels
}
```

**Scale algorithm:** Nearest-neighbor only. Pixel art must not be smoothed; smoothing produces blurry output that misrepresents the rendered state. PIL's `Image.resize(... resample=Image.NEAREST)` is the implementation.

**`output` vs `output_pattern`:** Single-frame snapshots use `output` (a literal path). Multi-frame snapshots (with `frames`) use `output_pattern`, where `{frame}` expands to the 5-digit zero-padded frame number (e.g., `"frames/{frame}.png"` → `"frames/00030.png"`). The two fields are mutually exclusive, matched to single-frame / multi-frame mode respectively. Validation errors otherwise.

#### 6.4.2 `screen_grid`

Captures the rendered screen as an inline 2D array of palette indices.

```python
Input: {
    "frame": int,
    "kind": "screen_grid",
    "bbox": [x, y, w, h] | None = None,    # default: full screen
}

Output: {
    "frame": int,
    "kind": "screen_grid",
    "bbox": [x, y, w, h],
    "grid": list[list[int]],    # row-major, palette indices 0-255
}
```

#### 6.4.3 `state`

Reads `App` instance attributes at the end of frame F.

```python
Input: {
    "frame": int,
    "kind": "state",
    "attrs": list[str] | [],    # dotted paths; empty = top-level scalar attrs only
}

Output: {
    "frame": int,
    "kind": "state",
    "values": dict[str, Any],    # path → value; values are JSON-serializable
    "warnings": list[str],       # e.g., "attr 'player.lives' not found"
}
```

**Attr path syntax:**
- Dotted: `"player.x"` → `getattr(getattr(app, "player"), "x")`.
- Indexed: `"barrels[0].y"` → `app.barrels[0].y`.
- Empty list `[]` returns App's top-level scalar/string/int/float/bool attrs only (no recursion into nested objects, no list/dict expansion).
- **Aggregate functions are NOT supported.** `len(barrels)` is not expressible. The agent must either inspect the list itself (which serializes if JSON-friendly) or have the script mirror `len(barrels)` into a top-level attr like `app.barrel_count`. This limitation is documented in the `pyxel-skill` `task-execution.md` knowledge.

**Value serialization:** Primitives (int, float, str, bool, None) pass through. Lists of primitives serialize as JSON arrays. Dicts of primitives serialize as JSON objects. Custom objects are represented as their `repr()` truncated to 200 chars with a `"<truncated>"` marker. Numpy arrays serialize as nested lists.

#### 6.4.4 `layout`

Layout balance analysis at frame F. Same algorithm as the existing `inspect_layout` analysis applied to the captured screen.

```python
Input: {
    "frame": int,
    "kind": "layout",
}

Output: {
    "frame": int,
    "kind": "layout",
    "h_balance": float,                          # 0-1, horizontal symmetry
    "v_balance": float,                          # 0-1, vertical symmetry
    "quadrant_density": [tl, tr, bl, br],        # 4 floats, normalized 0-1
    "center_of_mass": [float, float],
    "text_positions": list[{"x": int, "y": int, "text": str}],
    "warnings": list[str],
}
```

#### 6.4.5 `video`

Accumulates frames `[start_frame, end_frame)` during the run loop and encodes them into a single output file after the run completes.

```python
Input: {
    "kind": "video",
    "start_frame": int,
    "end_frame": int,        # exclusive
    "fps": int = 30,
    "output": str,           # extension determines format (see below)
    "scale": int = 1,        # nearest-neighbor upscaling
}

Output: {
    "kind": "video",
    "path": str,             # absolute path of the file actually written
    "format": "gif" | "mp4",
    "frame_count": int,      # frames actually encoded (see below)
    "duration_seconds": float,
    "warnings": list[str],
}
```

**Output extension validation:** The `output` extension MUST be one of `.gif` or `.mp4`. Any other extension (or no extension) is a validation error at tool call time. Future formats (e.g., `.webm`) require a spec amendment.

**Encoding pipeline:**
- `.gif`: PIL.Image.save with `append_images=[...]`, `loop=0`, `duration=int(1000/fps)`. No external dependency.
- `.mp4`: `ffmpeg -framerate {fps} -i {temp_dir}/%05d.png -c:v libx264 -pix_fmt yuv420p -movflags +faststart {output}`. Requires `ffmpeg` on PATH. **If ffmpeg is unavailable, the harness falls back to GIF**: it rewrites `path` to `<output_basename>.gif`, sets `format: "gif"`, and emits a warning `"ffmpeg unavailable; fell back to GIF: <new_path>"`. The agent is expected to handle either format.

**`frame_count` on crash:** This is the number of frames *actually written into the encoded file*. If the run crashed at frame F where `start_frame <= F < end_frame`, only `F - start_frame` frames were accumulated and encoded; `frame_count` reflects that lower number. If `end_frame > actual frames executed`, `frame_count` is also lower than `end_frame - start_frame`. The agent compares `frame_count` against the requested range to detect truncation.

**Range validation:** `start_frame >= 0`, `end_frame <= frames`, `start_frame < end_frame`. Violations are validation errors at tool call time.

**`frames` range syntax not supported:** `video` uses its own `start_frame` / `end_frame` fields. The §6.6 `frames` shorthand is rejected for `video` snapshots.

### 6.5 RunResult

```python
{
    "snapshots": list[SnapshotResult],    # see ordering rules below
    "exit_status": "ok" | "crashed" | "timeout" | "stalled",
    "frame_count": int,                   # actual frames executed (may be less than `frames` on crash)
    "elapsed_seconds": float,             # wall-clock harness time
    "log": str,                           # stdout + stderr from subprocess
    "seeded": bool,                       # was random_seed injected
    "errors": list[ToolError],            # per §5.4
}
```

**Snapshot ordering:**
- The output `snapshots` list preserves the **input order** of the input `snapshots` list.
- Single-frame inputs (using `frame`) produce **exactly one** SnapshotResult in the matching position.
- Multi-frame inputs (using `frames` per §6.6) expand into a **contiguous run** of N SnapshotResults at the original input's position, in **frame-ascending order** (e.g., a multi-frame snapshot at input position 3 with resolved frames `[30, 60, 120]` produces 3 SnapshotResults at output positions 3, 4, 5).
- `video` inputs always produce exactly one SnapshotResult (encoded after the run completes).

**Log content (informational reference):** The `log` field captures stdout + stderr from the harness subprocess. Common content the agent may scan for:
- Pyxel startup banner / version line
- Asset load failures (`"asset load failed: <path>"`)
- Pyxel runtime warnings (e.g., `"warning: cls() not called this frame"`)
- Python traceback when the script crashes
- Harness diagnostic messages prefixed `[pyxel-mcp]`

This list is non-exhaustive and informational; structured failures are reported via `errors` field, not parsed from `log`.

**Stall detection** (`exit_status="stalled"`) is opt-in via `stall_detection: bool = False` parameter (added to `run` signature; not shown above for brevity). When true, the harness computes a hash of `(screen_grid, state)` each frame and sets `stalled` if 60 consecutive frames have identical hash despite scheduled inputs. Default off; agent enables for long-path verification.

### 6.6 Verbose-snapshot reduction

For high-frequency snapshots (e.g., capture every frame's state), specifying 720 entries individually is verbose. `Snapshot` accepts `frames` (alternative to `frame`):

```python
{"frames": [30, 60, 120, 240], "kind": "state", "attrs": ["player.x"]}                # explicit list
{"frames": "0:720", "kind": "screen_image", "output_pattern": "frames/{frame:05d}.png"}  # range
{"frames": "0:720:10", "kind": "state", "attrs": ["player.y"]}                          # every 10
{"frames": "all", "kind": "screen_grid"}                                                # all frames
```

**Field consistency between `frame` and `frames` modes:**

| Mode         | Frame selector | Output destination (for `screen_image`) | Result count |
|--------------|----------------|------------------------------------------|--------------|
| Single-frame | `frame: int`   | `output: str` (literal path)             | 1            |
| Multi-frame  | `frames: ...`  | `output_pattern: str` with `{frame}` template (5-digit zero-padded) | N            |

`frame` / `frames` are mutually exclusive. `output` / `output_pattern` are mutually exclusive and matched to single / multi mode respectively. Mismatches (e.g., `frame: 30` paired with `output_pattern`) are validation errors.

For `state` and `screen_grid` snapshots (no file output), the multi-frame mode just emits N SnapshotResults inline.

For `layout` snapshots, multi-frame mode is supported and produces N analysis results.

`kind: "video"` does **not** accept `frames` — it has its own `start_frame` / `end_frame` fields (§6.4.5).

### 6.7 Example: DK win-path verification in 1 call

```python
run(
    script="main.py",
    frames=660,
    random_seed=42,
    inputs=[
        {"frame": 30,  "buttons": ["KEY_SPACE"]},
        {"frame": 32,  "buttons": []},
        {"frame": 60,  "buttons": ["KEY_RIGHT"]},
        {"frame": 120, "buttons": ["KEY_UP"]},
        {"frame": 280, "buttons": ["KEY_RIGHT"]},
        {"frame": 360, "buttons": ["KEY_UP"]},
        {"frame": 600, "buttons": ["KEY_UP"]},
        {"frame": 660, "buttons": []},
    ],
    snapshots=[
        # Per-milestone state + screen capture
        {"frame": 30,  "kind": "state", "attrs": ["scene", "player.x", "player.y", "lives"]},
        {"frame": 30,  "kind": "screen_image", "output": "frames/00030.png"},
        {"frame": 60,  "kind": "state", "attrs": ["player.x"]},
        {"frame": 120, "kind": "state", "attrs": ["player.y"]},
        {"frame": 280, "kind": "state", "attrs": ["player.x"]},
        {"frame": 360, "kind": "state", "attrs": ["player.y"]},
        {"frame": 600, "kind": "state", "attrs": ["player.y"]},
        {"frame": 660, "kind": "state", "attrs": ["scene"]},
        {"frame": 660, "kind": "screen_image", "output": "frames/00660.png"},
        # Whole-run video
        {"kind": "video", "start_frame": 0, "end_frame": 660, "fps": 30, "output": "win-path.gif"},
    ],
)
```

This single call produces:
- 8 state observations at milestone frames
- 2 screen captures (start, end)
- 1 GIF of the full win path

All from one deterministic execution. Compared to the current 16-tool surface, this would have required at least 5 separate calls (`play_and_capture` for screens, `inspect_state` for state — each at multiple frames — plus `record_gameplay` for the GIF), with no guarantee that all observations came from the same execution.

## 7. Static inspectors

### 7.1 `inspect_palette(script)`

Returns the palette state after `_build_assets()` runs.

```python
Output: {
    "colors": dict[int, str],                # idx → "#RRGGBB"
    "extended_palette": bool,                # was pyxel.colors.append called
    "palette_size": int,                     # count after extension
    "hierarchy": {
        "score": 0 | 1 | 2,                  # 0=poor, 1=partial, 2=good
        "background": list[int],
        "environment": list[int],
        "interactive": list[int],
    } | None,                                 # None if extended_palette (analysis n/a)
    "contrast_warnings": list[{
        "a": int, "b": int, "ratio": float, "message": str,
    }],
    "errors": list[ToolError],
}
```

**Color format:** Hex strings (`"#1d2b53"`). Human-readable; the harness formats from Pyxel's int representation. Agents needing RGB ints can parse on receipt; the cost of hex serialization is small.

**Hierarchy on extended palette:** When `pyxel.colors.append(...)` has been called and `palette_size > 16`, the 3-layer hierarchy analysis is skipped (`hierarchy: None`). Quality-gate check #8 (`Hierarchy score: 2/2`) is documented as not applicable for extended palettes; pyxel-skill convention is to use the default 16-color palette.

**Contrast analysis:** WCAG 2.0 contrast ratio computed for all pairs of colors used in the palette (as detected by reading the palette state). Warnings emitted for ratios < 3.0 between commonly co-located indices (e.g., a foreground color paired with the background color). Threshold and pair-detection algorithm match the existing `_common/format.py` implementation, ported verbatim.

### 7.2 `inspect_image(script, image, x, y, w, h, render_path)`

Reads pixels from image bank `image` at region `(x, y, w, h)`. Returns analytics inline; optionally writes a PNG visualization.

```python
Input: {
    "script": str,
    "image": int,                  # bank index
    "x": int = 0,
    "y": int = 0,
    "w": int | None = None,        # default: bank width
    "h": int | None = None,        # default: bank height
    "render_path": str | None = None,
}

Output: {
    "image_index": int,
    "bank_size": [int, int],       # [width, height] of the bank
    "region": {"x": int, "y": int, "w": int, "h": int},
    "pixels": list[list[int]] | None,    # null if region too large (see below)
    "color_count": dict[int, int],       # palette idx → pixel count in region
    "fill_ratio": float,                  # non-zero / total
    "symmetry": {"horizontal": float, "vertical": float} | None,
    "edge_density": float | None,         # outline density on perimeter
    "warnings": list[str],                # e.g., "fill_ratio outside [0.15, 0.95]"
    "rendered": str | None,               # absolute path if render_path given
    "errors": list[ToolError],
}
```

**Bank size handling:** Default `w=h=None` means "the actual size of `pyxel.images[image]`". If the user passes explicit `w`/`h` that exceed the bank's bounds, the region is clamped and a warning is emitted. If the bank index does not exist, `errors` contains a `script_import` or `build_assets` phase entry.

**Large region pixel return:** If `w * h > 4096`, `pixels` is set to `None` to avoid bloating JSON. The agent must use `render_path` to visualize large regions. `color_count`, `fill_ratio`, etc. are still computed.

**Threshold rationale (4096 = 64×64):** Common Pyxel sprite sizes are 8×8 (=64), 16×16 (=256), 24×24 (=576), 32×32 (=1024), 48×48 (=2304), 64×64 (=4096). 4096 is the upper bound of practical sprite analytics; full image banks (256×256 = 65536) and larger composite regions exceed this and produce JSON payloads of ~50 KB+ for the `pixels` field alone, which is wasteful when the agent only needs aggregate stats. Above the threshold, `inspect_image` continues to compute aggregate analytics (`color_count`, `fill_ratio`) but skips the pixel grid; agent uses `render_path` for visualization.

**Symmetry / edge_density:** Computed only when region is small enough to be a sprite (`w * h <= 4096`). For larger regions these analytics are meaningless (whole-bank symmetry is incidental) and are omitted (set to `None`).

### 7.3 `inspect_animation(script, image, x, y, w, h, frame_count, direction)`

Reads `frame_count` adjacent regions starting at `(x, y)`, each `(w, h)`, in the specified direction. Computes cross-frame analytics.

```python
Input: {
    "script": str,
    "image": int,
    "x": int, "y": int, "w": int, "h": int,
    "frame_count": int,                   # >= 2 (see validation below)
    "direction": "horizontal" | "vertical" = "horizontal",
}

Output: {
    "image_index": int,
    "frames": list[{
        "region": {"x": int, "y": int, "w": int, "h": int},
        "color_count": dict[int, int],
        "fill_ratio": float,
    }],
    "palette_consistency": float,    # 0-1, |intersect(frame_palettes)| / |union(frame_palettes)|
    "silhouette_stability": float,   # 0-1, mean Jaccard of consecutive fill masks
    "frame_diffs": list[{
        "from": int, "to": int, "diff_ratio": float,
    }],
    "warnings": list[str],
    "errors": list[ToolError],
}
```

**`frame_count >= 2`** is required (validation error otherwise). Single-frame inspection uses `inspect_image`.

**Direction:** `"horizontal"` reads regions at `(x, y), (x+w, y), (x+2w, y), ...`. `"vertical"` reads at `(x, y), (x, y+h), (x, y+2h), ...`. Range overflow (any region exceeds bank bounds) is a validation error.

**Cross-frame metric formulas (locked):**
- `palette_consistency = |∩ frame_i.color_count.keys()| / |∪ frame_i.color_count.keys()|` (Jaccard on palette index sets)
- `silhouette_stability = mean(|fill_mask_i ∩ fill_mask_{i+1}| / |fill_mask_i ∪ fill_mask_{i+1}|)` (Jaccard on per-pixel fill masks, averaged across consecutive pairs)
- `diff_ratio = (sum of pixels where frame_i != frame_{i+1}) / (w * h)` for adjacent pairs

These are pinned in spec so quality-gate check #4 (paired-frame diff in 5–50%) returns deterministic values regardless of implementation.

### 7.4 `inspect_tilemap(script, tilemap, render_path)`

Reads `pyxel.tilemaps[tilemap]` after `_build_assets()`.

```python
Input: {
    "script": str,
    "tilemap": int,
    "render_path": str | None = None,
}

Output: {
    "tilemap_index": int,
    "size": [int, int],
    "imgsrc": int,                       # which image bank tilemap draws from
    "tiles": list[list[[int, int]]] | None,  # 2D array of (u, v) tile coords; null if too large
    "usage": dict[str, int],             # "u,v" → tile count
    "bounding_box": {"x": int, "y": int, "w": int, "h": int} | None,  # non-(0,0) region
    "trap_warning": bool,                # (0,0) tile is non-empty in source bank
    "rendered": str | None,
    "errors": list[ToolError],
}
```

**Large tilemap handling:** Same as `inspect_image` — if `size[0] * size[1] > 4096`, `tiles` is `None`. The agent uses `usage`, `bounding_box`, and `render_path` for visualization.

**Trap warning:** True if the tile at source-bank coordinates (0, 0) has any non-transparent pixels. Pyxel tilemap cells default to (0, 0); a non-empty (0, 0) tile floods the entire tilemap.

## 8. Audit / discovery / audio

### 8.1 `validate(script)`

Static analysis on the script source. Replaces `validate_script`.

```python
Output: {
    "ok": bool,                          # true iff zero "error" severity issues
    "issues": list[{
        "severity": "error" | "warning" | "info",
        "line": int,
        "col": int | None,
        "category": str,                  # see taxonomy below
        "message": str,
    }],
    "errors": list[ToolError],
}
```

**Issue ordering:** Sorted by `line` ascending, then by severity (`error` > `warning` > `info`).

**Category taxonomy** (closed enum; future categories require spec update):
- `syntax` — Python syntax errors from `ast.parse`
- `anti_pattern.missing_colkey` — `pyxel.blt(...)` called without `colkey=` keyword
- `anti_pattern.tilemap_zero_zero` — visible tile placed at source-bank (0, 0)
- `anti_pattern.assets_in_update` — `pyxel.images[N].set(...)` called inside `update()` or `draw()`
- `anti_pattern.update_in_draw` — state mutation inside `draw()`
- `anti_pattern.iter_modify` — modifying a list while iterating it
- `anti_pattern.btn_one_shot` — `btn()` used for a one-shot action (should be `btnp()`)
- `anti_pattern.palette_animation` — palette mutation via index assignment in a loop
- `anti_pattern.cls_missing` — the first effective drawing operation in `draw()` is not `pyxel.cls(...)`. Variable assignments, conditional `return` statements, and helper-function calls that do not draw are permitted before `cls`. The detector flags `draw()` only if a draw API (`blt`, `bltm`, `pset`, `line`, `rect`, `rectb`, `circ`, `circb`, `tri`, `trib`, `text`, `pal`, `dither`) is invoked before any `cls()` call. Helper methods called from `draw()` are inlined for the analysis up to one level of depth.
- `anti_pattern.degree_radian_mix` — `math.sin/cos` used alongside `pyxel.sin/cos`
- `anti_pattern.other` — catch-all for future detectors before they get their own category

The `gate-report.json` in pyxel-skill's quality-gate stage consumes `ok` (top-level) for stop condition #2.

### 8.2 `pyxel_info()`

No-script discovery tool.

```python
Output: {
    "pyxel_mcp_version": str,             # "0.9.3"
    "pyxel_version": str,                 # e.g., "2.9.4"
    "python_version": str,                # e.g., "3.14.0"
    "stubs_path": str,                    # absolute path to pyxel.pyi
    "examples": list[{
        "name": str,                       # e.g., "01_hello_pyxel"
        "path": str,                       # absolute path to .py
        "description": str | None,
    }],
    "resources": {
        "api_reference": "pyxel://api-reference",
        "user_guide": "pyxel://user-guide",
        "mml_commands": "pyxel://mml-commands",
        "pyxres_format": "pyxel://pyxres-format",
        "default_palette": "pyxel://palette/default",
        "examples": "pyxel://examples/<name>",   # template URI
    },
}
```

`compatibility-matrix.md` in `pyxel-skill` reads `pyxel_mcp_version` and `pyxel_version` to validate the runtime.

### 8.3 `render_audio(script, target, output_path)`

Renders a single sound or music slot to WAV.

```python
Input: {
    "script": str,
    "target": {"sound": int} | {"music": int},  # union (exactly one)
    "output_path": str,
}

Output: {
    "path": str,                          # absolute path written
    "duration_seconds": float,
    "sample_rate": int,                   # 22050 for Pyxel default
    "channels": int,                      # 1 (mono)
    "peak_amplitude": float,              # 0.0 to 1.0
    "notes": list[{
        "frame": int,                      # internal Pyxel sound frame
        "note": str,                       # e.g., "C4"
        "tone": str,                       # "s" | "p" | "n" | "t"
        "volume": int,                     # 0-7
        "effect": str,                     # "n" | "s" | "v" | "f"
    }],
    "warnings": list[str],
    "errors": list[ToolError],
}
```

**Live audio capture (during a run) is out of scope for v0.9.3.** Quality-gate check #7 verifies declared sound slots are renderable, not that they triggered at expected frames during gameplay. The latter is reserved for a future `audio_state` snapshot kind in `run`.

### Aside: `target` as union

Old API had separate `sound_index` and `music_index` parameters that could in principle both be set, with undefined precedence. The new union enforces exactly one target, eliminating that ambiguity.

## 9. Artifact analyzer

### 9.1 `compare_frames(frame_a, frame_b)`

Pixel-wise diff between two PNG paths. No script required.

```python
Input: {
    "frame_a": str,                       # PNG path
    "frame_b": str,                       # PNG path
}

Output: {
    "identical": bool,                    # true iff zero pixel differences
    "size_match": bool,                   # are PNG dimensions equal
    "size_a": [int, int],
    "size_b": [int, int],
    "changed_pixels": int,                # 0 if size mismatch (see below)
    "total_pixels": int,
    "ratio": float,                       # changed / total, 0.0 if size mismatch
    "region": {"x": int, "y": int, "w": int, "h": int} | None,    # bounding box of changes
    "warnings": list[str],
    "errors": list[ToolError],
}
```

**Size mismatch:** When `size_a != size_b`, the tool returns `size_match: false`, `identical: false`, `changed_pixels: 0`, `ratio: 0.0`, `region: None`, and emits a warning "size mismatch; pixel comparison skipped". The agent decides whether to treat this as a regression (probably yes) or as expected (e.g., resolution change between attempts). The tool does not crop, scale, or center-align.

## 10. Migration impact on `pyxel-skill`

`pyxel-skill` v0.1.0 (in-flight, on `feat/harness-v5`) was authored against the current 16-tool surface. The redesign requires coordinated updates to its stage files. Estimated rewrite scope per file:

| File | Scope | Primary changes |
|------|-------|-----------------|
| `SKILL.md` | small | Required runtime version → `pyxel-mcp ≥ 0.9.3`, capabilities table tool names |
| `visual-target.md` | minimal | text-only, no tool calls |
| `decomposer.md` | minimal | 1-2 example tool calls in Verify rubric |
| `scaffold.md` | small | `validate_script` → `validate`, `run_and_capture` → `run` (5-6 places) |
| `asset-planner.md` | minimal | example update only |
| `asset-gen.md` | medium | per-sprite verify loop uses `inspect_image` + `inspect_animation` |
| `task-execution.md` | **heavy** | per-task 9-step loop entirely re-illustrated for `run` snapshot pattern |
| `quality-gate.md` | **heavy** | 12 stop conditions table "How" column rewritten |
| `quirks.md` | none | Pyxel API quirks; no tool names |
| `test-harness.md` | **heavy** | win/lose milestone playthrough from per-milestone tool chains to single-`run` snapshot lists |
| `capture.md` | medium | bundle composition uses `run` with `video` + `screen_image` snapshots |
| `knowledge/*.md` (all 5) | none | design knowledge; no tool names |
| `hooks/*` | none | bundle integrity check; no tool names |
| `docs/architecture.md` | small | tool list update |
| `docs/validation/dk-reference.md` | small | example tool calls |

**Total: 3 heavy + 2 medium + 5 small + 5 minimal/none.** The `task-execution.md`, `quality-gate.md`, and `test-harness.md` rewrites are the substantial part.

The pyxel-skill design itself (7 stages, 4 state files, anti-shortcut rules, gate, hooks, knowledge files) is unchanged. The redesign only affects how stages call `pyxel-mcp` tools.

## 11. Implementation strategy

### 11.1 Source-tree organization

```
src/pyxel_mcp/
├── server.py                             # FastMCP server, registers 9 tools
├── instructions.md                       # tool catalog for AI agents (concise; full schemas via MCP Resources)
├── _harnesses/
│   ├── main.py                           # subprocess entry point + subcommand dispatcher
│   ├── _common/
│   │   ├── script_loader.py              # script import + cwd handling
│   │   ├── pyxel_patcher.py              # headless mode + state isolation
│   │   ├── input_scheduler.py            # set_btn / set_btnv per-frame application
│   │   ├── snapshot_kinds/
│   │   │   ├── screen_image.py
│   │   │   ├── screen_grid.py
│   │   │   ├── state.py
│   │   │   ├── layout.py
│   │   │   └── video.py
│   │   ├── analyzers/
│   │   │   ├── palette.py
│   │   │   ├── image.py
│   │   │   ├── animation.py
│   │   │   └── tilemap.py
│   │   └── error_capture.py              # uniform ToolError shape
│   └── tools/
│       ├── run.py                        # orchestrates input_scheduler + snapshot_kinds
│       ├── inspect_palette.py
│       ├── inspect_image.py
│       ├── inspect_animation.py
│       ├── inspect_tilemap.py
│       ├── validate.py
│       ├── pyxel_info.py
│       ├── render_audio.py
│       └── compare_frames.py
└── _resources/
    ├── (existing MCP Resources: api-reference, user-guide, ...)
    └── run_snapshots_schema.md           # detailed snapshot schema, surfaced as pyxel://run-snapshots-schema
```

**Why this layout:**
- `tools/` are thin handlers (parse args, dispatch to `_common/`). Each tool is one file.
- `_common/snapshot_kinds/` and `_common/analyzers/` are reusable modules with single responsibility.
- `main.py` is one entry point invoked by `server.py` via subprocess; subcommand dispatch keeps the subprocess interface small and testable.
- The tree is flat-ish. Each file should remain under ~300 lines of Python.

### 11.2 server.py structure

The MCP server (FastMCP) registers each of the 9 tools as an MCP function. Each registration:

1. Accepts the tool's parameters via FastMCP decorator.
2. Serializes the tool's parameters to JSON.
3. Spawns subprocess `python -m pyxel_mcp._harnesses.main <subcommand>` (no parameters in argv beyond the subcommand name).
4. Writes the parameter JSON to the subprocess's **stdin** and closes stdin.
5. Reads stdout (JSON result) and stderr (logs).
6. Returns the parsed JSON result. For `run`, stderr → `log` field; for inspectors, stderr → merged into `errors[].message` if non-empty.
7. On subprocess timeout (per `timeout` parameter or default), kills the process and returns `exit_status="timeout"` (for `run`) or an error result (for other tools).

**Why stdin (not argv) for parameter passing:** A `run` call's snapshot schedule can be hundreds of lines of JSON. macOS / Linux `ARG_MAX` is ~256 KB, and shell escape of arbitrary JSON in argv is fragile. stdin handles arbitrary size and avoids quoting issues. The subprocess interface is `<binary> <subcommand>` + JSON-on-stdin → JSON-on-stdout.

`server.py` itself contains no Pyxel logic; it is purely a dispatcher.

### 11.3 Test infrastructure

Existing `pyxel-mcp` has 234 passing tests against the 16-tool surface. The redesign requires:

- **Replacement:** Tests bound to old tool names are rewritten for the new tools.
- **Addition:** New tests for `run`'s 5 snapshot kinds, the `frames` range syntax, `random_seed` injection, error handling phases, large-region pixel return policy, etc.
- **Reuse:** Test utilities (subprocess fixture, JSON assertion helpers) are reused; bare test cases are rewritten.

Estimated count: 250–300 tests after redesign. TDD: each new tool / snapshot kind is implemented test-first.

### 11.4 instructions.md and per-tool docstrings

Per §5.6, two distinct surfaces convey tool information to the agent: per-tool docstrings (FastMCP decorator) and `instructions.md` (server-wide instructions payload).

**Per-tool docstrings** (FastMCP `@mcp.tool()` parameter or first-line docstring):
- Concise: ~10-30 lines per tool
- Content: 1-paragraph purpose + signature summary + 1 canonical example
- Cross-links to instructions.md for workflow guidance and to `pyxel://...` resources for full schemas
- Written inline in `server.py`, alongside each `@mcp.tool()` registration

**`src/pyxel_mcp/instructions.md`** (~150-200 lines):
- Server-wide overview: what pyxel-mcp does, how to use the 9-tool surface together
- Workflow patterns (e.g., "use `run` with state+screen snapshots for milestone verification")
- Pyxel-API quirks index (cross-link to `pyxel://api-reference`)
- Cross-link to `pyxel-skill` repo for full production workflow
- Pointer to `pyxel://run-snapshots-schema` for the `run` snapshot schema in full detail

**Migration:** The current 0.9.3 in-flight `instructions.md` (223 lines, trimmed from 906; design-knowledge extracted to pyxel-skill/knowledge/) is **rewritten from scratch** for the 9-tool surface. The separation-of-concerns principle (mcp = technical verbs; skill = design knowledge) is preserved on merit; the existing trimmed content is reference material, not a base to incrementally edit.

### 11.5 ffmpeg as optional system dependency

The `video` snapshot kind uses ffmpeg only for MP4 output. Documentation:
- `README.md` lists ffmpeg as an optional dependency.
- `pyxel_info()` does not currently report ffmpeg availability; this is a possible future addition.
- When `output: "*.mp4"` is requested without ffmpeg on PATH, the harness emits a warning and falls back to GIF (output path adjusted to `.gif`).

## 12. Release plan

### 12.1 Version

`0.9.3` is the working version label for this redesign. The version may be revised at release time depending on the actual scope of changes (a 1.0.0 bump is justifiable given the breaking nature, but the choice is deferred to user judgment per the project's `feedback_versioning` memory).

The current `feat/v0.9.3-trim-instructions` branch (which carries the in-flight trim) becomes the working base for the redesign. The trim commits are preserved in history; the new commits add the redesign on top.

### 12.2 Phases

```
Phase 1  pyxel-mcp 0.9.3 spec doc (this document) → user review
Phase 2  pyxel-mcp 0.9.3 implementation plan via writing-plans skill
Phase 3  pyxel-mcp 0.9.3 implementation via subagent-driven-development (TDD)
Phase 4  pyxel-skill stage files rewrite plan via writing-plans skill
Phase 5  pyxel-skill stage files rewrite via subagent-driven-development
Phase 6  Local DK validation against feat branches (no PyPI publish yet)
         - test dir uses local-dev .mcp.json pointing to feat/v0.9.3-trim-instructions branch
         - iterate until DK reaches gate all-PASS with recognizable sprites + clear win/lose paths
Phase 7  User reviews validation results, declares "perfect" or requests iteration
Phase 8  pyxel-mcp 0.9.3 PyPI publish (only on user approval)
Phase 9  pyxel-skill v0.1.0+ tag (post-PyPI publish)
```

**Phase 6 may iterate.** Initial DK validation in 2026-05-01 with the in-flight 0.9.2/0.9.3 surface stopped at Stage 6 R1; the redesigned surface is expected to allow deeper progress in fewer iterations, but multiple validation rounds are anticipated.

### 12.3 Branch hygiene

- `pyxel-mcp` `feat/v0.9.3-trim-instructions`: continues as the working branch for 0.9.3 redesign. The trim commits remain at the base of the branch.
- `pyxel-skill` `feat/harness-v5`: tag the current head as `v0.1.0-pre-redesign` for archival, then the same branch (or a new branch off it) carries the stage-file rewrites. Branch naming TBD at Phase 4.

## 13. Open questions and risks

1. **Pyxel 2.9 mouse-position API.** The spec assumes Pyxel 2.9+ exposes a way to set `mouse_x` / `mouse_y` (either a `set_mouse_pos` API or direct module-attribute assignment). Verify against current Pyxel source before implementing `mouse_pos` in InputEvent. If the API does not exist, harness implementation may need to monkey-patch `pyxel._mouse_x` etc.
2. **Pyxel `set_btnv` argument-range convention.** §6.3 accepts axis values matching SDL gamepad ranges (typically `-32768..32767` for sticks, `0..32767` for triggers). Verify Pyxel's actual `set_btnv` signature accepts the same int range; if Pyxel normalizes to floats `-1.0..1.0`, the harness must convert before calling.
3. **`stall_detection` overhead.** Computing a state hash every frame is non-trivial. Default-off keeps the common path fast; enabling it for long-path verification incurs ~5-15% slowdown depending on state size. Acceptable; document.
4. **`ffmpeg` availability assumption.** Pyxel-skill tests on macOS in development; ffmpeg is typically installed via brew. CI environments (when added) need ffmpeg in their image. Headless servers may not have it; the GIF fallback is the safety net.
5. **Validation iteration count.** The redesign aims to make DK validation pass in 1-2 iterations vs the current 4+. This is an expectation, not a guarantee. If the redesigned surface still requires many iterations, additional design refinement may be needed before PyPI publish.
6. **`pyxel://run-snapshots-schema` MCP Resource.** This is a new resource URI; pyxel-mcp's resource-serving infrastructure must be extended to provide the schema as either a static markdown or a JSON Schema file.
7. **Anti-pattern category taxonomy completeness.** The closed enum in §8.1 covers anti-patterns the project knows about today. New patterns discovered during DK validation may require enum extensions; spec amendments are expected and noted as iterative.
8. **Spec ↔ implementation alignment validation.** During implementation (Phase 3), discrepancies between this spec and what's actually built will surface. Process: (a) implementer flags discrepancy in implementation plan task, (b) controller decides spec amendment vs implementation correction, (c) if amendment, this spec is updated and committed before implementation proceeds. The plan (Phase 2 output) is responsible for naming the discrepancy-tracking artifact.
9. **`repr()` truncation length (200 chars) is a default, not a hard rule.** Custom App attrs of pathological size (e.g., a list of 10000 enemies serialized inline) could still bloat the result. If real-world cases warrant, the limit becomes a `state` snapshot parameter (`max_repr_chars`); deferred until needed.

## 14. References

- `htdt/godogen` (`/tmp/godogen` checkout) — capability reference for Bevy/Godot harness
- `pyxel-skill` design spec — `/Users/takashi/repos/pyxel-skill/docs/superpowers/specs/2026-05-01-pyxel-harness-design.md`
- `pyxel-skill` v0.1.0 implementation plan — `/Users/takashi/repos/pyxel-skill/docs/superpowers/plans/2026-05-01-pyxel-skill-v0.1.0-implementation.md`
- `pyxel-mcp` 0.9.3 trim plan (predecessor of this redesign) — `/Users/takashi/repos/pyxel-skill/docs/superpowers/plans/2026-05-01-pyxel-mcp-0.9.3-trim-implementation.md`
- DK validation 2026-05-01 retrospective notes — referenced in this project's auto-memory at `~/.claude/projects/-Users-takashi-repos-pyxel-mcp/memory/project_pyxel_skill_harness.md`

---

End of spec.
