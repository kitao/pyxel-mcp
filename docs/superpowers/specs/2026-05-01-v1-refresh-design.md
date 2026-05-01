# Pyxel MCP 1.0.0 Refresh Design

## Goal

Modernize pyxel-mcp for Pyxel 2.9.4, polish every file to a 1.0
release-quality bar, and adopt MCP Resources to give AI agents
first-class access to Pyxel reference material.

The release marks the first stable major version — interface stays
mostly backward-compatible, internals are reorganized for clarity, and
two new tools (`record_gameplay`, analog-input extension to
`play_and_capture`) leverage Pyxel 2.9 capabilities.

## Non-Goals

- Adding MCP Prompts — client UX still uneven; revisit post-1.0.
- Replacing existing tools or breaking their public signatures.
- Rewriting `instructions.md` from scratch — its game-design knowledge
  (142-game analysis, SE cookbook, genre palettes) is the MCP's unique
  value and stays. We update it for 2.9 APIs and trim only obsolete
  bits.
- Rust/native extensions — pyxel-mcp remains pure Python.

## Motivation

Pyxel 2.9.4 added meaningful capabilities that the MCP doesn't
surface: `screencast` for GIF output in headless mode, `set_btnv`
for analog-stick simulation, `resize` for runtime screen changes, and
a redesigned `gen_bgm` whose new required parameters silently break
the cookbook examples we ship today.

Concurrently the codebase has accumulated structural debt — `server.py`
is 1097 lines holding all 13 tool definitions, and the flat
`_module.py` layout no longer scales. A refresh now is cheaper than
later, and re-anchors the project at a stable 1.0 line.

## Scope Summary

| Area | Change |
|------|--------|
| Pyxel dependency | `>=2.8.9` → `>=2.9.4` |
| Python support | `>=3.10` (unchanged); add 3.14 classifier |
| Code layout | Flat `_*.py` → `_common/`, `_tools/`, `_harnesses/`, `_resources/` subpackages |
| New tool | `record_gameplay` (GIF via `screencast`) |
| Extended tool | `play_and_capture` accepts `btnv` analog input |
| MCP Resources | Pyxel docs (4) + examples (~20) + palette reference |
| `instructions.md` | Update for 2.9 APIs, fix `gen_bgm` examples, add Resources guidance |
| Tests | 174 → ~220+, covering new tools, resources, refactor |
| Version | 0.9.2 → 1.0.0 |

---

## Phase 1: Code Reorganization

### 1.1 Subpackage layout

```
src/pyxel_mcp/
  __init__.py
  server.py              # FastMCP instance, instructions load, main()
  instructions.md
  
  _common/               # Shared helpers (was _*.py at package root)
    __init__.py
    audio.py             # was _audio.py
    errors.py            # was _errors.py
    format.py            # was _format.py
    headless.py          # was _headless.py
    palette.py           # was _palette.py
    pyxel_env.py         # NEW — Pyxel install lookup, version check, script validation
    subprocess.py        # was _subprocess.py
    validate.py          # was _validate.py
  
  _tools/                # Tool definitions, grouped by README category
    __init__.py          # registers all tools with the FastMCP instance
    run.py               # run_and_capture, capture_frames, play_and_capture, record_gameplay
    inspect.py           # inspect_state, inspect_screen, compare_frames, validate_script
    visual.py            # inspect_sprite, inspect_layout, inspect_palette,
                         # inspect_bank, inspect_tilemap, inspect_animation
    audio.py             # render_audio
    info.py              # pyxel_info
  
  _resources/            # MCP Resources (new)
    __init__.py          # registers all resources with the FastMCP instance
    docs.py              # pyxel://api-reference, user-guide, mml-commands, pyxres-format
    examples.py          # pyxel://examples/<name>
    palette.py           # pyxel://palette/default
  
  _harnesses/            # Subprocess scripts (was *_harness.py at root)
    __init__.py
    audio.py             # was audio_harness.py
    bank.py              # was bank_harness.py
    frames.py            # was frames_harness.py
    input.py             # was input_harness.py
    layout.py            # was layout_harness.py
    main.py              # was harness.py
    screen.py            # was screen_harness.py
    sprite.py            # was sprite_harness.py
    state.py             # was state_harness.py
    tilemap.py           # was tilemap_harness.py
    record.py            # NEW — for record_gameplay
```

**Rationale:**

- The four roles (server glue, tool defs, resources, subprocess
  harnesses) become four directories. `_common/` is the shared toolkit.
- `_harness` filename suffix becomes redundant inside `_harnesses/` —
  drop it. Same for `_tools/`.
- Underscore prefixes are kept on directories to mark internals.

### 1.2 `server.py` slim-down

Target: ~80 lines.

```python
"""MCP server for Pyxel."""
import os
from mcp.server.fastmcp import FastMCP

from pyxel_mcp._tools import register_tools
from pyxel_mcp._resources import register_resources

_INSTRUCTIONS_PATH = os.path.join(os.path.dirname(__file__), "instructions.md")
with open(_INSTRUCTIONS_PATH) as f:
    _INSTRUCTIONS = f.read()

mcp = FastMCP("pyxel-mcp", instructions=_INSTRUCTIONS)
register_tools(mcp)
register_resources(mcp)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
```

`_tools/__init__.py` exposes a single `register_tools(mcp)` that
imports each tool module and calls its `register(mcp)`. Same pattern
for `_resources`.

This keeps the FastMCP wiring readable in one screen, and tool
definitions live next to their helpers.

### 1.3 Cross-cutting helpers stay where they are conceptually

- `_pyxel_dir()`, `_check_script()`, version check helpers — currently
  in `server.py`. Move to `_common/pyxel_env.py` (new) since they're
  about the Pyxel installation, not server bootstrap.
- `_INSTRUCTIONS` load logic — stays in `server.py`; trivial.

### 1.4 Harness subprocess invocation

Harnesses are currently launched via `python <package>/x_harness.py`.
Switching to subpackage layout means launching as a module:
`python -m pyxel_mcp._harnesses.x`. `_common/subprocess.py` adjusts
its launch helper to use `-m <module>` form.

This is a private contract — no external users — so the change is safe.

---

## Phase 2: New Tools

### 2.1 `record_gameplay`

**Purpose:** Capture animation, transitions, and gameplay flow as a
single GIF. Replaces the awkward "capture 5 PNGs and squint" workflow
for animation verification.

**Signature:**

```python
@mcp.tool()
async def record_gameplay(
    script_path: str,
    duration: int = 60,        # frames to record
    inputs: str = "[]",        # same JSON shape as play_and_capture
    scale: int = 1,
    timeout: int = 15,
) -> Image:
    """Record gameplay as a GIF using Pyxel's screencast.

    Returns the GIF as a single image for visual verification of
    animations, transitions, and gameplay over time. For input-driven
    sequences, pass a JSON string of frame events in `inputs`
    (same format as play_and_capture).
    """
```

**Implementation (`_harnesses/record.py`):**

1. Launch script with patched `pyxel.run` (existing
   `setup_harness`/`patch_game_loop` from `_common/headless.py`).
2. In the per-frame callback, apply input events at their target frame
   (reuses `play_and_capture` input loop).
3. After `duration` frames, call `pyxel.screencast(filename)` then
   exit. Pyxel buffers all rendered frames internally — headless
   `draw_frame` already calls `capture_screen` (verified in
   `crates/pyxel-core/src/system.rs:283-303`).
4. Server reads the resulting `.gif` and returns it as an `Image`.

**Bounds:** `1 ≤ duration ≤ 600` (10 sec @ 60fps), `1 ≤ scale ≤ 4`,
`1 ≤ timeout ≤ 60`. Larger durations risk client image limits.

**Why a new tool, not extension of `capture_frames`:** `capture_frames`
returns N separate images for inspection; `record_gameplay` returns 1
GIF for animation flow. Different output types, different uses.

### 2.2 `play_and_capture` analog extension

**Current input event shape:**

```json
{"frame": 30, "keys": ["KEY_SPACE"]}
```

**Extended shape (additive, fully backward compatible):**

```json
{
  "frame": 30,
  "keys": ["KEY_SPACE"],
  "btnv": {"GAMEPAD1_AXIS_LEFTX": 16384}
}
```

**Implementation:**

- `_harnesses/input.py` already loops events and calls `set_btn`. Add
  a `btnv` branch calling `pyxel.set_btnv(key, val)`.
- Validation in `_tools/run.py`: `btnv` keys must be valid Pyxel
  constants (resolved via `getattr(pyxel, name)` in the harness),
  values must be int.
- Both `keys` and `btnv` may appear in the same event. Either may be
  omitted.

**Constants supported:** Any `GAMEPAD*_AXIS_*` constant. Validation is
delegated to Pyxel — invalid names error out at harness time with a
clear message routed back through stderr.

---

## Phase 3: MCP Resources

### 3.1 Resource set

| URI | Source | Update strategy |
|-----|--------|-----------------|
| `pyxel://api-reference` | `https://raw.githubusercontent.com/kitao/pyxel/main/docs/api-reference.md` | fetch + 24h in-memory cache |
| `pyxel://user-guide` | `.../docs/user-guide.md` | fetch + 24h cache |
| `pyxel://mml-commands` | `.../docs/mml-commands.md` | fetch + 24h cache |
| `pyxel://pyxres-format` | `.../docs/pyxres-format.md` | fetch + 24h cache |
| `pyxel://examples/<name>` | local `pyxel/examples/<name>.py` | read on demand |
| `pyxel://palette/default` | static, generated from `_common/palette.py` | static |

`<name>` for examples is the basename without `.py`:
`01_hello_pyxel`, `02_jump_game`, ..., `99_flip_animation`.

The example list is built by scanning the installed Pyxel's
`examples/` directory at server startup. If Pyxel isn't installed, the
list is empty and only the doc/palette resources are advertised.

### 3.2 Resource registration

```python
# _resources/__init__.py
def register_resources(mcp: FastMCP) -> None:
    register_docs(mcp)
    register_examples(mcp)
    register_palette(mcp)
```

Each module uses `@mcp.resource("pyxel://...")`. Doc resources and the
palette resource are static (one decorator per URI). Examples are
enumerated dynamically — each discovered example becomes a concrete
static resource so AI clients can see the full list via
`list_resources`:

```python
def register_examples(mcp: FastMCP) -> None:
    for name in _scan_examples():  # ["01_hello_pyxel", ...]
        # bind name into the closure via default arg
        @mcp.resource(f"pyxel://examples/{name}", name=name)
        def _read(name=name) -> str:
            return _load_example(name)
```

Rationale for enumeration over a single `pyxel://examples/{name}`
template: AI discovery is a primary use case ("what examples are
available?"). A template only shows up in `list_resource_templates`
which not every client surfaces well.

FastMCP supports both static and templated resource URIs (verified by
inspecting `mcp.server.fastmcp.FastMCP.resource` in the installed SDK).

### 3.3 Caching

- Doc fetch: simple module-level dict `{url: (timestamp, content)}`.
- TTL: 24h. On read, refetch if expired or missing.
- On fetch failure (network down): return last cached content if
  available; else raise an MCP error with a hint to use `pyxel_info`'s
  local stubs path as a fallback.
- No disk cache — keeps server startup fast and memory simple.

### 3.4 Palette resource format

Markdown table the AI can paste into context:

```markdown
# Pyxel Default Palette (16 colors)

| Idx | Name      | Hex      | RGB           | Common use |
|-----|-----------|----------|---------------|------------|
| 0   | black     | #000000  | (0, 0, 0)     | bg, outline |
| 1   | navy      | #2B335F  | (43, 51, 95)  | dark bg, shadows |
| ...
```

Sourced from `_common/palette.py` (already has names + RGB; "common
use" added inline as a static list). Total ~20 lines.

---

## Phase 4: `instructions.md` Updates

### 4.1 Bug fixes (current content has wrong examples)

The "Quick BGM" section currently shows:

```python
mml = pyxel.gen_bgm(7, 1, seed=42)        # ← missing transp (now required)
pyxel.gen_bgm(preset, instr, seed=42, play=True)  # ← wrong arg order
```

Pyxel 2.9.0 made the signature `gen_bgm(preset, transp, instr, seed,
play=False)` with `transp`, `instr`, `seed` all required. Audit every
`gen_bgm(` occurrence in instructions.md and update — including the
scene-specific BGM dict where `(preset, instr, seed)` tuples need to
become `(preset, transp, instr, seed)`.

### 4.2 New API coverage

Add concise sections documenting:

- **`pyxel.resize(w, h)`** — runtime screen resize. Use cases:
  options menus, responsive layouts. One short example.
- **`pyxel.screencast(filename)`** — note that the MCP exposes this
  via `record_gameplay`; users writing scripts can also call it
  directly.
- **`pyxel.set_btnv`** — covered in the `play_and_capture` example
  block under "Testing Input-Dependent Logic".

### 4.3 New tool documentation

- Add `record_gameplay` to the workflow checklist (step 4) and to the
  "Reading Tool Output" section.
- Update `play_and_capture` section with analog example.

### 4.4 Resources discovery

New short section: "Pyxel Reference via MCP Resources".

```markdown
### Pyxel Reference via MCP Resources

In addition to `pyxel_info`, this MCP server exposes Pyxel docs and
official examples as resources:

- `pyxel://api-reference` — full API reference
- `pyxel://user-guide` — concepts and patterns
- `pyxel://mml-commands` — MML syntax
- `pyxel://pyxres-format` — .pyxres file structure
- `pyxel://examples/<name>` — official examples (e.g. `02_jump_game`)
- `pyxel://palette/default` — 16-color reference

In Claude Code, reference them with `@pyxel:api-reference` etc.
```

### 4.5 No restructuring

The existing 23-section structure (visual design, SE cookbook, game
patterns, etc.) is the differentiated value of this MCP and stays.
Updates are surgical.

---

## Phase 5: Quality Pass

Per-file review with these criteria:

- **`server.py` (post-split):** ≤100 lines, no tool definitions.
- **`_common/format.py` (569 lines):** Largest helper. Audit for
  splittable groups (sprite/layout/palette/state/animation report
  formatters are independent). Split into `_common/format/` package
  with one file per report type IF the file is hard to navigate;
  otherwise leave alone — splitting for its own sake is anti-policy.
- **`_common/audio.py` (251 lines):** WAV analysis is one concern. Keep
  as single file; review for dead code and naming.
- **All harnesses:** Verify they use `setup_harness` /
  `patch_game_loop` from `_common/headless.py`. Any straggler that
  still hand-rolls headless setup gets migrated.
- **Docstrings:** Every public tool has an MCP-visible docstring with
  Args. Verify formatting consistency. (Doc generation is a future
  concern; consistency now is enough.)
- **Type hints:** Add return types to every tool function. Use
  `list[str]` etc. (Python 3.10+ syntax) — already required by
  `requires-python`.
- **Error messages:** Run grep for "pyxel" vs "pyxel-mcp" — make sure
  user-facing errors recommend the right package.

Decision rule for splitting `_common/format.py`: if at the end of all
other refactors it remains the largest file by 2x and is the most
edited during the refactor, split it. Otherwise leave it.

---

## Phase 6: Tests

### 6.1 New tests

- `tests/test_resources.py` — list_resources returns expected URIs;
  read_resource for `pyxel://palette/default` returns valid markdown;
  example resource resolves an installed example; doc cache returns
  stale content on fetch failure (mocked).
- `tests/test_record_gameplay.py` — integration test (marked
  `integration`) that runs a tiny Pyxel script and verifies a non-empty
  GIF is returned. Validation tests for bounds and bad input.
- `tests/test_play_and_capture_analog.py` — verify `btnv` events are
  forwarded to `set_btnv`. Use a script that reads
  `pyxel.btnv(GAMEPAD1_AXIS_LEFTX)` and writes it to state, then
  inspect the result.

### 6.2 Refactor tests

- `tests/test_imports.py` — every public module imports cleanly,
  no circular imports, `pyxel_mcp.server.main` is callable.
- Existing tests adjust to new import paths
  (`from pyxel_mcp._common.audio import ...` etc.).

### 6.3 Test target

220+ tests, all passing. `make test` (or `pytest`) green on a clean
checkout with Pyxel 2.9.4.

---

## Phase 7: Release Artifacts

### 7.1 `pyproject.toml`

```toml
[project]
version = "1.0.0"
requires-python = ">=3.10"
dependencies = ["mcp>=1.0.0,<2.0.0", "pyxel>=2.9.4", "numpy"]
classifiers = [
    "Development Status :: 5 - Production/Stable",  # was Beta
    ...
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",  # NEW
    ...
]
```

### 7.2 `server.json`

Bump `version` to `1.0.0`, both top-level and inside `packages[0]`.

### 7.3 `CHANGELOG.md`

New section at top, before 0.9.2:

```markdown
## 1.0.0

- Bump Pyxel minimum version to 2.9.4
- Reorganize package into _common/_tools/_harnesses/_resources subpackages
- Slim server.py to FastMCP wiring only
- Add record_gameplay tool — capture gameplay as GIF via screencast
- Extend play_and_capture with btnv analog input events
- Add MCP Resources: pyxel://api-reference, user-guide, mml-commands,
  pyxres-format, examples/<name>, palette/default
- Update instructions.md for Pyxel 2.9 APIs (resize, screencast, set_btnv)
- Fix gen_bgm examples in instructions.md for Pyxel 2.9 signature
- Mark Production/Stable; add Python 3.14 classifier
```

### 7.4 `README.md`

- Add `record_gameplay` to Run & Capture section
- Add "Resources" section listing the 6 resource URIs
- Bump quoted version where present

### 7.5 Publish steps

Per repo CLAUDE.md:

```
rm -rf dist/ && .venv/bin/python -m build
.venv/bin/python -m twine upload dist/*
git push origin main
mcp-publisher login github  # ask user first — token expires
mcp-publisher publish server.json
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Subpackage refactor breaks user imports | All `_*` modules are private; FastMCP entry point and `pyxel-mcp` CLI script are the only public surface. Verified via grep that nothing else is documented as importable. |
| `screencast` headless behavior differs from windowed | Verified in Pyxel source: `draw_frame` always calls `capture_screen` regardless of headless. Integration test will catch regressions. |
| Doc fetch hangs offline | 5s urlopen timeout (matches `_check_updates` pattern), serve stale cache on failure. |
| MCP Resources unsupported by older clients | FastMCP advertises capabilities; clients that don't support resources just ignore them. No tool functionality regresses. |
| `gen_bgm` signature change confuses existing user code | Out of scope — that's a Pyxel 2.9 break. We only fix our own examples. |

## Open Questions

None blocking. Test the cache TTL value (24h) against actual usage
during dogfooding; can adjust before tagging 1.0.0.

## Success Criteria

- `pytest` passes with 220+ tests against Pyxel 2.9.4
- `pyxel-mcp` boots, advertises 14 tools and ~25 resources
- `record_gameplay` produces a valid GIF for `02_jump_game.py`
- `play_and_capture` accepts both old and new input shapes
- All `instructions.md` `gen_bgm` examples run cleanly under Pyxel 2.9.4
- README, CHANGELOG, server.json, pyproject.toml all show 1.0.0
- Published to PyPI and MCP Registry
