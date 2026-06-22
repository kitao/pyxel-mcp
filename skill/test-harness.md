# Reference: Milestone Playthrough Verification

Called from `task-execution.md` (Stage 6) and from `quality-gate.md`
when re-verifying a fix. Run the win-path and lose-path milestone
tables from `PLAN.md` against the implemented game. This is the
integration test; per-task verification belonged to earlier stages.

## References

- `pyxel://run-snapshots-schema` (MCP resource) — snapshot kind schemas and multi-frame syntax.
- `task-execution.md` — per-task verification (this file scales to whole-path verification).

## What to run

For each milestone table in `PLAN.md` (one for the win path, one for the lose path):

1. Build the input schedule from the table's `Inputs` column → `inputs: list[InputEvent]`.
2. Collect every milestone frame and every attribute referenced by the table's `Asserts` column.
3. Issue **one** `run` call (Pattern A) with `inputs` and one multi-frame `state` snapshot covering the milestone frames.
4. Optionally include script-side ASSERT lines (Pattern B) and read `result["assertions"]` for the script's self-check.
5. Aggregate per-milestone PASS/FAIL by walking `result["snapshots"]` (Pattern D) and evaluating each predicate against the captured value.

## Win-path execution

The win-path schedule is a sequence of inputs leading the player
from start to goal. Translate the milestone table directly:

| Frame | Inputs (held until next row) | Asserts |
|-------|-----------------------------|---------|
| 30    | KEY_SPACE press             | scene == "PLAY" |
| 60    | KEY_RIGHT held              | player.x > start_x + 20 |
| 120   | KEY_UP at route marker      | player.y < floor_y - 8 |

becomes a single `run` call:

```python
run(
    script="main.py",
    frames=121,                    # one past the last milestone
    random_seed=42,                # required for gate playthroughs (quality-gate Anti-shortcut rule #8)
    stall_window_frames=60,        # 2s freeze detection (when state snapshots are scheduled, see §6.5)
    inputs=[
        {"frame": 30, "buttons": ["KEY_SPACE"]},
        {"frame": 32, "buttons": []},
        {"frame": 60, "buttons": ["KEY_RIGHT"]},
        {"frame": 120, "buttons": ["KEY_UP"]},
    ],
    snapshots=[
        {"frames": [30, 60, 120], "kind": "state",
         "attrs": ["scene", "player.x", "player.y"]},
    ],
)
```

After the call, walk `result["snapshots"]` (frame-ascending) and evaluate
each predicate against the matching snapshot's `values`. Pattern D for the keying:

```python
snaps = {s["frame"]: s["values"] for s in result["snapshots"] if s["kind"] == "state"}
assert snaps[30]["scene"] == "PLAY"
assert snaps[60]["player.x"] > start_x + 20
assert snaps[120]["player.y"] < floor_y - 8
```

## Lose-path execution

The lose path is usually simpler: the player stands still (or
performs the minimum input to enter PLAY) and is killed by hazards.

```python
run(
    script="main.py",
    frames=601,
    random_seed=42,                # required for gate playthroughs (quality-gate Anti-shortcut rule #8)
    stall_window_frames=60,        # 2s freeze detection (when state snapshots are scheduled, see §6.5)
    inputs=[
        {"frame": 30, "buttons": ["KEY_SPACE"]},
        {"frame": 32, "buttons": []},
    ],
    snapshots=[
        {"frames": [120, 240, 360, 480, 600], "kind": "state",
         "attrs": ["lives", "scene"]},
    ],
)
```

Predicate: lives decrements monotonically across snapshots, and the snapshot
at the largest frame has `scene == "GAME_OVER"`. If `scene` never reaches
`"GAME_OVER"` by frame 600, FAIL — either hazards are not actually hazardous
(collision detection bug; back to per-task verification) or difficulty is too
low (boss spawn rate, hazard speed) — fix and rerun.

## Stall and crash monitoring

Beyond per-milestone asserts, `run` exposes the data needed directly:

- **Crash:** `result["exit_status"] == "crashed"` and `result["errors"]`
  carries the phase + traceback. No subprocess returncode check needed.
- **Stall:** compare two `state` snapshots N frames apart — if every observed
  attribute is identical despite scheduled inputs, the game has stalled. Optionally,
  capture two `screen_image` snapshots and use Pattern G's `diff_frames` to
  confirm visual stall. Prefer `run(stall_window_frames=N, snapshots=[...])`
  with at least one `state` or `screen_grid` snapshot signal; when the observed
  signal is unchanged for the window, `exit_status` becomes `"stalled"`.
- **Frame budget:** `result["elapsed_seconds"] / frames` gives average per-frame ms.
  Same rule as before (>100ms → WARN, not FAIL).

## Closed-loop steering for paths > 200 frames

Use Pattern C verbatim. pyxel-mcp's subprocess isolation precludes mid-run
resume, so the canonical pattern is cumulative-replay from frame 0 with the
union of all input segments. The trade-off is determinism over runtime cost:
fresh subprocesses guarantee no leaked state between attempts.

Example: instead of pre-baking "hold RIGHT for 80 frames", check at frame 60
whether the player has reached the expected route x — if yes, switch to KEY_UP;
if not, add more KEY_RIGHT inputs and rebuild the cumulative schedule from frame 0.

Open-loop input with generous tolerances handles most win paths under roughly
200 frames. Pattern C (cumulative-replay segmentation) is the escape hatch when
a single open-loop schedule cannot be made deterministic.

## Test fixture considerations

Pyxel reads input via `pyxel.btnp` / `pyxel.btn`. The harness's `apply_to_pyxel`
(called from `run`'s frame loop) drives Pyxel's `set_btn` / `set_btnv` API
directly, in the same OS process as the script. There is no cross-process
keyboard emulation; combined with `random_seed`, this gives frame-precise
deterministic input replay. Production code does not need a separate
"capture mode" branch to be testable — the gate's playthroughs use the same
code path the player will run.

Avoid cross-process keyboard emulation. Pyxel-mcp closes that gap structurally:
`set_btn` writes the same input
ring buffer that `pyxel.btn` reads, on the same frame, in the same process.
Drift, when it occurs, comes only from physics over long horizons, which is
what Pattern C (cumulative-replay) is for.

For frame-based logic that needs determinism (random spawn timing, particle scatter),
`run` accepts `random_seed: int` which seeds Pyxel's RNG (`pyxel.rseed`) at the
pre-loop checkpoint. Pass the same seed across re-runs for reproducible behavior:

```python
run(script="main.py", frames=600, random_seed=42, inputs=..., snapshots=...)
```

## Anti-patterns

- Snapshotting only the final milestone. Intermediate `state` entries cost
  nothing extra (one `run` call) and catch divergence early — Pattern D's
  snapshot-by-frame indexing makes intermediate entries cheap to read.
- Verifying only the win path and skipping the lose path. The lose path is what
  proves hazards function as hazards.
- Loose predicates ("scene changed") instead of exact values ("scene == WIN").
  A loose predicate passes for the wrong reason.
- Listing milestone frames in `snapshots` that exceed `frames`. The `frames`
  parameter must be at least one past the last milestone frame, or the snapshot
  will not be captured.

## When this is done

All win-path milestones PASS, all lose-path milestones PASS, no crashes, no
stalls. Return to `task-execution.md` and proceed to producing the proof
bundle (`capture.md`).
