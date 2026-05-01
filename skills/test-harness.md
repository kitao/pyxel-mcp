# Test Harness — milestone-based playthrough verification

**Phase 7.** Run the win-path and lose-path milestone tables from
PLAN.md against the implemented game. This is the integration test;
unit-style task verification was Phase 6.

## What to run

For each milestone table in PLAN.md (win + lose):

1. Build the input schedule from the table's `Inputs` column.
2. Build the assertion plan from the table's `Asserts` column.
3. Run `play_and_capture` with the input schedule, capturing
   screenshots at each milestone frame.
4. Run `inspect_state` (or its harness equivalent) at each milestone
   frame, asserting against the planned predicate.
5. Aggregate per-milestone PASS/FAIL.

## Win-path execution

The input schedule for the win path is a sequence of keys leading
the player from start to the goal. For arcade platformers it's
typically: walk to first ladder → climb → walk to next ladder →
climb → ... → reach goal.

Translate the table:

```
| Frame | Inputs (held until next row) | Asserts |
|-------|-----------------------------|---------|
| 30    | KEY_SPACE press             | scene == PLAY |
| 60    | KEY_RIGHT held              | player.x > start_x + 20 |
| 120   | KEY_UP at ladder_a          | player.y < floor_y - 8 |
```

→ `play_and_capture` inputs:

```json
[
  {"frame": 30, "keys": ["KEY_SPACE"]},
  {"frame": 32, "keys": []},
  {"frame": 60, "keys": ["KEY_RIGHT"]},
  {"frame": 120, "keys": ["KEY_UP"]},
  ...
]
```

→ `inspect_state` at frames `30, 60, 120, ...`, attributes
`scene,player.x,player.y,...`, evaluating predicates against captured
values.

## Lose-path execution

Lose path is simpler — typically the player stands still and is
killed by hazards. Schedule: empty inputs, just observe state.

```json
[{"frame": 30, "keys": ["KEY_SPACE"]}, {"frame": 32, "keys": []}]
```

Run for the full death duration (e.g., 600+ frames). Assert at
intermediate milestones that lives decrease, and at the final
milestone that scene == GAME_OVER.

If lose path doesn't fail by the planned frame, either:
- Difficulty is too low (boss spawn rate, barrel speed) — fix and
  rerun.
- Collision detection isn't actually working — back to Phase 6.

## Stall and crash monitoring

Beyond per-milestone asserts, the harness also watches:

- **Crash**: `play_and_capture` returns non-zero or stderr contains
  exception trace → FAIL with "script crashed at frame N".
- **Stall**: state hash unchanged across 60 consecutive frames
  despite scheduled inputs → FAIL with "no progress between frame
  X and frame Y; expected motion in attribute Z".
- **Frame budget**: if the script takes > 100ms per frame to render
  → WARN (not FAIL, but flagged as perf bug).

## Closed-loop steering for long playthroughs

For paths longer than ~200 frames, open-loop scripted inputs drift.
Closed-loop: at each milestone, read observed state, compute next
input segment.

Example: instead of pre-baking "hold RIGHT for 80 frames", the test
runs in segments. At each milestone, it asks "is player at the
expected ladder x?" If yes, switch to KEY_UP. If not, keep RIGHT
for another 10 frames, recheck. This is implemented as iterative
calls to `play_and_capture` with progressively-built input schedules.

For now (v0.10.0), open-loop with generous time tolerances suffices
for verifying win-path completability. Closed-loop is a future
improvement.

## Test fixture considerations

If the production code reads keyboard input via `pyxel.btnp/btn`,
the harness's `set_btn` calls flow through naturally. No code
changes needed for testing.

If the game has frame-based logic that needs determinism (e.g.,
random barrel spawn timing), seed the RNG at scene-start so
test runs are repeatable. Use `pyxel.rseed(42)` if needed.

## Anti-patterns in this phase

- Verifying only the final milestone. Intermediate milestones catch
  early divergence.
- Verifying win path but not lose path. The lose path validates
  that hazards actually function as hazards.
- Asserting "anything happened" instead of specific values. "scene
  changed" is too loose; "scene == WIN" is the right predicate.
- Forgetting to capture state at frame > duration of `play_and_capture`'s
  input schedule. The schedule's last entry must be before the last
  observation frame.

## When this phase is done

All win-path milestones PASS, all lose-path milestones PASS, no
crashes, no stalls. Move to `capture` (read `pyxel://skills/capture`)
to produce the proof bundle.
