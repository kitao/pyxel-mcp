# pyxel-mcp v1.0.0 Godogen-Style Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drop the entire Layer 2 (judge_*) tool surface and refactor the skill markdown set to godogen-style "agent-driven visual primacy" — replacing 17-check numerical-default matrix with a flat 11-step stop-conditions list, and replacing tool-mediated predicate evaluation (judge_milestone / judge_genre with sandboxed AST eval) with agent-direct Python asserts against `state` snapshots.

**Architecture:** The MCP server reduces from 17 tools to 9 (Layer 1 observe only): `pyxel_info`, `validate`, `run`, `read_palette`, `read_image`, `read_animation`, `read_tilemap`, `read_audio`, `diff_frames`. Quality verification moves entirely into the skill: agent runs `run` to capture state snapshots + frames, then asserts predicates directly in Python AND uses the `Read` tool to inspect captured PNG bundles, verbalizing against PLAN.md / ASSETS.md anchors. No tool encodes a numerical default; "good" is judged by what the captured frames show.

**Tech Stack:** Python ≥3.10, Pyxel ≥2.9.5, FastMCP, PIL/Pillow, pytest, hatchling.

**Memory references:**
- `feedback_numerical_defaults_brittle.md` (root cause of recurring failure mode)
- `feedback_read_base_material_first.md` (godogen as base material — its design philosophy continues into v1.0.0)
- `feedback_self_playtest_loop.md` (agent's multimodal Read loop is the gate)
- `feedback_e2e_scale.md` (small-scale PASS is necessary, not sufficient — DK-scale validation required)

**Branch:** `feat/v1.0.0-integrate-skill` (continues; commits land here, no new branch).

**v1.0.0 status:** Not yet released to PyPI. Refactor lands as part of the pre-release work; CHANGELOG `## 1.0.0 (unreleased)` entries gain a major-refactor block. Version number stays 1.0.0 (no PyPI users to break).

---

## File Structure (target after implementation)

```
src/pyxel_mcp/
├── __init__.py                          (unchanged)
├── server.py                            ~165 lines (was ~272 — 9 tools only)
├── cli.py                               (unchanged — install / publish-skill / serve)
├── instructions.md                      ~120 lines (rewrite — Layer 1 only)
├── observe/                             (unchanged — 9 Layer 1 harnesses)
├── workflow/                            (unchanged — workflow_root + _content/)
├── _resources/                          (unchanged — 16 MCP resource URIs)
└── (judge/ DELETED ENTIRELY — 968 LOC removed)

skill/
├── SKILL.md                             ~150 lines (refactor — drop Layer 2, mantras, 8 anti-shortcut rules)
├── quality-gate.md                      ~250 lines (FULL REWRITE — 11-step flat list, no judge_* calls)
├── task-execution.md                    ~190 lines (refactor — visual primacy embedded, direct Python asserts)
├── decomposer.md                        ~240 lines (refactor — Genre Identity / milestones use Python predicates)
├── capture.md                           ~210 lines (refactor — drop judge_bundle/judge_audio examples; agent review is the gate)
├── asset-planner.md                     ~160 lines (refactor — drop judge_sprite/judge_animation references)
├── asset-gen.md                         ~180 lines (refactor — drop judge_sprite reference, agent direct verify)
├── visual-target.md                     ~170 lines (minor — wording sweep, no judge refs to remove)
├── scaffold.md                          ~220 lines (minor — wording sweep)
├── test-harness.md                      (unchanged — Pattern C closed-loop)
├── quirks.md                            (unchanged — Pyxel API gotchas)
├── README.md                            (unchanged)
├── knowledge/                           (all 5 files unchanged — pixel-art / background / game-feel / audio / patterns)
└── hooks/
    ├── stop_check_bundle.py             ~70 lines (refactor — drop gate-report.json inspection, keep bundle-missing tripwire only)
    ├── test_stop_check_bundle.py        ~adjust to new shape
    ├── install.sh                       (unchanged)
    └── README.md                        (unchanged)

tests/
├── judge/                               (DELETED ENTIRELY — 1181 LOC removed, ~63 tests)
├── (everything else unchanged)
└── conftest.py                          (unchanged — no judge references)

docs/
├── CHANGELOG.md                         ~adjust 1.0.0 block (major refactor entry)
└── superpowers/plans/2026-05-04-godogen-style-refactor.md  (this file)
```

**Test count delta:** 413 → ~350 (delete 63 judge tests, no other test impact since no non-judge test references the judge layer).

---

## Task 1: Drop judge layer from server (mechanical)

**Files:**
- Modify: `src/pyxel_mcp/server.py:11` (remove judge import)
- Modify: `src/pyxel_mcp/server.py:164-214` (remove 8 judge_* @mcp.tool() registrations)
- Modify: `src/pyxel_mcp/server.py:228-235` (remove 8 judge_* aliases)
- Delete: `src/pyxel_mcp/judge/` (entire directory, 11 files, 968 LOC)
- Delete: `tests/judge/` (entire directory, 10 files, 1181 LOC)

- [ ] **Step 1: Remove judge import line**

In `src/pyxel_mcp/server.py`, delete line 11:

```python
from pyxel_mcp import judge as _judge
```

- [ ] **Step 2: Remove judge_* tool registrations**

In `src/pyxel_mcp/server.py`, delete lines 164-214 (the entire block from `# --- Layer 2: judge_* policy primitives ...` through the closing of `judge_layout`). Replace with nothing — the file moves directly from `diff_frames` (line 162) to the alias block (was line 217).

- [ ] **Step 3: Remove judge_* aliases**

In `src/pyxel_mcp/server.py`, delete lines 228-235:

```python
judge_palette_tool = judge_palette
judge_sprite_tool = judge_sprite
judge_animation_tool = judge_animation
judge_milestone_tool = judge_milestone
judge_genre_tool = judge_genre
judge_bundle_tool = judge_bundle
judge_audio_tool = judge_audio
judge_layout_tool = judge_layout
```

- [ ] **Step 4: Verify server.py compiles**

Run: `.venv/bin/python -c "from pyxel_mcp.server import mcp; print(len(mcp._tool_manager._tools))"`
Expected: `9` (the 9 Layer 1 tools).

- [ ] **Step 5: Delete judge/ directory tree**

Run: `rm -rf src/pyxel_mcp/judge`

Verify: `/bin/ls src/pyxel_mcp/` does not list `judge`.

- [ ] **Step 6: Delete tests/judge/ directory tree**

Run: `rm -rf tests/judge`

Verify: `/bin/ls tests/` does not list `judge`.

- [ ] **Step 7: Run full test suite, verify expected count drop**

Run: `.venv/bin/python -m pytest tests/ -q 2>&1 | /usr/bin/tail -3`
Expected: `~350 passed, 1 skipped` (down from 413).
If failures: read each failure carefully — there may be incidental judge references in fixtures or conftest that didn't show in grep. Fix or delete those references.

- [ ] **Step 8: Stage and commit**

```bash
git add -A src/pyxel_mcp/server.py src/pyxel_mcp/judge tests/judge
git status  # confirm: deletions of judge/, edits to server.py
git commit -m "$(cat <<'EOF'
refactor(v1.0.0)!: drop judge layer entirely (godogen-style visual primacy)

The 8 judge_* tools (palette / sprite / animation / milestone / genre /
bundle / audio / layout) had hardcoded numerical DEFAULT_CONTRACT values
that fought legitimate game-design idioms across every e2e validation
cycle. 4 fix sessions (abed9fe / 0d10a45 / 3b2e2a4 / 7161d37, 16 fixes
total) all share the same root cause: a numerical default contradicted
either pyxel-skill's own knowledge files or its own examples, and tuning
one knob always surfaced another for the next game type. The pattern is
unbounded.

godogen — the design base for this project — solves this by having zero
numerical default thresholds: agent multimodal eyes are the gate, with
"Bias toward failure" repeated as a cultural mantra across every stage
file. This refactor adopts the same approach.

This commit removes the server-side surface only. The skill markdown
refactor (which actually moves verification to agent-direct Python
asserts and Read-PNG verbalization) lands in follow-up commits.

- src/pyxel_mcp/judge/ deleted (968 LOC, 11 files)
- tests/judge/ deleted (1181 LOC, 10 files)
- src/pyxel_mcp/server.py: 9 judge_* tool registrations + aliases removed

Tests: 413 -> ~350 (delta = deleted judge tests; no other test impact).
Memory: feedback_numerical_defaults_brittle.md captures the root cause.
EOF
)"
```

---

## Task 2: Update instructions.md for Layer 1 only

**Files:**
- Modify: `src/pyxel_mcp/instructions.md` (rewrite Layer 1/2 split into Layer 1 only)

- [ ] **Step 1: Read current instructions.md to scope the changes**

Run: `Read src/pyxel_mcp/instructions.md`

Identify all Layer 2 sections / `judge_*` references / "17 tools" wording.

- [ ] **Step 2: Rewrite instructions.md**

Replace the file with content that:
- Removes the entire "Layer 2 — judge" section
- Removes any "17 tools" wording, replacing with "9 tools" or simply the tool list
- Keeps the Layer 1 tool descriptions intact (run / validate / pyxel_info / read_palette / read_image / read_animation / read_tilemap / read_audio / diff_frames)
- Adds one short paragraph at the end: "Quality verification (judging whether captured state / frames meet a contract) is the agent's responsibility, not a tool's. The agent runs Layer 1 tools to capture observations, then asserts predicates directly in Python or by reading captured PNG bundles with the `Read` tool."

Use `Read` then `Write` for the full rewrite. Keep tool argument signatures verbatim.

- [ ] **Step 3: Sanity check**

Run: `.venv/bin/python -c "from pyxel_mcp.server import _INSTRUCTIONS; print(_INSTRUCTIONS[:200])"`
Expected: instructions text loads, no Layer 2 / judge_* mentions in the first 200 chars.

Run: `/usr/bin/grep -c "judge_\|Layer 2" src/pyxel_mcp/instructions.md` → expected `0`.

- [ ] **Step 4: Commit**

```bash
git add src/pyxel_mcp/instructions.md
git commit -m "docs(v1.0.0): instructions.md drops Layer 2, Layer 1 only

The 9 observe tools are the entire MCP surface now. Verification belongs
to the agent: capture observations via Layer 1, assert in Python or via
Read-PNG verbalization."
```

---

## Task 3: Rewrite skill/quality-gate.md (centerpiece)

**Files:**
- Modify: `skill/quality-gate.md` (full rewrite — 267 lines → ~250 lines, godogen-style)

This is the largest single content change. Replace the entire file with the new flat 11-step stop-conditions list below.

- [ ] **Step 1: Replace skill/quality-gate.md with the new content**

Use `Write` (after reading the existing file once for the Read precondition) to replace the file with this content verbatim:

````markdown
# Stage 7: Quality Gate

Final acceptance check. PASS gates "done"; FAIL routes back to the phase that owns the failed check. The gate is **agent-driven visual primacy** — the agent (you) reads bundle frames with the `Read` tool, verbalizes observations against PLAN.md / ASSETS.md anchors, and asserts state predicates directly in Python. There are no numerical default thresholds — "good" is judged by what the captured frames actually show.

This file contains no `judge_*` calls. The harness's contract is the agent's discipline: run the 11 stop conditions in order, write `gate-report.json`, route every FAIL to its owning phase, and re-run from the top.

## Inputs

- `PLAN.md` (Stage 2) — Win Path / Lose Path Milestones, **`## Genre Identity`** rules, optional `## Difficulty floor override`.
- `STRUCTURE.md` (Stage 3) — `FPS` constant.
- `ASSETS.md` (Stage 4) — sprite manifest (especially `represents:` strings) + audio manifest.
- `MEMORY.md` — gotchas accumulated across phases.
- `screenshots/result/<N>/` — proof bundle from `capture.md` (win-path GIF, lose-path GIF, frames/, audio/).
- `pyxel://run-snapshots-schema` (MCP resource) — snapshot field shapes.

## Output

`screenshots/result/<N>/gate-report.json` — flat list of 11 stop conditions, each PASS or FAIL with evidence. The gate writes this file regardless of overall PASS/FAIL — the artifact is what the user reviews. `<N>` is the bundle counter `task-execution` and `capture.md` produced — the gate writes its report inside the existing bundle directory rather than creating a new one.

## Order of execution

Run the 11 stop conditions in numeric order. Cheap structural checks first; expensive playthrough-driven checks last; agent visual review is the closing gate.

If a check FAILs, stop and write the gate report with the FAIL even if later checks would have passed. Partial reports are valid input for routing — there is no benefit in running #4 (Win path) when #1 (State files) has already failed.

## Stop conditions (all 11 must PASS)

### 1. State files

PASS condition: `PLAN.md`, `STRUCTURE.md`, `ASSETS.md`, `MEMORY.md` all exist and are non-empty.

```python
from pathlib import Path
for name in ("PLAN.md", "STRUCTURE.md", "ASSETS.md", "MEMORY.md"):
    p = Path(name)
    assert p.is_file() and p.stat().st_size > 0, f"{name}: missing or empty"
```

FAIL routes to: `visual-design` / `spec` / `scaffolding` / `asset-planning` (whichever file is missing).

### 2. Validate clean

PASS condition: `validate(script="main.py")` returns no errors.

```python
result = validate(script="main.py")
assert not result.get("errors"), f"validate errors: {result['errors']}"
```

FAIL routes to: `playthrough`.

### 3. Smoke run

PASS condition: a 30-frame `run` returns `exit_status=="ok"` AND the captured PNG is non-empty AND the agent reads the PNG and confirms it is not entirely black/blank.

```python
result = run(script="main.py", frames=30, snapshots=[
    {"frame": 29, "kind": "screen_image", "output": "tmp/smoke.png"},
])
assert result["exit_status"] == "ok"
assert Path("tmp/smoke.png").stat().st_size > 200  # > empty PNG header
# Then: Read tmp/smoke.png and confirm it shows expected scene state.
```

FAIL routes to: `scaffolding` (no scene rendered) or `playthrough` (early crash).

### 4. Win path

Agent runs the win path and asserts each PLAN.md milestone predicate **directly in Python** against the returned state values. No tool wraps the predicate; no sandbox restricts which Python you can write.

```python
result = run(
    script="main.py", frames=720, random_seed=42,
    inputs=<PLAN.md Win Path inputs>,
    snapshots=[
        {"frames": [<every milestone frame>], "kind": "state",
         "attrs": [<every attr referenced in any milestone>]},
    ],
)

assert result["seeded"] is True, "non-deterministic playthrough — refusing to gate"

snaps = {(s["kind"], s["frame"]): s for s in result["snapshots"]}
v = lambda f, a: snaps[("state", f)]["values"][a]

# One assertion per PLAN.md Win Path milestone row:
assert v(60, "scene") == "PLAY", f"frame 60: scene={v(60,'scene')!r}"
assert v(60, "player.x") > 10
assert v(300, "score") >= 100
assert v(660, "scene") == "WIN"
```

PASS condition: every milestone assert holds. `random_seed=42` is mandatory — if `result["seeded"]` is False, mark FAIL with reason `"non-deterministic playthrough"` even if the asserts happen to pass this attempt.

FAIL routes to: `playthrough` (game can't reach milestone) or `spec` (predicate references attribute not exposed by the App).

### 5. Lose path

Same shape as #4 but with PLAN.md Lose Path inputs and asserts. Final assert must be `scene == "GAME_OVER"`.

FAIL routes to: `playthrough` (hazards too soft) or `spec` (predicate misaligned).

### 6. Difficulty floor

PASS condition: lose path reaches `GAME_OVER` inside the FPS-derived window. Default band: `int(10*fps)` ≤ game_over_frame ≤ `int(14*fps)`. Below = unfair (player has no time to react). Above = the lose-path schedule is not reliably triggering GAME_OVER, which means hazards or collision logic are too soft.

```python
fps = int(structure_constants["FPS"])
lo, hi = int(10 * fps), int(14 * fps)

# Find the frame where scene first becomes "GAME_OVER"
go_frames = [s["frame"] for s in result["snapshots"]
             if s["kind"] == "state" and s["values"].get("scene") == "GAME_OVER"]
assert go_frames, "no GAME_OVER frame in lose-path snapshots"
go = min(go_frames)
assert lo <= go <= hi, f"GAME_OVER at frame {go}, expected {lo}-{hi}"
```

**Genre exception.** If PLAN.md declares a `## Difficulty floor override` section (e.g. survival-genre 60 s round, one-screen puzzle 3-4 s), use that band instead. Anti-shortcut #5 still applies — the override locks before the run begins, not after a failing run.

FAIL routes to: `playthrough` / `spec`. Both routes — fix the underlying cause, do not widen the band.

### 7. Audio

For every audio cue declared in ASSETS.md, render to WAV and verify peak / notes.

```python
for cue in audio_manifest:  # one entry per SE / per BGM channel
    obs = read_audio(script="main.py",
                     target={"sound": cue["sound_id"]},
                     output_path=f"screenshots/result/{N}/audio/{cue['name']}.wav")
    assert Path(obs["output_path"]).is_file()
    assert obs["peak_amplitude"] >= 0.02, f"{cue['name']}: silent (peak={obs['peak_amplitude']})"
    assert len(obs["notes"]) >= 1, f"{cue['name']}: no notes (slot empty?)"
```

**Always render against sound slots, not music slots, when feeding the gate** — `target={"music": N}` produces a WAV but no `notes` list, so the audio test cannot verify it. For BGM, walk the music slot's constituent sound IDs and render each as a sound. A whole-mix `target={"music": N}` render is fine for a peak-amplitude sanity check but is not gateable.

FAIL routes to: `sprite-quality` (slot empty) or `scaffolding` (slot wrong).

### 8. Proof bundle + dead-time

PASS condition: `screenshots/result/<N>/` contains the bundle layout from `capture.md`:
- `win-path.gif` (or `.mp4`)
- `lose-path.gif` (or `.mp4`)
- `frames/` with at least 5 PNGs (`title.png`, `play_start.png`, `mid_game.png`, `win.png`, `game_over.png`)
- `audio/*.wav` per ASSETS.md audio manifest
- `notes.md`

PASS condition (dead-time check): the bundle proves motion across its full duration. Pick two PNGs that are visually mid-game (NOT title vs game_over — alphabetical first-vs-mid pairs frequently land on backgrounds-only frames that are legitimately similar) and use `diff_frames` to confirm they differ.

```python
import os
bundle = Path(f"screenshots/result/{N}")
required = ["win-path.gif", "lose-path.gif", "notes.md", "frames", "audio"]
for r in required:
    assert (bundle / r).exists(), f"missing {r}"

png_files = sorted((bundle / "frames").glob("*.png"))
assert len(png_files) >= 5, f"only {len(png_files)} frame PNGs"

# Dead-time: pick the largest pairwise diff across the bundle, must exceed 0.05.
# (Alphabetical first-vs-mid is unreliable — see commit abed9fe.)
max_diff = 0.0
for i in range(len(png_files)):
    for j in range(i + 1, len(png_files)):
        r = diff_frames(frame_a=str(png_files[i]), frame_b=str(png_files[j]))
        if not r.get("size_match", True):
            assert False, f"frame size mismatch: {png_files[i].name} vs {png_files[j].name}"
        if not r.get("identical", False):
            d = r.get("diff_ratio", 0.0)
            if d > max_diff:
                max_diff = d
assert max_diff >= 0.05, f"all bundle frames within 5% diff — bundle is static"
```

A bundle whose first 3 seconds are correct and the rest is static is FAIL, not partial pass (Anti-shortcut #4).

FAIL routes to: `bundle` (missing artifacts) or `playthrough` (frozen entity / frozen camera).

### 9. Tilemap trap clean

For every tilemap declared in STRUCTURE.md: PASS condition: `read_tilemap(script="main.py", tilemap=N)` returns `trap_warning: False`.

The `(0,0)` trap = the source bank's tile at `(0,0)` has visible pixels, and the tilemap uses `(0,0)` for "empty" cells. Result: every "empty" cell renders that sprite, producing a stair-step pattern across the whole screen. Easy to miss in a small screenshot, fatal in a 256×256 tilemap.

```python
for tm in structure_tilemaps:  # e.g. [0, 1]
    obs = read_tilemap(script="main.py", tilemap=tm)
    assert obs.get("trap_warning") is False, f"tilemap {tm}: (0,0) trap detected"
```

FAIL routes to: `sprite-quality` (clear `(0,0)` of the source bank) or `scaffolding` (remap empty cells).

### 10. Genre identity

For each rule in PLAN.md `## Genre Identity` (3+ rules required by `decomposer.md`): agent runs the rule's `Verify:` predicate as Python.

The Verify predicate is **the agent's Python code**, not a string parsed by a tool. Each rule typically has a small `run` call with specific inputs and asserts — the same shape as #4/#5 but scoped to one mechanic.

Example for "ladders are the only floor-to-floor path":

```python
result = run(
    script="main.py", frames=120, random_seed=42,
    inputs=[{"frame": 30, "buttons": ["KEY_SPACE"]}, {"frame": 32, "buttons": []}],
    snapshots=[
        {"frame": 29, "kind": "state", "attrs": ["player.y"]},
        {"frame": 60, "kind": "state", "attrs": ["player.y"]},
    ],
)
y_before = result["snapshots"][0]["values"]["player.y"]
y_after  = result["snapshots"][1]["values"]["player.y"]
girder_pitch = STRUCTURE_CONSTANTS["GIRDER_PITCH_Y"]
assert (y_before - y_after) <= girder_pitch, \
    f"jump bypassed a girder: y went from {y_before} to {y_after}, pitch={girder_pitch}"
```

PASS condition: every rule's predicate holds. If PLAN.md lacks the `## Genre Identity` section or any predicate fails, the gate FAILs.

FAIL routes to: `spec` (rules absent) or `playthrough` (predicate fails).

### 11. Agent visual review (THE GATE)

This is the gate's primary check — tool-based observations certify mechanics, but only the agent's own multimodal eyes certify *recognizability* and *playability*.

After all bundle artifacts exist (#8 PASS), the agent (you) must:

1. List bundle frame PNGs:
   - `screenshots/result/<N>/frames/title.png`
   - `screenshots/result/<N>/frames/play_start.png`
   - `screenshots/result/<N>/frames/mid_game.png`
   - `screenshots/result/<N>/frames/win.png`
   - `screenshots/result/<N>/frames/game_over.png`

2. For each PNG, **use the `Read` tool to open it**. The Pyxel canvas is small (typically 224×256), so the multimodal LLM reads every pixel.

3. Verbalize observation in 1-2 sentences per frame, covering all of:
   - **Sprite identity** — does the player sprite match ASSETS.md `represents:` (e.g. "red-cap plumber, mid-stride")? Or is it a single-color rectangle, an unrecognizable blob, the wrong sprite?
   - **Scene state** — TITLE / PLAY / WIN / GAME_OVER as the PLAN.md milestone for this frame implies?
   - **HUD content** — score / lives / level / "PRESS SPACE" prompts — visible, legible, no overflow, no overlap with gameplay sprites?
   - **Animation state** — mid-stride / climbing / jumping / falling / dead as the milestone implies?
   - **Background and hazards** — playfield populated (girders, ladders, pickups, hazards) or mostly empty? Are barrels / enemies in plausible positions?

4. Compare each verbalization against the corresponding PLAN.md milestone description. Note divergences explicitly: "milestone says barrel near floor at frame 200, observation: barrel still on girder 1".

5. **If any frame shows a defect** — missing sprite, wrong scene, static animation, placeholder rectangle, illegible HUD, recognizability failure — return to the owning stage:
   - `asset-gen.md` for sprite identity
   - `scaffold.md` for scene routing / HUD layout
   - `decomposer.md` for milestone alignment
   - `task-execution.md` for animation / hazard implementation

   Do NOT proceed to mark the gate PASS.

6. The verbalizations populate `gate-report.json["agent_review"]`. Empty / boilerplate ("scene shown", "looks fine") / contradictory verbalizations are **themselves a FAIL** — the gate is built to catch this exact shortcut.

FAIL routes to: `playthrough` / `sprite-quality` / `scaffolding`.

## Visual primacy mantras (read before writing the gate report)

These mantras echo across `SKILL.md`, `task-execution.md`, `capture.md`, and `decomposer.md`. They are the gate's contract.

- **Do not trust code alone.** When code says X but the captured frame shows Y, trust the frame.
- **Bias toward failure.** If the required behavior is not clearly visible in the capture, treat it as not done.
- **No partial pass.** A bundle whose first 3 seconds look right and then sits static is FAIL, not partial pass.
- **No verbalization, no PASS.** A 10/11 PASS with empty / boilerplate `agent_review` is itself a FAIL.

## gate-report.json schema

One row per check. The gate writes this file regardless of overall PASS/FAIL.

```json
{
  "attempt": 1,
  "fps": 30,
  "checks": [
    {"id": 1, "label": "State files", "result": "PASS"},
    {"id": 2, "label": "Validate", "result": "PASS"},
    {"id": 3, "label": "Smoke run", "result": "PASS"},
    {"id": 4, "label": "Win path", "result": "PASS",
     "evidence": "all milestones asserted; final scene=WIN at frame 660"},
    {"id": 5, "label": "Lose path", "result": "PASS"},
    {"id": 6, "label": "Difficulty floor", "result": "PASS",
     "evidence": "GAME_OVER at frame 372 (12.4s @ 30fps, in 10-14s band)"},
    {"id": 7, "label": "Audio", "result": "PASS",
     "evidence": "5 WAVs rendered, all peak >= 0.02, all sounds have notes"},
    {"id": 8, "label": "Proof bundle + dead-time", "result": "PASS",
     "evidence": "12 PNGs; max pairwise diff 0.18"},
    {"id": 9, "label": "Tilemap trap clean", "result": "PASS"},
    {"id": 10, "label": "Genre identity", "result": "PASS",
     "evidence": "3 of 3 rules passed"},
    {"id": 11, "label": "Agent visual review", "result": "PASS"}
  ],
  "agent_review": {
    "title": "TITLE scene with the game name centered, 'PRESS SPACE' blinking below, no gameplay sprites visible.",
    "play_start": "Mario in red cap and blue overalls at bottom-left girder; DK boss at top with scaffolding visible; princess and 'HELP!' text on top platform; HUD shows 1UP 0000 / HIGH 0000 / L=01.",
    "mid_game": "Mario climbing ladder on girder 3; one barrel mid-air falling between girders 1 and 2; another rolling on girder 2; HUD shows score 0300, lives 3.",
    "win": "Mario adjacent to princess on top platform; 'YOU WIN!' overlay text visible; HUD shows final score 8500.",
    "game_over": "Mario sprite shows death frame at floor; 'GAME OVER' overlay text; HUD shows score 1200, lives 0."
  },
  "summary": {"pass": 11, "fail": 0, "total": 11}
}
```

The `fail_route` field is required on every FAIL row. PASS rows may omit `evidence` when the check is binary; FAIL rows must include enough evidence to act on.

## Anti-shortcut rules (restated for the agent at gate time)

These are the cheats the gate is built to catch. Read them before writing `gate-report.json`.

1. **"It compiles and runs, looks fine."** Checks #2 / #3 only certify no-crash. Checks #4 / #5 (direct Python asserts on state snapshots) are the gameplay certifications.
2. **"I added a sprite."** Without check #11 (agent reads the PNG and matches against ASSETS.md `represents:`), the sprite is unverified.
3. **"Bundle exists."** Without check #8's max-pairwise-diff dead-time test, the bundle could be a 30-frame loop with stale frames.
4. **"Audio plays."** Without check #7's peak ≥ 0.02 + notes ≥ 1 per slot, the slot may be silent or empty. A `play()` call alone passes #2 and #3 but fails #7.
5. **Adjusting milestones to fit.** *Most important.* If the game can't reach WIN by the planned frame, fix the game, not the milestone. Loosening the spec to dodge a FAIL is the failure mode this gate exists to prevent. The `## Difficulty floor override` (and any other override declared in PLAN.md) **locks before the run begins**, not after a failing run.
6. **`trap_warning: True` is a silent killer.** Tilemap (0,0) trap = stair-step pattern across the whole screen. Check #9 catches it.
7. **No unseeded gate playthroughs.** Win/lose paths use `random_seed=42` unless PLAN.md declares an alternative. If `result["seeded"] is False`, mark #4 / #5 FAIL with reason `"non-deterministic playthrough"` even if the asserts happen to pass this attempt. Determinism is a precondition, not an optimization.
8. **No bundle without honest agent review.** A green stop-conditions list with empty / boilerplate / contradictory `agent_review` is itself a FAIL. Tool checks (`run` snapshots, `read_audio`, `diff_frames`) certify mechanics; only the agent's verbalization certifies recognizability and playability. Fabricating observations to skip the review is the deepest form of shortcut this gate exists to catch.

## What happens on FAIL

For each FAIL row in `gate-report.json`:

1. Route to the phase named in `fail_route`. The phase reads its own state files plus the FAIL evidence and decides what to change.
2. Apply the remediation (fix the bug, redraw the sprite, retune the difficulty, regenerate the bundle). Update `MEMORY.md` if the fix is non-obvious — future sessions will need it.
3. Bump the bundle counter `<N>` and produce a fresh `screenshots/result/<N>/` per `capture.md`. Stale bundles are not patched in place.
4. Re-run the gate from check #1. **Do not retry the gate without remediation** — re-running the same checks against the same artifacts produces the same `gate-report.json`.

If multiple checks FAIL, route to the earliest-stage owner first (e.g., #11 sprite-recognizability before #4 playthrough) — fixing upstream often resolves downstream failures. The gate is not a debugger; it tells you *which* phase owns the failure, not *what code* to change.

### Common FAIL patterns

- **#4 reaches PLAY but never WIN.** Win-trigger logic missing → `playthrough`.
- **#5 reaches PLAY and stays past the lose-path window.** Hazard / collision too soft → `playthrough`.
- **#6 GAME_OVER frame outside FPS band.** Hazards too aggressive (frame < lo) or too gentle (frame > hi) → `playthrough`.
- **#7 audio peak == 0.0 with `slot empty` warning.** Sound slot was never assigned → `sprite-quality`.
- **#8 max pairwise diff < 0.05.** Mid-bundle frames identical (frozen entity / camera) → `playthrough`.
- **#9 `trap_warning: True`.** Source-bank `(0,0)` has visible pixels and tilemap uses `(0,0)` → `sprite-quality` (clear source) or `scaffolding` (remap empty cells).
- **#11 verbalization contradicts ASSETS.md `represents:`.** Sprite drawn doesn't match the design — wrong sprite swapped in, or the sprite was implemented as a placeholder rectangle → `sprite-quality` or `asset-gen`.

## When this gate PASSes

All 11 checks PASS in `gate-report.json`. Then:

- `PLAN.md` shows all milestone rows marked `done` with one-line `verified by:` notes.
- `MEMORY.md` records any non-obvious gotchas worth keeping for next session.
- The latest `screenshots/result/<N>/` bundle is the deliverable, and `screenshots/result/<N>/gate-report.json` proves the bundle was accepted.

Report to the user (concise; the bundle and `gate-report.json` carry the detail):

- **Bundle path** — `screenshots/result/<N>/`. The user opens the GIFs and WAVs from there.
- **One-line summary** — game title, win condition, lose condition.
- **Any caveats** — known limitations, out-of-scope items deferred, anything the gate did not check.

Then stop. Done. Do not start the next iteration speculatively; if the user wants polish or a new feature, they will say so.
````

- [ ] **Step 2: Verify markdown shape**

Run: `/usr/bin/grep -c "judge_\|Layer 2" skill/quality-gate.md` → expected `0`.
Run: `/usr/bin/wc -l skill/quality-gate.md` → expected `~250-280`.

- [ ] **Step 3: Commit**

```bash
git add skill/quality-gate.md
git commit -m "$(cat <<'EOF'
docs(v1.0.0): rewrite quality-gate.md as 11-step flat list (godogen-style)

- Drop the 17-check matrix that depended on judge_* numerical defaults.
- Replace with 11 stop conditions, each evaluated by the agent in Python:
  state files, validate, smoke, win path direct assert, lose path direct
  assert, difficulty floor, audio (read_audio + manual peak/notes check),
  proof bundle + max-pairwise-diff dead-time, tilemap trap, genre identity
  (Python predicate), agent visual review.
- Genre identity rules become Python code the agent writes directly,
  not strings the AST sandbox parses (no abs/len/min/max friction).
- Audio rendering retains the target={"sound": N} guidance from β3.
- Anti-shortcut rules collapse from 9 to 8, with stronger emphasis on
  visual primacy mantras (Bias toward failure, No partial pass, No
  verbalization no PASS).
EOF
)"
```

---

## Task 4: Refactor skill/SKILL.md

**Files:**
- Modify: `skill/SKILL.md` (~167 lines → ~150 lines)

- [ ] **Step 1: Read current SKILL.md**

Run: `Read skill/SKILL.md`

- [ ] **Step 2: Apply targeted edits**

Apply these specific edits:

**Edit 2.1** — Required runtime tool list. Find the bullet list under "If the namespace is missing, the user can get the install snippet by running:" (lines ~14-22) and remove the Layer 2 line. The new tool list:

```markdown
- `pyxel_info` (discovery — versions + paths + resource URIs)
- `validate` (static analysis — 10 anti-pattern detectors)
- `run` (dynamic execution — N frames, scheduled inputs, snapshots)
- `read_palette` / `read_image` / `read_animation` / `read_tilemap` / `read_audio` (raw observation)
- `diff_frames` (PNG pixel diff)
```

(Drop the `judge_palette / judge_sprite / ...` line entirely.)

**Edit 2.2** — Pipeline diagram. Stage 7 line currently reads:
```
+-- Stage 7  quality-gate   -> flat stop-conditions list; FAIL -> loop back to phase that owns the failure
```
Keep as-is (already godogen-style wording).

**Edit 2.3** — Anti-shortcut rules. The current list has 9 items. Update to:

```markdown
## Anti-shortcut rules

These are the cheats this harness exists to catch. Do not commit any of them.

1. **Visual primacy.** When code says X happened but a captured frame shows Y, trust the capture.
2. **Trust media over code.** A passing `validate` and a non-crashing `run` only certify the script does not crash. They do not certify gameplay.
3. **No procedural fallback.** `pyxel.rect(x, y, 16, 16, 8)` in place of a declared sprite means asset-gen was skipped. Go back. The `pyxel.rect()` calls for player/enemy bodies are a red flag.
4. **Bundle integrity.** A `screenshots/result/<N>/` bundle whose first 3 seconds are correct and the rest is static is FAIL, not partial pass.
5. **Bias toward failure.** If behavior is not clearly visible in the capture, treat as not-done. Hidden or inferred behavior does not count.
6. **Closed-loop input only.** Open-loop scripted input drifts past ~200 frames. Issue `run` calls in segments per Pattern C (cumulative-replay), reading observed `state` snapshots between segments and recomputing the next input schedule from the actual position.
7. **No "looks fine".** Every verify is a specific Python predicate against an observed value, not a vibe check. The predicate is *your* code; no tool wraps it for you.
8. **No bundle, no done.** A `screenshots/result/<N>/` directory containing win-path.gif, lose-path.gif, frames, audio WAVs is the precondition for declaring "done". A green gate report without a bundle is FAIL.
9. **No user-handoff without agent visual review.** Before reporting "done" to the user, agent (you) must `Read` every key frame in the proof bundle, verbalize observations in 1-2 sentences each, and confirm against PLAN.md milestones. Tool-based checks (`run` state snapshots, `read_audio`) certify *mechanics*; only the agent's own eyes certify *recognizability* and *playability*. "Did I look at the screenshot?" is a precondition for "is this done?". See `capture.md` "Pre-handoff agent review".
```

(Rule wording on #7 changes — references to specific judge_* tools removed. Rules count stays 9.)

**Edit 2.4** — "Quality gate is the contract" section. Update to:

```markdown
## Quality gate is the contract

Done is whatever `quality-gate.md`'s 11 stop conditions say is done. The agent cannot skip ahead, cannot self-certify, and cannot claim "done" with unaddressed FAILs. Re-enter whichever phase the FAIL points to, remediate, re-run the gate.

The Stop hook (`hooks/stop_check_bundle.py`) fires at session boundary as a non-blocking tripwire. It surfaces missing bundles to the user — it does not replace the agent running the gate.
```

(Drop the "unaddressed gate FAILs" wording for the hook — see Task 10 for hook simplification.)

- [ ] **Step 3: Verify**

Run: `/usr/bin/grep -c "judge_\|Layer 2" skill/SKILL.md` → expected `0`.

- [ ] **Step 4: Commit**

```bash
git add skill/SKILL.md
git commit -m "docs(v1.0.0): SKILL.md drops Layer 2 references, anti-shortcut #7 wording

The Required Runtime tool list shows 9 tools (Layer 1 only). Anti-shortcut
rule #7 no longer references specific judge_* tools — every verify is a
Python predicate the agent writes against an observed value. The gate
contract paragraph drops the 'unaddressed gate FAILs' hook detail (the
hook simplifies to bundle-existence tripwire only)."
```

---

## Task 5: Refactor skill/task-execution.md

**Files:**
- Modify: `skill/task-execution.md` (~187 lines → ~190 lines)

- [ ] **Step 1: Read current task-execution.md**

Run: `Read skill/task-execution.md`

- [ ] **Step 2: Apply targeted edits**

**Edit 5.1** — At the top of the file, after the "Outputs" section, add a "Visual Verification" section (echoing godogen's task-execution.md):

```markdown
## Visual Verification

- Do not trust code alone. Look at screenshots, captured frames, and `state` snapshots after every visible change.
- When code and media disagree, trust the media.
- Bias toward failure. If the required behavior is not clearly visible, treat it as unfinished.
- Hidden or inferred behavior does not count. The visible result has to prove the requirement.
```

**Edit 5.2** — In the "Per-task loop" section, step 6 currently says:

> 6. **One `run` call covers smoke + milestone verification (Pattern A).** Build a `snapshots` list with: ... Pass the task's input schedule via `inputs`. The single call returns `snapshots`, `assertions`, `exit_status`, and `log` — **read them all**.

Update to drop the "Pattern A" wording (which referenced wrapping in judge_milestone) and clarify direct Python evaluation:

> 6. **One `run` call covers smoke + milestone verification.** Build a `snapshots` list with: (a) `{"frame": K, "kind": "screen_image", "output": "tmp/smoke.png"}` at one early frame to catch black-screen / import failures, and (b) one multi-frame `{"frames": [...], "kind": "state", "attrs": [...]}` covering every frame the task's predicates reference. Pass the task's input schedule via `inputs`. The single call returns `snapshots`, `assertions`, `exit_status`, and `log` — **read them all**. The `log` field captures stdout/stderr from the script; scan it for warnings, missing-asset errors, unexpected `print` output, and any line containing `WARN`, `ERROR`, `Failed`, or `Traceback` even when `exit_status == "ok"`. A clean `exit_status` with a noisy `log` is a yellow flag worth investigating before declaring PASS. Predicates are Python expressions you write against the returned snapshots — there is no judge tool that wraps them.

**Edit 5.3** — Step 6.5 stays as-is; it already enforces Read PNG + verbalize, which is the visual primacy core.

**Edit 5.4** — Step 7 currently references "Pattern B" (script-side ASSERT) and Pattern A (judge_milestone). Update to drop Pattern A reference:

> 7. **Evaluate the task's Verify predicates against the returned snapshots and assertions.** Each Verify clause maps to either (a) a `state` snapshot value at a specific frame (Python `assert` from the agent), or (b) a named `ASSERT` line in `result["assertions"]` (Pattern B — script-side `print("ASSERT PASS: ...")`). For complex tasks, use both: state for the agent's predicate evaluation, ASSERT for the script's self-check. If the script-side ASSERT disagrees with the agent-side predicate evaluation, OR the visual observation from step 6.5 disagrees with either, that's a divergence — investigate before declaring PASS.

**Edit 5.5** — In the "Worked example" section, the example already uses agent-direct Python asserts (no judge_milestone). Verify it does, and add a note before the example:

> The example below is **agent-direct Python**. The agent reads `result["snapshots"]`, indexes by `(kind, frame)`, and asserts each predicate. There is no `judge_milestone` wrapping; the predicates are normal Python and can use `abs()`, `len()`, list comprehensions, anything Python supports.

(Add this paragraph just before the `# In your stage script (or directly via the MCP client):` block.)

**Edit 5.6** — In "Closed-loop input simulation" section, no judge_* references. Leave as-is (Pattern C is structural, not judge-related).

- [ ] **Step 3: Verify**

Run: `/usr/bin/grep -c "judge_\|Pattern A" skill/task-execution.md` → expected `0`.

- [ ] **Step 4: Commit**

```bash
git add skill/task-execution.md
git commit -m "docs(v1.0.0): task-execution.md embeds visual verification, drops Pattern A

Adds a Visual Verification section at the top mirroring godogen's
task-execution.md ('Bias toward failure, hidden behavior doesn't count').
Per-task step 6 drops the 'Pattern A judge_milestone wrapping' wording —
predicates are normal Python the agent writes against snapshot values.
The worked example was already agent-direct; adds a clarifying paragraph."
```

---

## Task 6: Refactor skill/decomposer.md

**Files:**
- Modify: `skill/decomposer.md` (~238 lines)

- [ ] **Step 1: Read current decomposer.md**

Run: `Read skill/decomposer.md`

- [ ] **Step 2: Apply targeted edits**

**Edit 6.1** — Genre Identity section, the example for "Donkey Kong-style platformer" L1 verify currently reads:

```
- **Verify:** at frame F (mid PLAY) hold `KEY_SPACE` for 5 frames
  with no `KEY_UP`. Player.y must NOT decrease by more than one
  floor height (`girder_pitch_y`) — a jump cannot bypass the next
  girder up. Run with two starts: under a girder, and at the edge.
```

Keep the verify text (it is already a description of agent behavior, not a sandbox predicate string), but add a clarifying note at the start of the Genre Identity section:

```markdown
**The Verify line is a description of the agent's Python code, not a string for tool consumption.** The quality gate's check #10 evaluates each rule by having the agent (you) write a Python script that issues `run` calls, reads `result["snapshots"]`, and asserts predicates directly. There is no AST sandbox — use any Python you need (`abs`, `min`, `max`, list comprehensions, helper functions).
```

(Insert this just after the "The `## Genre Identity` section captures the genre-defining rules that mechanic checks miss." paragraph.)

**Edit 6.2** — In L2 / L3 verify lines, no changes needed — they are already description-shaped.

**Edit 6.3** — In the section after Genre Identity, where the gate's check #16 was mentioned:

Old text:
> `quality-gate.md` check #16 evaluates each;

New text:
> `quality-gate.md` check #10 evaluates each (it iterates rules, runs each verify as Python);

**Edit 6.4** — In Win Path Milestones section, the closed-loop note currently references "the test harness reads observed values; if they don't match the planned trajectory within tolerance, the milestone FAILs." Keep as-is; this is general truth.

**Edit 6.5** — At the end of the Win Path Milestones section the note about "Frame numbers are guesses, not commitments" stays as-is — already handled by β2 fix (commit 0d10a45).

**Edit 6.6** — Verify any remaining judge_* references:

Run: `/usr/bin/grep -n "judge_" skill/decomposer.md`

If any matches: read context, rewrite as agent-direct Python descriptions.

- [ ] **Step 3: Verify**

Run: `/usr/bin/grep -c "judge_" skill/decomposer.md` → expected `0`.

- [ ] **Step 4: Commit**

```bash
git add skill/decomposer.md
git commit -m "docs(v1.0.0): decomposer.md genre-identity verify is agent Python, not sandbox string

Genre Identity rules' Verify lines are descriptions of agent-written
Python code, not strings for an AST sandbox. The clarifying paragraph
preempts the abs/len/min/max workaround friction that the prior
judge_genre sandbox required. Check number reference updated 16->10."
```

---

## Task 7: Refactor skill/capture.md

**Files:**
- Modify: `skill/capture.md` (~230 lines)

- [ ] **Step 1: Read current capture.md**

Run: `Read skill/capture.md`

- [ ] **Step 2: Apply targeted edits**

**Edit 7.1** — Audio rendering section: current text (post-β3) already explains `target={"sound": N}` vs music. Keep as-is. The judge_audio reference in the closing paragraph ("`judge_audio`'s default `min_notes: 1` therefore cannot be satisfied by a music-target render") needs updating:

Old text:
> `judge_audio`'s default `min_notes: 1` therefore cannot be satisfied by a music-target render. Treat the music-target render as a peak-amplitude-only sanity check; route the per-channel sound renders into `judge_audio` for the gate (#7).

New text:
> The audio gate (quality-gate.md check #7) requires `len(notes) >= 1` per cue, which only `target={"sound": N}` populates. Treat the music-target render as a peak-amplitude sanity check; render the per-channel sound IDs as sounds for the gateable evidence.

**Edit 7.2** — In the Concrete Invocations section, the comment "Use `target={"sound": N}` for anything that will go through judge_audio" — update to:

> Use `target={"sound": N}` for anything that will go through quality-gate check #7 — the music-target render does not populate `notes` (see "Audio rendering" section above for the full explanation).

**Edit 7.3** — Anti-patterns section currently references `compare_frames`. Update to `diff_frames`:

Old text references `diff_frames` already (post-Phase 3 rename). Verify with `/usr/bin/grep -n "compare_frames" skill/capture.md` → expected `0`.

**Edit 7.4** — Pre-handoff agent review section (lines 172-219 in current file) is the gate's primary mechanism. Strengthen its opening:

Old text:
> After `screenshots/result/<N>/` is produced, before calling the gate or reporting to the user, agent (you) must inspect the bundle visually. This is the harness's enforcement of SKILL.md Anti-shortcut rule #9 — tool-based checks certify *mechanics*; only the agent's own eyes certify *recognizability* and *playability*.

New text:
> After `screenshots/result/<N>/` is produced, before calling the gate or reporting to the user, agent (you) must inspect the bundle visually. This is **the gate's primary check** (quality-gate.md #11) — tool-based observations (`run` state snapshots, `read_audio` peak/notes, `diff_frames` dead-time) certify *mechanics*; only the agent's own multimodal eyes certify *recognizability* and *playability*. A bundle that passes #1-#10 with empty / boilerplate / contradictory verbalization fails #11 and the gate.

- [ ] **Step 3: Verify**

Run: `/usr/bin/grep -c "judge_" skill/capture.md` → expected `0`.

- [ ] **Step 4: Commit**

```bash
git add skill/capture.md
git commit -m "docs(v1.0.0): capture.md drops judge_audio refs, strengthens agent-review primacy

Audio rendering section refers to 'quality-gate check #7' instead of
'judge_audio' for the gate path. The Pre-handoff agent review section
is repositioned as 'the gate's primary check' (quality-gate.md #11),
making explicit that tool checks certify mechanics and verbalization
certifies recognizability + playability."
```

---

## Task 8: Refactor skill/asset-planner.md + skill/asset-gen.md

**Files:**
- Modify: `skill/asset-planner.md` (~167 lines)
- Modify: `skill/asset-gen.md` (~187 lines)

- [ ] **Step 1: Read both files**

Run: `Read skill/asset-planner.md` and `Read skill/asset-gen.md`

- [ ] **Step 2: asset-planner.md edits**

Find every `judge_sprite` / `judge_animation` / `judge_*` reference. Most likely locations:
- Stop-conditions / Verify rows
- "Sprite verification" subsection if present
- Closing summary

Replace each reference with agent-direct verification language. Pattern:

Old form (any variant of):
> Pass `judge_sprite` per ASSETS.md row.

New form:
> Verify each sprite: `read_image(script="main.py", image=N, x=..., y=..., w=..., h=...)` then `Read` the rendered PNG (use the `render_path` arg) and confirm it matches the ASSETS.md `represents:` description for that row. Reject sprites that read as single-color rectangles, blobs, or wrong subjects.

Same pattern for paired animations:
> Verify each paired-frame animation: `read_animation(script="main.py", image=N, ..., region_count=2)` to read both frames + diff stats, then `Read` each rendered PNG and confirm visual change between them matches the description (e.g. "wing flap up vs down").

**Edit 8.1** — Palette runtime merge guidance (added in cycle 4) stays — it is a procedure for the agent to follow before declaring asset planning done, not a judge_* reference. Verify wording:

Old form:
> ... then hand the merged observation to `judge_palette`.

New form:
> ... then evaluate the merged `used_indices` set: count distinct dark-layer indices (0,1,5), mid-layer (3,4,13), and bright-layer (8,10,11) — at least 2 layers should be present (hierarchy ≥ 2), and visual contrast between adjacent indices should not be so low that they read as the same swatch (the agent judges this by looking at the rendered PNG, not by a numerical threshold).

- [ ] **Step 3: asset-gen.md edits**

Same pattern. Find every judge_* reference and rewrite as agent-direct verification.

**Edit 8.2** — The per-sprite render_path + Read enforcement (added in 2026-05-03 round) stays — that is exactly the agent-direct pattern. Verify the wording does not still reference judge_sprite for the verdict.

If the file currently says "then pass to judge_sprite for the verdict", change to:

> Then **the agent (you) judges the verdict**: does the rendered PNG match the ASSETS.md `represents:` string? If yes, mark the row done. If no — wrong sprite, color-blob, illegible — fix the hex string and regenerate before moving on.

- [ ] **Step 4: Verify**

Run: `/usr/bin/grep -c "judge_" skill/asset-planner.md` → expected `0`.
Run: `/usr/bin/grep -c "judge_" skill/asset-gen.md` → expected `0`.

- [ ] **Step 5: Commit**

```bash
git add skill/asset-planner.md skill/asset-gen.md
git commit -m "docs(v1.0.0): asset-planner + asset-gen drop judge_* refs, agent direct verifies

Sprite identity verification was previously routed through judge_sprite
with min_distinct_colors / silhouette numerical defaults that fought
small-sprite (4x4) cases and material-pattern color budgets. Now the
agent uses read_image + Read of rendered PNG + match against ASSETS.md
represents: directly. Same shape for animations (read_animation + Read
each frame). Palette hierarchy / contrast become agent visual judgments
on the rendered PNG, not numerical thresholds."
```

---

## Task 9: Refactor skill/visual-target.md + skill/scaffold.md (minor)

**Files:**
- Modify: `skill/visual-target.md` (~174 lines)
- Modify: `skill/scaffold.md` (~220 lines)

- [ ] **Step 1: Search both files for judge_* references**

Run: `/usr/bin/grep -n "judge_\|Layer 2" skill/visual-target.md skill/scaffold.md`

If 0 matches, this task is a no-op pair (but skim each file once for any "17 tools" or other Layer 2-derived wording that should drop).

- [ ] **Step 2: Apply any edits found**

For each match, rewrite as agent-direct verification language (same pattern as Task 8).

- [ ] **Step 3: Quick wording sweep**

In each file, search for "17 checks" or "17 tools" — replace with current numbers if present.

Run: `/usr/bin/grep -n "17 checks\|17 tools" skill/visual-target.md skill/scaffold.md`

- [ ] **Step 4: Commit (only if edits made; skip if both files were no-op)**

```bash
git add skill/visual-target.md skill/scaffold.md
git commit -m "docs(v1.0.0): visual-target + scaffold sweep — drop stray Layer 2 wording"
```

---

## Task 10: Simplify Stop hook

**Files:**
- Modify: `skill/hooks/stop_check_bundle.py` (~89 lines → ~70 lines)
- Modify: `skill/hooks/test_stop_check_bundle.py` (adjust assertions)

- [ ] **Step 1: Read current hook implementation**

Run: `Read skill/hooks/stop_check_bundle.py` and `Read skill/hooks/test_stop_check_bundle.py`

- [ ] **Step 2: Simplify stop_check_bundle.py**

The current hook inspects `gate-report.json` for `summary.fail > 0`. Since the gate report schema changed (summary now reads `{"pass": 11, "fail": 0, "total": 11}`), the inspection still works numerically — but per the godogen-style design, the hook is a tripwire for missing bundles, not a re-check of gate state. Strip the gate-report.json inspection entirely; keep only the missing-bundle / missing-win-path.gif tripwires.

Replace the file content with:

```python
#!/usr/bin/env python3
"""pyxel-skill Stop hook: warn (don't block) on missing/incomplete proof bundle.

Best-effort. The hook never blocks Claude Code from stopping. It silently no-ops
when the cwd is not a pyxel-skill project (no .pyxel-skill/ marker).

The hook is a tripwire for missing artifacts only. The gate-report.json content
is the agent's responsibility; the hook does not re-evaluate it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def repo_root_from(cwd_str: str) -> Path:
    """Return the cwd as a Path. Caller already passes a usable directory."""
    return Path(cwd_str).resolve()


def is_pyxel_skill_project(root: Path) -> bool:
    return (root / ".pyxel-skill").is_dir()


def latest_bundle(root: Path) -> Path | None:
    results = root / "screenshots" / "result"
    if not results.is_dir():
        return None
    numbered: list[tuple[int, Path]] = []
    for child in results.iterdir():
        if not child.is_dir():
            continue
        try:
            numbered.append((int(child.name), child))
        except ValueError:
            continue
    if not numbered:
        return None
    numbered.sort(key=lambda pair: pair[0])
    return numbered[-1][1]


def warn(msg: str) -> None:
    print(f"[pyxel-skill] WARN: {msg}", file=sys.stderr)


def main() -> None:
    # Always print {} on stdout to be non-blocking. Even if input is malformed.
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        return

    cwd = event.get("cwd", ".")
    root = repo_root_from(cwd)

    if not is_pyxel_skill_project(root):
        # Not a pyxel-skill project; silent no-op.
        print(json.dumps({}))
        return

    bundle = latest_bundle(root)
    if bundle is None:
        warn("no proof bundle found at screenshots/result/<N>/. The quality gate may have been skipped.")
        print(json.dumps({}))
        return

    if not (bundle / "win-path.gif").is_file() and not (bundle / "win-path.mp4").is_file():
        warn(f"bundle {bundle.name} is incomplete: missing win-path.gif/mp4.")

    if not (bundle / "gate-report.json").is_file():
        warn(f"bundle {bundle.name} has no gate-report.json — quality gate did not run.")

    print(json.dumps({}))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Update test_stop_check_bundle.py**

Read the current test file, then update to match the simplified hook. Specifically: remove any test cases that verified the `summary.fail` parsing path. Add a new test case that verifies the missing-`gate-report.json` tripwire fires.

(Keep TDD discipline: read existing tests, identify which ones become obsolete, add the new one, run pytest, fix until green.)

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest skill/hooks/ -q 2>&1 | /usr/bin/tail -3`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add skill/hooks/stop_check_bundle.py skill/hooks/test_stop_check_bundle.py
git commit -m "refactor(v1.0.0): stop hook simplifies to bundle-existence tripwire only

The hook previously parsed gate-report.json for summary.fail count.
Per the godogen-style design, gate-report content is the agent's
responsibility (the agent ran the gate and wrote the JSON); the hook
is just a tripwire for missing artifacts. Now warns on:
- no bundle directory at screenshots/result/<N>/
- bundle missing win-path.gif/mp4
- bundle missing gate-report.json (= gate not run)

Tests adjusted to match the simplified contract."
```

---

## Task 11: Update CHANGELOG and run full test suite

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Read current CHANGELOG.md**

Run: `Read CHANGELOG.md`

- [ ] **Step 2: Add a major-refactor block to the `## 1.0.0 (unreleased)` section**

Append (do not overwrite existing entries — they document earlier 1.0.0 work):

```markdown
- Drop Layer 2 entirely: 8 judge_* tools and their numerical
  DEFAULT_CONTRACT thresholds removed (godogen-style visual primacy)
- Quality gate moves to agent-driven 11-step flat list: agent asserts
  win/lose-path predicates directly in Python, reads bundle frames with
  Read tool, verbalizes against ASSETS.md represents: anchors
- Genre Identity rules use agent-written Python predicates (no AST
  sandbox, no abs/len/min/max friction)
- Stop hook simplifies to bundle-existence tripwire only (no
  gate-report.json content inspection)
- 9 MCP tools (Layer 1 observe only): pyxel_info, validate, run,
  read_palette, read_image, read_animation, read_tilemap, read_audio,
  diff_frames
- Tests: ~350 (was 413; deleted 63 judge tests)
```

- [ ] **Step 3: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -q 2>&1 | /usr/bin/tail -5`
Expected: ~350 passed, 1 skipped (or whatever count remains after Task 1).

If any failures: read each carefully, fix, re-run.

- [ ] **Step 4: Smoke check the server starts**

Run: `.venv/bin/python -c "from pyxel_mcp.server import mcp, _log_startup; _log_startup()"`
Expected: a single line on stderr like `[pyxel-mcp] starting — 9 tools, workflow=...`

- [ ] **Step 5: Smoke check CLI**

Run: `.venv/bin/python -m pyxel_mcp.cli install` (should print snippet, not edit anything).
Run: `.venv/bin/python -m pyxel_mcp.cli publish-skill /tmp/test-publish --dry-run` (should print files that would be copied).

- [ ] **Step 6: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(v1.0.0): CHANGELOG block for godogen-style major refactor"
```

---

## Task 12: Validate via small-scale e2e (β2 redo)

**Files:**
- (no code changes; agent-dispatch task)

- [ ] **Step 1: Dispatch a fresh subagent in a temp working dir**

Pick a small-scope game (avoidance shooter, ~30s playthrough). Use the Agent tool with subagent_type=`general-purpose`. Give it the same brief used for the prior β2 / β3 (or a comparable small-scale scope). Working dir under `/tmp/`. Tell the agent:

- `pyxel-mcp` is locally installed (use `.mcp.json` override in the working dir if needed)
- Use the v1.0.0 skill at `/Users/takashi/repos/pyxel-mcp/skill/` (publish via `publish-skill` to the temp dir's `.claude/skills/` first)
- Run all 7 stages, end with quality-gate.md
- Goal: empty-override 11/11 PASS

- [ ] **Step 2: Review the agent's gate-report.json**

When the agent finishes (or is interrupted with a `not_run` summary), open the `gate-report.json` it produced. Look for:
- 11 checks, all `PASS`?
- `agent_review` populated with non-boilerplate verbalizations?
- Any `contract_overrides` field present? (Should be empty / absent — the gate has no contracts.)

- [ ] **Step 3: If any FAIL, route per the gate's `fail_route` and decide**

If the FAILs reveal a defect in the **new skill** (e.g. a wording issue that confused the agent, a missing piece of guidance), patch the skill md and dispatch β3 redo.

If the FAILs reveal a real game defect that the gate correctly caught — that's the gate working as intended, no action.

- [ ] **Step 4: Once β2 is empty-override 11/11 PASS, dispatch β-DK**

Same pattern, larger scope (Donkey-Kong-style platformer, multi-hazard, BARREL_PERIOD ≤ 30 production tune). Working dir `/tmp/pyxel-mcp-v1-dk-redo/`. Background agent (long run, possibly hours).

- [ ] **Step 5: β-DK result review**

Same as β2: open gate-report.json, verify 11/11 PASS empty-override, sanity-check `agent_review` honesty.

If PASS: v1.0.0 has demonstrated DK-scale empty-override completion under godogen-style gate. Ready for Phase 6 (release prep, user-approval-gated).

If FAIL: route per gate, patch, redispatch.

- [ ] **Step 6: Update memory if learnings emerge**

If e2e surfaces non-obvious lessons (hardness of agent direct asserts at scale, common failure modes, etc.), append to `MEMORY.md` of this repo or to user-memory feedback files as appropriate.

---

## Self-Review (run before handoff)

**1. Spec coverage** — every requirement from the user's "godogenに倣う" directive maps to a task:
- Drop 8 judge_* tools entirely → Task 1
- Quality gate becomes flat stop-conditions list (godogen style) → Task 3
- Visual primacy embedded in stages → Tasks 4 (SKILL.md), 5 (task-execution.md), 7 (capture.md)
- Predicates become agent-direct Python (no sandbox) → Task 5 (task-execution.md), 6 (decomposer.md)
- Sprite verification by agent Read of rendered PNG → Task 8 (asset-planner / asset-gen)
- Stop hook simplifies → Task 10
- v1.0.0 number stays, CHANGELOG documents the major shift → Task 11
- DK-scale empty-override validation → Task 12

**2. Placeholder scan** — searched my plan for "TBD", "TODO", "implement later", "appropriate error handling", "similar to Task N", "fill in details": all clean. Each step gives the actual code or markdown to write.

**3. Type consistency** — tool names referenced (`run`, `validate`, `read_palette`, `read_image`, `read_animation`, `read_tilemap`, `read_audio`, `diff_frames`, `pyxel_info`) match the existing server.py signatures. The new quality-gate.md Python examples use `run(...).snapshots` indexed by `(kind, frame)` — matches the existing snapshot schema. `read_audio` returns `peak_amplitude` and `notes` — matches the existing harness output. `diff_frames` returns `identical`, `size_match`, `diff_ratio` — matches.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-04-godogen-style-refactor.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — I execute tasks in this session using executing-plans, batch execution with checkpoints

Auto mode is active and the user prefers fast turnaround. **Inline Execution is the better fit here**: tasks 1, 2, 9, 10, 11 are mechanical (file deletes, targeted edits, commits); tasks 3, 4, 5, 6, 7, 8 contain the new content verbatim in the plan, so a subagent would just copy-paste; task 12 is a long-running agent dispatch that fits cleanly at the end.

I will proceed with inline execution unless you say otherwise.
