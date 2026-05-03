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
