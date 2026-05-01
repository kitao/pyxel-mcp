# Task Execution — gameplay implementation loop

**Phase 6.** Implement gameplay logic against PLAN.md and STRUCTURE.md.
The execution loop is small and verifies after every change.

## Loop

For each task in `PLAN.md`:

1. Read PLAN.md task definition. Confirm Verify criteria are clear.
2. Read STRUCTURE.md. Identify which class/function gains the change.
3. Read the relevant source code (current state).
4. Implement the smallest change that makes the task observable
   (one method, one constant, one behavior).
5. `validate_script` — must be clean.
6. `run_and_capture` at a relevant frame — sanity-render. Catches
   import errors, infinite loops, and obvious draw failures.
7. Run the task's specific Verify procedure (likely `play_and_capture`
   with scripted input + `inspect_state` at milestone frames).
8. If FAIL: read the captured state, find the divergence, fix.
   Don't move on.
9. If PASS: update `PLAN.md` (mark task done), append findings to
   `MEMORY.md` if a non-obvious gotcha was discovered, commit.

## Visual primacy

When code says X happened but capture shows Y, the capture is right.
Don't argue with the pixels. Common cases:

- "I drew the player at (40, 100)" but the screenshot shows nothing
  at (40, 100): probably `colkey` makes the sprite invisible against
  background, OR the sprite is drawn but at a different layer
  ordering, OR draw is called before `cls()`.
- "I incremented score on barrel-jump" but `inspect_state` at frame
  150 shows score == 0: the collision check never fires; either the
  hitbox is wrong or the trigger condition has off-by-one.
- "Mario climbs the ladder" but `play_and_capture` with KEY_UP shows
  Mario stuck: the climb-eligibility check has a strict bound
  (`==` instead of `<=`).

## Anti-shortcut rules

- **No "looks fine"**. Each verify is a specific predicate against
  an observed value.
- **Don't skip lose-path verification**. Win path is exciting, lose
  path is forgotten. Both must verify.
- **Don't comment out failing assertions**. Fix the code.
- **Don't lower the threshold to make it pass**. If `lives reaches 0`
  doesn't happen by frame 360 in lose path, either barrels are too
  slow (PLAN.md is wrong → re-decompose) or collision is broken
  (code is wrong → fix). Don't move the milestone to frame 600.
- **Don't trust subprocess returncode alone**. A script can run
  cleanly and produce a black screen, no audio, frozen state. Always
  observe the captured state.

## Closed-loop input simulation

Open-loop input (timed press/release) drifts. Over 200+ frames the
player position desyncs from the planned trajectory because of
floating-point physics, frame-skip, etc.

Closed-loop pattern: temporarily replace user-input checks with
deterministic state observation:

```python
# Production code:
if pyxel.btn(pyxel.KEY_UP) and self.on_ladder:
    self.y -= CLIMB_SPEED

# For deterministic test (in a test fixture or instrumented script):
if self.test_target_y is not None and self.y > self.test_target_y:
    self.y -= CLIMB_SPEED
```

`play_and_capture` provides input simulation; for sustained motion
where drift would cause divergence, design milestones around what
state should be reached, not what input should have happened.

## Per-task implementation checklist

Before declaring a task done:

- [ ] Code change is minimal and confined to the task's scope
- [ ] `validate_script` clean
- [ ] `run_and_capture` at a representative frame: no black screen,
       no obvious render bug
- [ ] All Verify predicates from PLAN.md observed
- [ ] PLAN.md task marked done with a one-line "verified by:" note
- [ ] MEMORY.md updated if a gotcha was discovered

## Anti-patterns in this phase

- Implementing all tasks before verifying any. Catch a bad pattern
  before propagating it.
- Skipping Risk Tasks for Main Build because Main Build is "easier".
  Risk Tasks were isolated for a reason — bugs in them spread into
  Main Build.
- Editing physics constants mid-task. If JUMP_VY changes, all
  jump-related milestones in PLAN.md need re-verification.
- Adding new features mid-task. If a fix needs a new system (e.g.,
  particle effects for damage flash), open a new task in PLAN.md
  and verify it on its own loop.

## When this phase is done

Every PLAN.md task is marked done with verified-by notes. Move to
`test-harness` (read `pyxel://skills/test-harness`) for the integrated
playthrough verification.
