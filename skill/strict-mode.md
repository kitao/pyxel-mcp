# Strict Mode

Use this only when the user asks for release-quality proof, an audit trail, or a game large enough that lightweight iteration is no longer reliable.

## Trigger

Strict mode is opt-in. Do not apply it to small prototypes by default.

Good triggers:

- "make this release-ready"
- "produce a proof bundle"
- "verify adversarially"
- "continue this over multiple sessions"
- "I need confidence before publishing"

## Evidence Bundle

Create `screenshots/result/<N>/` with only the artifacts that prove the current game:

- `frames/`: title/start, representative play, success, and failure/retry if applicable.
- `win-path.gif` or `.mp4` when the game has a clearable path.
- `fail-path.gif` or `.mp4` when the genre has hazards, enemies, timeouts, or an explicit fail state.
- `audio/*.wav` only for games with authored audio.
- `notes.md`: controls, verification commands, and known limitations.

## Checks

Run these in order and stop on the first failure:

1. `validate` has no errors and no relevant warnings.
2. Smoke `run` reaches the requested frame count.
3. Captured frames are non-blank and visually match the intended scene.
4. Genre predicates pass from `state` snapshots.
5. Success/failure paths are verified when the genre has them.
6. Captured gameplay is not static during active play.
7. Audio slots used by the game render audible WAVs.
8. Final visual review agrees with the user's brief.

Write `gate-report.json` only if a machine-readable report helps the user. Keep it small: check name, PASS/FAIL, evidence path or observed value.

## Genre Notes

Do not force action-game checks onto puzzle games. A Sokoban level needs solvability and illegal-push rejection; it does not need hazard distribution. A platformer needs collision and timing tolerance; it may not need sprite-bank analysis. Choose evidence from the game, not from a fixed checklist.
