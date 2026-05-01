# Quality Gate — final acceptance criteria

**Phase 9.** The gate is the contract that prevents shortcut "done"
declarations. The AI cannot tell the user the game is finished
until **every** Tier 1 check passes and at least 3 of 4 Tier 2
checks pass.

This file is the AI's checklist. The MCP also exposes a
`quality_gate` tool that runs the same checks programmatically and
returns a structured PASS/FAIL report.

## Tier 1 — Stability (HARD; must all pass)

| # | Check | How |
|---|-------|-----|
| 1.1 | Project artifacts exist | `REFERENCE.md`, `PLAN.md`, `STRUCTURE.md`, `ASSETS.md` all present and non-empty |
| 1.2 | Script validates | `validate_script` clean (no syntax errors, anti-pattern warnings reviewed) |
| 1.3 | Smoke run | `run_and_capture` at frame 30 returns non-empty image, no crash |
| 1.4 | Asset identity | For each asset in ASSETS.md: pixels match `represents`, color region count ≥ declared minimum, silhouette < 95% box density, paired-frame diff in 5–50% range |
| 1.5 | Win path | `play_and_capture` with PLAN.md win-path inputs reaches `scene == WIN` by the final-milestone frame |
| 1.6 | Lose path | `play_and_capture` with PLAN.md lose-path inputs reaches `scene == GAME_OVER` by the final-milestone frame |
| 1.7 | Audio renders | For every entry in REFERENCE.md §6: `render_audio` returns duration > 0, peak > minimum threshold |
| 1.8 | Proof bundle | `screenshots/result/<N>/` exists with `win-path.gif`, `lose-path.gif`, frames, audio WAVs |

Any FAIL → return to the relevant phase. Do not retry the gate
without fixing the cause.

## Tier 2 — Balance (SOFT; need 3 of 4)

| # | Check | How |
|---|-------|-----|
| 2.1 | Palette hierarchy | `inspect_palette` reports `Hierarchy score: 2/2` |
| 2.2 | Contrast | `inspect_palette` low-contrast warnings ≤ 1 |
| 2.3 | Difficulty floor | Lose path takes between 10 and 25 seconds — too fast = unfair, too slow = boring |
| 2.4 | Layout balance | `inspect_layout` reports H-balance ≥ 70% on PLAY scene |

3 of 4 → PASS. Fewer → return to the appropriate phase
(palette/asset-gen for 2.1/2.2; PLAN.md timing for 2.3; layout
constants for 2.4).

## Tier 3 — Regression (informational)

If a previous bundle exists at `screenshots/result/<N-1>/`:

- Compare bundle file sizes, frame counts. Drastic shrinkage
  suggests broken capture.
- Compare audio render durations. Sudden zero suggests an SE was
  removed or moved channels.

This tier doesn't block but warns; humans should review surprising
deltas.

## What "done" means

After PASS:

- `PLAN.md` shows all tasks marked `done` with verified-by notes.
- `MEMORY.md` has any non-obvious gotchas captured.
- The latest `screenshots/result/<N>/` bundle is the deliverable.
- The user can run `python main.py` and play the game.

When reporting completion to the user, include:

- Path to `screenshots/result/<N>/`
- One-line summary of what was implemented
- Any Tier 2 checks that didn't pass and why (with rationale why
  it's acceptable as-is)
- Known limitations / out-of-scope items

## Specific FAIL modes and where to go

| FAIL | Phase to return to |
|------|-------------------|
| 1.1 missing artifact | Whichever phase produces it (visual-target / decomposer / scaffold / asset-planner) |
| 1.2 syntax / anti-pattern | task-execution |
| 1.3 black screen / crash | task-execution (likely scaffold or asset-gen) |
| 1.4 single-blob sprite | asset-gen |
| 1.4 frames identical | asset-gen (replace one of the pair) |
| 1.5 win path doesn't reach WIN | task-execution (climb / win-trigger logic) or PLAN.md milestones too aggressive |
| 1.6 lose path doesn't reach GAME_OVER | task-execution (collision / death logic) or PLAN.md milestones too lenient |
| 1.7 audio missing | asset-gen (sound definitions) |
| 1.8 missing bundle | capture |
| 2.1 / 2.2 contrast | asset-planner / asset-gen (recolor) |
| 2.3 difficulty | task-execution (tune barrel speed, spawn rate) |
| 2.4 layout | scaffold (recenter content) |

## Anti-shortcut rules (restated)

These are the cheats the gate is built to catch:

1. **"It compiles and runs, looks fine"** — `validate_script` and
   `run_and_capture` together don't certify gameplay; they certify
   the script doesn't crash. Tier 1.5 / 1.6 are the gameplay
   certifications.
2. **"I added a sprite"** — without `inspect_sprite` matching the
   `represents` description, the sprite is unverified. Add to ASSETS,
   render, look, compare to `represents`.
3. **"Bundle exists"** — without playthrough completion, the bundle
   could be a 30-frame loop. Tier 1.5 / 1.6 require *full* playthrough
   reach.
4. **"Audio plays"** — without `render_audio` returning non-empty
   notes, the sound slot may be empty.
5. **Adjusting milestones to fit** — if the game can't reach WIN by
   the planned frame, fix the game, not the milestone. Backward edits
   to PLAN.md require re-running win/lose paths.

## When this gate PASSes

Report to the user with the bundle path, then stop.
