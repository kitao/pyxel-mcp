# Stage 6: Task Execution

Implement gameplay logic against `PLAN.md` and `STRUCTURE.md`. Verify after every change. Move on only when the task's Verify predicates are met by observed state, not by inspection of the code.

## Inputs

- `PLAN.md` (from Stage 2) — Risk Tasks, Main Build tasks, Win/Lose milestones, Audio manifest.
- `STRUCTURE.md` (from Stage 3) — modules, scene state machine, tuning constants.
- `ASSETS.md` (from Stage 4 + 5) — sprite manifest with bank coordinates.
- `MEMORY.md` — gotchas accumulated so far.
- `main.py` — runnable skeleton with `_build_assets()` populated.

## Outputs

- `main.py` with all PLAN.md tasks implemented and verified.
- `PLAN.md` tasks marked done with one-line `verified by:` notes.
- `MEMORY.md` updated with any non-obvious gotcha discovered while implementing.

## Visual Verification

- Do not trust code alone. Look at screenshots, captured frames, and `state` snapshots after every visible change.
- When code and media disagree, trust the media.
- Bias toward failure. If the required behavior is not clearly visible, treat it as unfinished.
- Hidden or inferred behavior does not count. The visible result has to prove the requirement.

## References

Read these before invoking the corresponding tools:

- `test-harness.md` — milestone playthrough via a single `run` call with scheduled `inputs` + per-milestone `state` snapshots. Read before win/lose-path runs.
- `capture.md` — intermediate captures and the final proof bundle. Read before producing any frames or GIFs that the gate will read.
- `quirks.md` — Pyxel gotchas (coords, `btnp` semantics, `colkey`, MML volume scaling). Read whenever Pyxel behaves unexpectedly.
- `knowledge/game-feel.md` — physics tuning (gravity, jump arcs), hitboxes vs sprite bounds, camera follow, screen shake, hitstop. Read before implementing player physics or hit feedback.
- `knowledge/audio.md` — SE-per-event policy, channel allocation (BGM ch0–2, SE ch3), MML volume mapping. Read before adding any sound trigger.
- `knowledge/patterns.md` — level/enemy archetypes, animation-frame timing (`frame_count // 4 % 2`). Read before implementing scrolling, spawn waves, or AI patterns.
- `pyxel://run-snapshots-schema` (MCP resource) — full schema for the 5 snapshot kinds (screen_image, screen_grid, state, layout, video) and multi-frame syntax. Read before constructing complex snapshot lists.

## Per-task loop

For each task in `PLAN.md`:

1. **Read the task definition.** Confirm Verify criteria are observable (specific predicates against state values or scene transitions, not "looks fine"). If the Verify is vague — re-read `decomposer.md` and tighten PLAN.md before coding.
2. **Read `STRUCTURE.md`.** Identify which class / function gains the change. If no module owns this behavior, you skipped Stage 3 — go back.
3. **Read the current source.** Don't guess what's there.
4. **Implement the smallest change that makes the task observable.** One method, one constant, one behavior. No bundled "while I'm in there" edits.
5. **`validate` clean.** Catches syntax errors and Pyxel anti-patterns before runtime.
6. **One `run` call covers smoke + milestone verification.** Build a `snapshots` list with: (a) `{"frame": K, "kind": "screen_image", "output": "tmp/smoke.png"}` at one early frame to catch black-screen / import failures, and (b) one multi-frame `{"frames": [...], "kind": "state", "attrs": [...]}` covering every frame the task's predicates reference. Pass the task's input schedule via `inputs`. The single call returns `snapshots`, `assertions`, `exit_status`, and `log` — **read them all**. The `log` field captures stdout/stderr from the script; scan it for warnings, missing-asset errors, unexpected `print` output, and any line containing `WARN`, `ERROR`, `Failed`, or `Traceback` even when `exit_status == "ok"`. A clean `exit_status` with a noisy `log` is a yellow flag worth investigating before declaring PASS. Predicates are Python expressions you write against the returned snapshot values — there is no judge tool that wraps them.

6.5. **Read the captured PNG with `Read` tool (visual primacy enforcement).** For each frame where you took a `screen_image` snapshot, open the PNG with the `Read` tool and verbalize what you see in 1–2 sentences (e.g., `"at frame 60: Mario is on girder 4, barrel mid-air at x≈140, score=300 in HUD"`). Compare against the task's expected visual outcome. If the verbalized observation contradicts the predicate, **trust the observation** — the predicate may pass on `state.player.y` while the rendered frame shows the player drawn behind the HUD, swapped to the wrong sprite, or invisible due to `colkey` collision. Skipping this step is the failure mode the harness exists to catch: tool-based gate PASS while the agent never looked at a single frame. See SKILL.md Anti-shortcut rule #9.

7. **Evaluate the task's Verify predicates against the returned snapshots and assertions.** Each Verify clause maps to either (a) a `state` snapshot value at a specific frame (Python `assert` from the agent), or (b) a named `ASSERT` line in `result["assertions"]` (Pattern B — script-side `print("ASSERT PASS: ...")`). For complex tasks, use both: state for the agent's predicate evaluation, ASSERT for the script's self-check. If the script-side ASSERT disagrees with the agent-side predicate evaluation, OR the visual observation from step 6.5 disagrees with either, that's a divergence — investigate before declaring PASS.
8. **If FAIL** — read the captured state, find the divergence, fix. Don't move on. Don't lower the threshold. Don't retry the same input expecting a different result.
9. **If PASS** — update `PLAN.md` (mark task done with a one-line `verified by:` note pointing to the milestone frame and observed value), append to `MEMORY.md` if a non-obvious gotcha was discovered, commit.

## Worked example: one task end-to-end

PLAN.md task: *"Player jumps reach height H_JUMP=24px in 18 frames; falling resumes after frame 18; landing on platform clears `vy`."*

Verify: a single `run` call drives the script through 60 frames with `KEY_SPACE` pressed at frame 30, capturing `state` at frames 30, 31, 48, 60.

The example below is **agent-direct Python**. The agent reads `result["snapshots"]`, indexes by `(kind, frame)`, and asserts each predicate. There is no `judge_*` wrapping; the predicates are normal Python and can use `abs()`, `len()`, list comprehensions, anything Python supports.

```python
# In your stage script (or directly via the MCP client):
run(
    script="main.py",
    frames=60,
    inputs=[
        {"frame": 30, "buttons": ["KEY_SPACE"]},
        {"frame": 32, "buttons": []},
    ],
    snapshots=[
        {"frame": 5, "kind": "screen_image", "output": "tmp/smoke-f5.png"},
        {"frames": [30, 31, 48, 60], "kind": "state",
         "attrs": ["player.y", "player.vy", "player.on_ground"]},
    ],
)
```

The `state` block expands to 4 entries with frames 30, 31, 48, 60. Index snapshots by `(kind, frame)` for direct lookup:

```python
snaps = {(s["kind"], s["frame"]): s for s in result["snapshots"]}
y30 = snaps[("state", 30)]["values"]["player.y"]
y31 = snaps[("state", 31)]["values"]["player.y"]
y48 = snaps[("state", 48)]["values"]["player.y"]
y60 = snaps[("state", 60)]["values"]["player.y"]

assert y31 - y30 < 0           # jumping
assert abs(y48 - y31 - (-24)) < 2   # peak around -24px
assert y60 >= y31              # landed
```

(Optional augmentation per Pattern B: have the script `print("ASSERT PASS: jump_lands")` once `on_ground` becomes True after frame 31. The agent then sees both the predicate result AND the script's self-confirmation in `result["assertions"]`.)

Read the state output. If `player.y[48] - player.y[31] == -10` instead of ~-24, the jump curve is wrong — fix `JUMP_VY` or gravity, not the milestone frame. If `player.on_ground[60] == False`, the landing detection is broken — fix the collision check, not the predicate. Step 9 only runs once all three predicates hold.

## Phases

**Risk Slice.** Implement each PLAN.md risk task in isolation. Keep code small and contained — a risk task that needs three classes and a state machine is a sign the risk wasn't really isolated. Once the risk task passes its Verify, carry only the validated pattern (the single function, the single constant, the single approach) into Main Build. Don't carry forward speculative scaffolding.

**Main Build.** Everything else from PLAN.md. Lock scene ownership first (which class owns TITLE rendering, which owns PLAY update, etc., per STRUCTURE.md), then implement vertical slices: pick one feature, run it through draw + update + verify, before starting the next.

## Visual primacy

When the code says X happened but the capture shows Y, the capture is right. Don't argue with the pixels. Three concrete divergence cases:

- "I drew the player at (40, 100)" but the screenshot shows nothing at (40, 100). Probable causes: `colkey` makes the sprite invisible against background; the sprite is drawn but at a different layer ordering and is overdrawn; `pyxel.cls()` is called *after* the player's draw and erases it. Use a `run` call snapshotting `screen_grid` at that frame and look at the palette indices around (40, 100); the truth is in the grid.
- "I incremented score on barrel-jump" but a `state` snapshot inside `run` at frame 150 shows `score == 0`. The collision check never fires; either the hitbox rectangle is wrong (bounds inverted, off-by-one) or the trigger condition has a strict-equality bug (`y == barrel.y` instead of `abs(y - barrel.y) < EPS`).
- "Mario climbs the ladder" but `run` with `KEY_UP` inputs shows Mario stuck. The climb-eligibility check has a strict bound (`x == ladder.x` instead of `ladder.x <= x <= ladder.x + ladder.w`), or `on_ladder` is set in `update()` *after* the input read.

In each case the fix is to look at observed state, not to re-explain the code. `screen_grid` and `state` snapshots inside `run` are the witnesses; the code is the suspect.

## When to consult each knowledge file

The references at the top of this stage are not all loaded for every task. Choose by what the current task touches:

- Implementing player movement, jump arcs, gravity, hit feedback, screen shake, hitstop, camera follow → read `knowledge/game-feel.md` *before* writing the constants. Tuning numbers in PLAN.md must agree with the heuristics there.
- Adding any sound trigger (jump, hit, death, score, scene transition) → read `knowledge/audio.md` for SE-per-event policy and channel allocation. SE volume below 5/7 will be inaudible over BGM.
- Implementing scrolling, parallax, enemy spawn waves, animation cycles, AI patterns → read `knowledge/patterns.md`. Animation timing follows `frame_count // 4 % 2`, not `frame_count % 2` — the latter flickers.
- Pyxel doing something unexpected at runtime → check `quirks.md` first. If the issue is not there, it's a project-specific bug → fix it and append to `MEMORY.md`.

## Anti-shortcut rules

- **No "looks fine".** Each Verify is a specific predicate against an observed value. If you cannot name the predicate, it is not a Verify — go fix PLAN.md.
- **Don't skip lose-path verification.** Win path is exciting; lose path is forgotten. Both must verify with `run` with `inputs` and reach their target scene by the milestone frame.
- **Don't comment out failing assertions.** Fix the code.
- **Don't lower the threshold to make it pass.** If `lives reaches 0` doesn't happen by frame 360 in lose path, either barrels are too slow (PLAN.md is wrong → re-decompose) or collision is broken (code is wrong → fix). Don't move the milestone to frame 600.
- **Don't trust subprocess returncode alone.** A script can run cleanly and produce a black screen, no audio, frozen state. Always observe captured state — that's what `state` snapshots inside `run` are for.
- **Don't replace ASSERT lines with comments.** If the script writes `print("ASSERT PASS: ...")` to confirm a milestone, removing the print to "clean up" silently breaks Pattern B verification. Either keep the ASSERT or migrate to an explicit `state` snapshot agent-side.

## Closed-loop input simulation

Open-loop input (timed press / release) drifts. Over 200+ frames the player position desyncs from the planned trajectory because of floating-point physics, frame-skip, and stochastic spawn timing. For long sequences, use Pattern C — canonical for pyxel-mcp's subprocess isolation model:

1. `result = run(script=..., frames=200, inputs=schedule_so_far, snapshots=[{"frames": [199], "kind": "state", "attrs": [...]}])`
2. Read observed state from `result["snapshots"]`.
3. Compute the next input segment from the observed state.
4. Issue a **new** `run` call with the **cumulative** input schedule from frame 0 to the next milestone.

Do NOT try to resume `run` from a mid-game state. Each `run` is a fresh subprocess init — pyxel-mcp's isolation model (spec §5.1) makes each call start from frame 0. The cumulative-replay approach is the correct trade-off: slower than continuation but deterministic. This differs from godogen, where Bevy's persistent `World` allows `Update`-loop continuation.

### Spawn determinism — `random_seed` alone is not enough

`random_seed=42` to `run` seeds Pyxel's `pyxel.rseed` and Python's stdlib `random` once at the pre-loop checkpoint. **It does not guarantee identical spawn timing across `run` calls with different `frames=` values** if the script reads `random` inside `update()` based on accumulated state — the seeded sequence advances per call to `random.randint` / `random.choice`, so a longer run draws more numbers from the same seeded stream and the *order* of what gets produced when can shift if the script's branch points differ.

For Pattern C cumulative replay (and any check #4 / #5 / #10 win/lose/genre-identity playthrough), spawn timing must be deterministic by **construction**, not by reseeding. Two patterns:

```python
# Pattern: integer-modular spawn (simplest, no RNG state)
def update(self):
    if self.frame % SPAWN_PERIOD == 0:
        spawn_x = (self.frame * 37) % SCREEN_W   # deterministic by frame
        self.spawn_hazard(spawn_x)

# Pattern: dedicated frame-counted RNG (when variety is needed)
def update(self):
    if self.frame % SPAWN_PERIOD == 0:
        rng = random.Random(self.frame)         # fresh RNG per spawn frame
        spawn_x = rng.randint(0, SCREEN_W - 16)
        self.spawn_hazard(spawn_x)
```

Both patterns produce identical spawn sequences regardless of `frames=` value passed to `run`, because the spawn position depends only on `self.frame`, not on accumulated draws from a single shared RNG.

If your spawn must use a single shared `random.Random` instance for variety, snapshot its state and replay it explicitly rather than relying on `random_seed`. As a quick check: run `result = run(..., frames=N, snapshots=[{"frame": F, "kind": "state", "attrs": ["spawn_x_at_F"]}])` twice with different `N` values (both `N >= F`); if `spawn_x_at_F` differs, your spawn isn't seed-deterministic and the gate's win/lose checks will be flaky.

A second pattern, useful when input would have to thread a precise needle: temporarily replace input checks with state observation in a test fixture:

```python
# Production code:
if pyxel.btn(pyxel.KEY_UP) and self.on_ladder:
    self.y -= CLIMB_SPEED

# Deterministic test (in an instrumented build):
if self.test_target_y is not None and self.y > self.test_target_y:
    self.y -= CLIMB_SPEED
```

Design milestones around what state should be reached, not what input should have happened. See `test-harness.md` for the full segmented playthrough pattern.

### Variability tests (gate #4b/#4c — playability proof, not just solvability)

Pattern C above proves a winning trajectory **exists**. Quality-gate #4b/#4c additionally demand the game admits *human-like* play — multiple seeds, jitter-tolerant timing, multiple strategies. Without these, you've found an answer key, not a game. After Pattern C converges on a winning input schedule, run these checks before declaring task done.

```python
import random

# Assumes `inputs` is the cumulative input schedule that cleared under seed=42.
final = <last milestone frame>
attrs = ["scene"]   # plus any milestone-relevant attrs

# --- #4b — ±3 frame jitter, 5 trials, must clear in ≥ 4 ---
JITTER = 3
N_TRIALS = 5
THRESHOLD = 4

cleared = 0
for trial in range(N_TRIALS):
    rng = random.Random(trial)
    jittered = [
        {**inp, "frame": max(0, inp["frame"] + rng.randint(-JITTER, JITTER))}
        for inp in inputs
    ]
    result = run(script="main.py", frames=final + 5, random_seed=42,
                 inputs=jittered,
                 snapshots=[{"frames": [final], "kind": "state", "attrs": attrs}])
    snaps = {(s["kind"], s["frame"]): s for s in result["snapshots"]}
    if snaps[("state", final)]["values"]["scene"] == "WIN":
        cleared += 1

if cleared < THRESHOLD:
    # Don't tighten thresholds — fix the game. See knowledge/game-feel.md
    # "Variability Budget" for design constants (hazard window, input
    # spacing, invuln frames, etc.).
    raise SystemExit(f"jitter test: {cleared}/{N_TRIALS} — game requires "
                     f"frame-perfect timing")

# --- #4a — multi-seed, same input schedule, all must clear ---
for seed in [42, 99, 1]:
    result = run(script="main.py", frames=final + 1, random_seed=seed,
                 inputs=inputs,
                 snapshots=[{"frames": [final], "kind": "state", "attrs": attrs}])
    snaps = {(s["kind"], s["frame"]): s for s in result["snapshots"]}
    final_scene = snaps[("state", final)]["values"]["scene"]
    if final_scene != "WIN":
        # Spawn timing depends on RNG sequence — make spawns deterministic
        # by frame (see "Spawn determinism" subsection above).
        raise SystemExit(f"seed={seed}: scene={final_scene}, expected WIN")

# --- #4c — find a second strategy that also clears ---
# The 'distinct' strategy is up to you. Common shapes:
#  - take a different path (skip a pickup, take a longer-but-safer route)
#  - use jumps where Strategy A used hammers (or vice versa)
#  - climb a different ladder column
# Document both in PLAN.md ## Win Path Strategies.
inputs_strategy_b = <agent-designed alternate input schedule>
result_b = run(script="main.py", frames=final + 1, random_seed=42,
               inputs=inputs_strategy_b,
               snapshots=[{"frames": [final], "kind": "state", "attrs": attrs}])
snaps = {(s["kind"], s["frame"]): s for s in result_b["snapshots"]}
if snaps[("state", final)]["values"]["scene"] != "WIN":
    raise SystemExit("Strategy B did not clear — game is single-thread, "
                     "not gameplay. Tune until ≥ 2 strategies viable.")
```

If any of these fail, **do not** lower the gate constants (JITTER, THRESHOLD, strategy count) — that's anti-shortcut #5 in disguise. Fix the design via the constants in `knowledge/game-feel.md` "Variability Budget".

## Per-task implementation checklist

Before marking a task done in PLAN.md:

- [ ] Code change is minimal and confined to the task's scope (no drive-by edits).
- [ ] `validate` clean.
- [ ] One `run` call with smoke screen_image + milestone state snapshots: no black screen, no obvious render bug.
- [ ] All Verify predicates from PLAN.md are observed in `state` snapshots / `run` output.
- [ ] PLAN.md task marked done with a one-line `verified by:` note (e.g., `verified by: run frames=420, state snapshot at frame 419 → scene=WIN, score=12000`). If the task uses ASSERT lines, also include the assertion summary: `verified by: run frames=420, state snapshot frame 419 → scene=WIN; assertions: win_path_complete=PASS`.
- [ ] `MEMORY.md` updated if a gotcha was discovered (don't repeat yourself in the next task).

## What to record in MEMORY.md

`MEMORY.md` is the project-local log of gotchas — the file you'll thank yourself for in the next session. Append items only when they meet all three:

- Non-obvious (a fresh reader of `quirks.md` would not have predicted it).
- Project-specific (general Pyxel behavior belongs in `quirks.md`, not here).
- Cost more than 5 minutes to track down.

Format: one bullet, one or two sentences, with the symptom first and the fix second. Examples: `- Boss spawns at x=128 collide with HUD score text (also at x=128). Fixed: drew score at x=120.` Don't write a postmortem; one bullet is enough. The next session reader scans MEMORY.md before touching `task-execution`.

## Stop hook awareness

The Stop hook (`hooks/stop_check_bundle.py`) fires at session end and warns on a missing or incomplete proof bundle. **Do not** rely on it to enforce; you must run the gate (Stage 7) explicitly. The hook is a guardrail against accidental "I'm done" — it is not a quality gate.

## Anti-patterns in this stage

- **Implementing all tasks before verifying any.** Catch a bad pattern before propagating it across five tasks.
- **Skipping Risk Tasks for Main Build because Main Build is "easier".** Risk Tasks were isolated for a reason — bugs in them spread into Main Build with interest.
- **Editing physics constants mid-task.** If `JUMP_VY` changes, all jump-related milestones in PLAN.md need re-verification — and they probably already passed at the old value, so changing it now silently breaks them.
- **Adding new features mid-task.** If a fix needs a new system (e.g., particle effects for damage flash), open a new task in `PLAN.md` and verify it on its own loop. Don't pile.
- **"It works on my machine" via interactive run.** Stage 6 verifies via the harness — `run` for state and screen, `read_audio` for audio. An interactive run means nothing.
- **Skipping `MEMORY.md` updates.** A gotcha you found and didn't write down will cost an hour next session.

## When this stage is done

- Every PLAN.md task is marked done with a one-line `verified by:` note.
- `MEMORY.md` records the gotchas worth keeping.
- The proof bundle exists at `screenshots/result/<N>/` (win-path GIF, lose-path GIF, milestone frames, audio renders) — see `capture.md` for the bundle contract.
- Move to Stage 7 (read `quality-gate.md`).
