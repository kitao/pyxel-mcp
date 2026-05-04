# Stage 7: Quality Gate

Final acceptance check. PASS gates "done"; FAIL routes back to the phase that owns the failed check. The gate is **agent-driven visual primacy** — the agent (you) reads bundle frames with the `Read` tool, verbalizes observations against PLAN.md / ASSETS.md anchors, and asserts state predicates directly in Python. There are no numerical default thresholds — "good" is judged by what the captured frames actually show.

This file contains no `judge_*` calls. The harness's contract is the agent's discipline: run the 11 numbered stop conditions (14 rows after #4 splits into 4a/4b/4c/4d) in order, write `gate-report.json`, route every FAIL to its owning phase, and re-run from the top.

## Inputs

- `PLAN.md` (Stage 2) — Win Path / Lose Path Milestones, **`## Genre Identity`** rules, optional `## Difficulty floor override`.
- `STRUCTURE.md` (Stage 3) — `FPS` constant.
- `ASSETS.md` (Stage 4) — sprite manifest (especially `represents:` strings) + audio manifest.
- `MEMORY.md` — gotchas accumulated across phases.
- `screenshots/result/<N>/` — proof bundle from `capture.md` (win-path GIF, lose-path GIF, frames/, audio/).
- `pyxel://run-snapshots-schema` (MCP resource) — snapshot field shapes.

## Output

`screenshots/result/<N>/gate-report.json` — flat list of 11 numbered stop conditions (14 rows after #4 splits into 4a/4b/4c/4d), each PASS or FAIL with evidence. The gate writes this file regardless of overall PASS/FAIL — the artifact is what the user reviews. `<N>` is the bundle counter `task-execution` and `capture.md` produced — the gate writes its report inside the existing bundle directory rather than creating a new one.

## Order of execution

Run the 11 numbered stop conditions (14 rows after #4 splits into 4a/4b/4c/4d) in numeric order. Cheap structural checks first; expensive playthrough-driven checks last; agent visual review is the closing gate.

If a check FAILs, stop and write the gate report with the FAIL even if later checks would have passed. Partial reports are valid input for routing — there is no benefit in running #4 (Win path) when #1 (State files) has already failed.

## Stop conditions (all must PASS — counted as 14 rows after #4 splits into 4a/4b/4c/4d)

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

### 4. Win path (multi-attempt with variability)

The win path passes only if the agent can clear under **variability** — not via one specific seed + frame-perfect inputs. A single Pattern-C-found clearance is "answer-key making" with rewind, not gameplay; without variability the gate proves *clearability* but not *playability*. Three sub-checks; **all** must pass.

#### #4a — Multi-seed clearance

Run the same input schedule under at least 3 different `random_seed` values. Every run must reach `scene == "WIN"` and hit every PLAN.md milestone.

```python
SEEDS = [42, 99, 1]   # 3 minimum; 5 if the game has heavy RNG
inputs = <PLAN.md Win Path inputs>
final = <last milestone frame>

for seed in SEEDS:
    result = run(script="main.py", frames=final + 1, random_seed=seed,
                 inputs=inputs,
                 snapshots=[{"frames": [<every milestone frame>],
                             "kind": "state",
                             "attrs": [<every attr referenced>]}])
    assert result["seeded"] is True
    snaps = {(s["kind"], s["frame"]): s for s in result["snapshots"]}
    v = lambda f, a: snaps[("state", f)]["values"][a]

    # Every PLAN.md Win Path milestone assertion under THIS seed:
    assert v(60, "scene") == "PLAY", f"seed={seed} frame 60: {v(60,'scene')!r}"
    assert v(660, "scene") == "WIN", f"seed={seed}: did not reach WIN"
```

If only seed=42 clears and seed=99 doesn't, the win path is exploiting one specific RNG sequence — design failure. Either make spawns deterministic by frame (integer-modular per `task-execution.md` "Spawn determinism"), or design hazards so any plausible RNG yields a clearable pattern.

FAIL routes to: `playthrough` (game requires specific RNG to clear) or `spec` (milestone tied to RNG).

#### #4b — Timing jitter tolerance

Take a winning input schedule from #4a. Apply random ±3 frame jitter to each input's `frame` field. Replay 5 trials with different jitter draws. At least 4 of 5 must clear. Catches games requiring frame-perfect timing — humans react in ~6 frames at 30fps and cannot replicate frame-precise input.

```python
import random
JITTER = 3       # ± frames per input
N_TRIALS = 5
THRESHOLD = 4    # must clear in 4/5

cleared = 0
for trial in range(N_TRIALS):
    rng = random.Random(trial)
    jittered = [
        {**inp, "frame": max(0, inp["frame"] + rng.randint(-JITTER, JITTER))}
        for inp in inputs
    ]
    result = run(script="main.py", frames=final + 5, random_seed=42,
                 inputs=jittered,
                 snapshots=[{"frames": [final], "kind": "state", "attrs": ["scene"]}])
    snaps = {(s["kind"], s["frame"]): s for s in result["snapshots"]}
    if snaps[("state", final)]["values"]["scene"] == "WIN":
        cleared += 1
assert cleared >= THRESHOLD, f"jitter tolerance: only {cleared}/{N_TRIALS} clears"
```

If 0/5 clear under ±3 frame jitter, the game requires frame-perfect timing — not playable by humans. Widen hazard windows, slow projectile speeds, add invuln frames after jumps, or extend pickup windows. See `knowledge/game-feel.md` "Variability Budget" for design constants.

FAIL routes to: `playthrough` (game requires frame-perfect timing) or `spec` (milestones too tight).

#### #4d — Hazard spatial distribution

The win-path's hazard spawns must cover the playfield, not cluster on one side. Single-side bias = the player only needs to dodge in one direction = memorization, not reactive gameplay.

```python
result = run(script="main.py", frames=final + 1, random_seed=42,
             inputs=inputs,
             snapshots=[{"frames": list(range(0, final, 30)),
                         "kind": "state",
                         "attrs": ["barrels"]}])  # or whatever hazard collection
# Collect hazard x positions across all snapshots:
xs = [b["x"] for s in result["snapshots"] for b in s["values"].get("barrels", [])]
assert xs, "no hazards observed in win-path window"

usable_lo, usable_hi = 16, 208   # exclude HUD / wall margins (224-wide screen)
usable_w = usable_hi - usable_lo

coverage = (max(xs) - min(xs)) / usable_w
assert coverage >= 0.70, f"hazard span only {coverage:.0%} of usable width"

# Variance check — single-side cluster fails even with one outlier covering width
import statistics
center = (usable_lo + usable_hi) / 2
stddev = statistics.pstdev(xs) if len(xs) > 1 else 0
assert stddev >= 0.18 * usable_w, \
    f"hazard stddev {stddev:.1f} < 18% of usable width — clustered"
```

PASS condition: hazard x positions span ≥70% of usable playfield width AND stddev ≥18% of usable width. Both must hold — width alone passes with 1 outlier; variance alone passes with 2 stuck-at-extremes points.

If FAIL: hazards are biased to one column / one path. See `knowledge/game-feel.md` "Hazard Distribution" for design fixes (multi-spawn point, randomize spawn x with deterministic-by-frame variation, telegraphed alternating pattern).

FAIL routes to: `playthrough` (game-balance failure — memorization shortcut design).

#### #4c — Strategy diversity

Find at least 2 **distinct** winning strategies and verify each clears under one seed. "Distinct" means materially different approach: different climb path, different pickup-use sequence, different jump-timing pattern. PLAN.md must contain a `## Win Path Strategies` section listing each strategy's input schedule and rationale.

```markdown
## Win Path Strategies

### Strategy A — hammer chain
Pick up hammer on each girder, traverse during invuln, climb when next
hammer is ~2s away.

### Strategy B — dodge-only
Skip hammers, jump-dodge each barrel at the apex. Slower, but possible
because BARREL_SPEED leaves a 20-frame jump window.
```

```python
for name, inputs_for_strategy in strategies.items():
    result = run(script="main.py", frames=final + 1, random_seed=42,
                 inputs=inputs_for_strategy,
                 snapshots=[{"frames": [final], "kind": "state", "attrs": ["scene"]}])
    snaps = {(s["kind"], s["frame"]): s for s in result["snapshots"]}
    assert snaps[("state", final)]["values"]["scene"] == "WIN", \
        f"strategy {name!r}: did not reach WIN"
```

If only Strategy A clears and Strategy B (a sane alternate path) doesn't, the game is single-thread — memorization, not gameplay. Tune so multiple strategies work.

FAIL routes to: `playthrough` (insufficient solution space) or `spec` (PLAN.md `## Win Path Strategies` section missing or contains < 2 strategies).

### 5. Lose path (multi-seed)

The lose path uses PLAN.md Lose Path inputs (typically passive, e.g., "stand still"). Multi-seed only — jitter and strategy-diversity are not meaningful for a passive failure path.

```python
SEEDS = [42, 99, 1]
lose_inputs = <PLAN.md Lose Path inputs>
lose_final = <lose-path final frame>

for seed in SEEDS:
    result = run(script="main.py", frames=lose_final + 1, random_seed=seed,
                 inputs=lose_inputs,
                 snapshots=[{"frames": [lose_final], "kind": "state", "attrs": ["scene"]}])
    assert result["seeded"] is True
    snaps = {(s["kind"], s["frame"]): s for s in result["snapshots"]}
    assert snaps[("state", lose_final)]["values"]["scene"] == "GAME_OVER", \
        f"seed={seed}: lose path did not reach GAME_OVER"
```

If only one seed reaches GAME_OVER, the hazard spawn is RNG-dependent and the lose path isn't reliable.

FAIL routes to: `playthrough` (hazards too soft / spawn unreliable) or `spec` (lose-path milestones misaligned).

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

### 8. Proof bundle

PASS condition: `screenshots/result/<N>/` contains the bundle layout from `capture.md`:
- `win-path.gif` (or `.mp4`)
- `lose-path.gif` (or `.mp4`)
- `frames/` with at least 5 PNGs (`title.png`, `play_start.png`, `mid_game.png`, `win.png`, `game_over.png`)
- `audio/*.wav` per ASSETS.md audio manifest
- `notes.md`

PASS condition (no frame-size mismatch): all `frames/*.png` were captured at the same `scale` so they can be compared. Use `diff_frames` on adjacent files and assert `size_match: True`.

```python
import os
bundle = Path(f"screenshots/result/{N}")
required = ["win-path.gif", "lose-path.gif", "notes.md", "frames", "audio"]
for r in required:
    assert (bundle / r).exists(), f"missing {r}"

png_files = sorted((bundle / "frames").glob("*.png"))
assert len(png_files) >= 5, f"only {len(png_files)} frame PNGs"

# Size mismatch is a capture defect (capture.md mandates uniform scale).
for i in range(len(png_files) - 1):
    r = diff_frames(frame_a=str(png_files[i]), frame_b=str(png_files[i + 1]))
    assert r.get("size_match", True), f"size mismatch: {png_files[i].name} vs {png_files[i+1].name}"
```

**Dead-time / static-bundle detection moved to check #11**, where the agent's per-frame verbalizations against PLAN.md milestones inherently catch "frames look identical" — a stalled entity or frozen camera produces verbalizations that contradict the milestone's expected motion. Numerical diff thresholds are genre-dependent (sparse-canvas avoidance shooters legitimately hit 5% even with full action; dense platformers easily hit 20%) — encoding "static = FAIL" as agent visual judgment instead of a universal threshold avoids the recurring tuning trap.

FAIL routes to: `bundle` (missing artifacts).

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

**Pre-condition: ASSETS.md must contain the multi-draft history from `asset-gen.md` Rule A.** For each character sprite (`represents:` names a subject with anatomy: head/body/limbs/face), ASSETS.md must list ≥3 hex-string drafts, each draft's literal verbalization (per Rule B Step B1, pixel-position concrete), the recognition check outcome (Rule B Step B2), and the selection reasoning. If ASSETS.md ships single-draft character sprites, that's a Rule A violation — gate FAILs at #11 because the iteration loop wasn't actually run.

After all bundle artifacts exist (#8 PASS) and ASSETS.md draft history is complete:

1. List bundle frame PNGs:
   - `screenshots/result/<N>/frames/title.png`
   - `screenshots/result/<N>/frames/play_start.png`
   - `screenshots/result/<N>/frames/mid_game.png`
   - `screenshots/result/<N>/frames/win.png`
   - `screenshots/result/<N>/frames/game_over.png`

2. For each PNG, **use the `Read` tool to open it** following the `asset-gen.md` Rule B blind read protocol where applicable: Step B1 literal pixel-position description first, then Step B2 recognition check against ASSETS.md `represents:` strings and PLAN.md milestone description. Vague labels ("Mario-like", "looks like a barrel") are themselves a FAIL — see Rule C anti-patterns.

3. Verbalize observation in 2-3 sentences per frame using **pixel-position-concrete language** (Rule C), covering all of:
   - **Sprite identity (concrete)** — for each visible character: pixel-position description AND recognition outcome ("Mario at row 200, col 30: 4-pixel red region top, brown 8×6 center, blue lower with two leg columns; recognizable as red-cap plumber per ASSETS.md player_walk_1 represents:"). NOT: "Mario in the bottom-left".
   - **Scene state** — TITLE / PLAY / WIN / GAME_OVER as the PLAN.md milestone for this frame implies?
   - **HUD content** — score / lives / level / "PRESS SPACE" prompts — visible, legible, no overflow, no overlap with gameplay sprites?
   - **Animation state** — mid-stride / climbing / jumping / falling / dead as the milestone implies?
   - **Background and hazards** — playfield populated (girders, ladders, pickups, hazards) or mostly empty? Are barrels / enemies in plausible positions?

4. Compare each verbalization against the corresponding PLAN.md milestone description. Note divergences explicitly: "milestone says barrel near floor at frame 200, observation: barrel still on girder 1".

5. **Dead-time / static-bundle catch.** Read the verbalizations across `play_start`, `mid_game`, and other gameplay frames. If two gameplay frames produce essentially the same verbalization (same sprite at same position, same hazard placement, same HUD), the bundle is static — entity / camera frozen, broken state, or capture replayed the same frame. This is a FAIL even if every individual frame looks correct in isolation. Anti-shortcut #4 ("a bundle whose first 3 seconds are correct and the rest is static is FAIL, not partial pass") is enforced here, not in #8.

6. **If any frame shows a defect** — missing sprite, wrong scene, static animation, placeholder rectangle, illegible HUD, recognizability failure, or two gameplay frames verbalize identically — return to the owning stage:
   - `asset-gen.md` for sprite identity
   - `scaffold.md` for scene routing / HUD layout
   - `decomposer.md` for milestone alignment
   - `task-execution.md` for animation / hazard implementation

   Do NOT proceed to mark the gate PASS.

7. The verbalizations populate `gate-report.json["agent_review"]`. Empty / boilerplate ("scene shown", "looks fine") / contradictory verbalizations are **themselves a FAIL** — the gate is built to catch this exact shortcut.

FAIL routes to: `playthrough` / `sprite-quality` / `scaffolding`.

## Visual primacy mantras (read before writing the gate report)

These mantras echo across `SKILL.md`, `task-execution.md`, `capture.md`, and `decomposer.md`. They are the gate's contract.

- **Do not trust code alone.** When code says X but the captured frame shows Y, trust the frame.
- **Bias toward failure.** If the required behavior is not clearly visible in the capture, treat it as not done.
- **No partial pass.** A bundle whose first 3 seconds look right and then sits static is FAIL, not partial pass.
- **No verbalization, no PASS.** A 13/14 PASS with empty / boilerplate `agent_review` is itself a FAIL.

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
    {"id": "4a", "label": "Win path multi-seed", "result": "PASS",
     "evidence": "seeds [42, 99, 1] all reached WIN; all milestones held"},
    {"id": "4b", "label": "Win path jitter tolerance", "result": "PASS",
     "evidence": "±3 frame jitter, 5 trials, 4 cleared (threshold 4)"},
    {"id": "4c", "label": "Win path strategy diversity", "result": "PASS",
     "evidence": "2 strategies (hammer-chain, dodge-only) both reached WIN"},
    {"id": "4d", "label": "Hazard spatial distribution", "result": "PASS",
     "evidence": "barrel x positions: span 78% of usable width, stddev 23%"},
    {"id": 5, "label": "Lose path multi-seed", "result": "PASS",
     "evidence": "seeds [42, 99, 1] all reached GAME_OVER"},
    {"id": 6, "label": "Difficulty floor", "result": "PASS",
     "evidence": "GAME_OVER at frame 372 (12.4s @ 30fps, in 10-14s band)"},
    {"id": 7, "label": "Audio", "result": "PASS",
     "evidence": "5 WAVs rendered, all peak >= 0.02, all sounds have notes"},
    {"id": 8, "label": "Proof bundle", "result": "PASS",
     "evidence": "5 frame PNGs + 8 audio WAVs + 2 GIFs + notes.md, all sizes match"},
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
  "summary": {"pass": 14, "fail": 0, "total": 14}
}
```

`#4` is reported as four rows (`4a` multi-seed, `4b` jitter, `4c` strategy, `4d` distribution) counted as four toward `total`. `#5` is one row (multi-seed). The other checks (1-3, 6-11) are one row each. So a clean run reports 14 PASS / 14 total.

The `fail_route` field is required on every FAIL row. PASS rows may omit `evidence` when the check is binary; FAIL rows must include enough evidence to act on.

## Anti-shortcut rules (restated for the agent at gate time)

These are the cheats the gate is built to catch. Read them before writing `gate-report.json`.

1. **"It compiles and runs, looks fine."** Checks #2 / #3 only certify no-crash. Check #4 (multi-seed, jitter-tolerant, multi-strategy clearance) is what proves the game is *playable* — not just *clearable* by one perfectly-timed input sequence.
2. **"I added a sprite."** Without check #11 (agent reads the PNG and matches against ASSETS.md `represents:`), the sprite is unverified.
3. **"Bundle exists."** Bundle artifact presence (#8) only certifies all the files are there. Dead-time / static-bundle is caught by #11's per-frame agent verbalization comparison — if two gameplay frames verbalize identically, the bundle is static.
4. **"Audio plays."** Without check #7's peak ≥ 0.02 + notes ≥ 1 per slot, the slot may be silent or empty. A `play()` call alone passes #2 and #3 but fails #7.
5. **Adjusting milestones / variability params to fit.** *Most important.* If the game can't reach WIN by the planned frame, fix the game, not the milestone. Loosening the spec to dodge a FAIL is the failure mode this gate exists to prevent. The `## Difficulty floor override` (and any other override declared in PLAN.md) **locks before the run begins**, not after a failing run. Same applies to #4b's `JITTER` / `THRESHOLD` and #4c's strategy count: these are gate-defined constants (±3 frame, 4/5 threshold, ≥2 strategies); reducing them to dodge a FAIL is the same shortcut.
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

- **#4a reaches PLAY but never WIN under some seed.** RNG-dependent clearance — design failure or spawn not seed-deterministic → `playthrough`.
- **#4b 0/5 clears under jitter.** Frame-perfect timing required — humans cannot play this. Widen hazard windows, slow projectile speeds → `playthrough`.
- **#4c only one strategy clears.** Single-thread memorization puzzle, not a game. Tune until 2+ strategies viable → `playthrough`.
- **#4d hazard span < 70% or stddev < 18%.** Hazards cluster on one side — player only needs to dodge in one direction = memorization shortcut. Add multi-spawn point or randomize spawn x deterministic-by-frame → `playthrough`.
- **#5 some seeds reach GAME_OVER, others don't.** Hazard spawn RNG-dependent → `playthrough`.
- **#6 GAME_OVER frame outside FPS band.** Hazards too aggressive (frame < lo) or too gentle (frame > hi) → `playthrough`.
- **#7 audio peak == 0.0 with `slot empty` warning.** Sound slot was never assigned → `sprite-quality`.
- **#11 two gameplay frames verbalize identically.** Frozen entity / frozen camera / capture replayed the same frame → `playthrough`.
- **#9 `trap_warning: True`.** Source-bank `(0,0)` has visible pixels and tilemap uses `(0,0)` → `sprite-quality` (clear source) or `scaffolding` (remap empty cells).
- **#11 verbalization contradicts ASSETS.md `represents:`.** Sprite drawn doesn't match the design — wrong sprite swapped in, or the sprite was implemented as a placeholder rectangle → `sprite-quality` or `asset-gen`.

## When this gate PASSes

All 14 rows (11 numbered checks; #4 expands to 4a/4b/4c/4d) PASS in `gate-report.json`. Then:

- `PLAN.md` shows all milestone rows marked `done` with one-line `verified by:` notes.
- `MEMORY.md` records any non-obvious gotchas worth keeping for next session.
- The latest `screenshots/result/<N>/` bundle is the deliverable, and `screenshots/result/<N>/gate-report.json` proves the bundle was accepted.

Report to the user (concise; the bundle and `gate-report.json` carry the detail):

- **Bundle path** — `screenshots/result/<N>/`. The user opens the GIFs and WAVs from there.
- **One-line summary** — game title, win condition, lose condition.
- **Any caveats** — known limitations, out-of-scope items deferred, anything the gate did not check.

Then stop. Done. Do not start the next iteration speculatively; if the user wants polish or a new feature, they will say so.
