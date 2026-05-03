---
name: pyxel
description: Build complete retro games with Pyxel through a verified, gated pipeline. TRIGGER when the user wants to make a Pyxel / retro / 8-bit / pixel-art game, or asks to recreate a classic arcade title. DO NOT TRIGGER on general Python work, on existing non-Pyxel projects, or when a different game engine (Pygame, Godot, Unity) is mentioned.
license: MIT
version: 0.2.0
---

# pyxel — Retro Game Production Harness

Build playable, clearable, recognizable-sprite Pyxel games via a phased pipeline that prevents shortcut "done" declarations. Every stage gates the next; the agent cannot self-certify completion without observable artifacts.

## Required runtime

This skill assumes `pyxel-mcp` ≥ 0.10.0 is installed and registered as an MCP server reachable at the namespace `pyxel`. On activation, before reading any stage file, verify:

- `mcp__pyxel__pyxel_info` is callable.
- `mcp__pyxel__validate` is callable.
- `mcp__pyxel__run` is callable.

If absent, run:

```bash
uvx pyxel-mcp --version
```

If not installed, instruct the user to add to their `.mcp.json`:

```json
{
  "mcpServers": {
    "pyxel": { "command": "uvx", "args": ["pyxel-mcp"] }
  }
}
```

The skill cannot proceed without these tools. Bail with a clear message if Claude Code's permission prompt for `uvx` is denied.

## Pipeline

```
User request: "make a Pyxel game ..."
        |
        +-- PLAN.md exists? (Resume Detection — see below)
        |     |
        |     +-- yes: read PLAN.md / STRUCTURE.md / MEMORY.md / ASSETS.md, jump to Stage 6
        |     +-- no: continue
        |
        +-- Stage 1  visual-target  -> ASSETS.md "Art direction" + STRUCTURE.md "Vision"
        +-- Stage 2  decomposer     -> PLAN.md (Risk Tasks + Main Build + Win/Lose milestones)
        +-- Stage 3  scaffold       -> STRUCTURE.md complete + skeleton main.py + .pyxel-skill/ marker
        +-- Stage 4  asset-planner  -> ASSETS.md sprite manifest
        +-- Stage 5  asset-gen      -> _build_assets() populated, per-sprite verified
        |
        +-- Show user a concise plan summary (risk tasks if any, main build scope)
        |
        +-- Stage 6  task-execution
        |     +-- Risk Slice: implement each PLAN.md risk task in isolation, verify, commit
        |     +-- Main Build: implement remainder, verify, commit
        |     +-- (calls test-harness.md and capture.md as references when needed)
        |
        +-- Stage 7  quality-gate   -> flat stop-conditions list; FAIL -> loop back to phase that owns the failure
        |
        +-- Proof bundle present at screenshots/result/<N>/
        +-- Pre-handoff agent visual review: Read each key frame PNG, verbalize, compare to PLAN.md milestones (capture.md)
        +-- Stop hook fires (best-effort assertion that bundle is well-formed)
        +-- Summary to user
```

Each stage file is read **only when entering that stage** (JIT loading). Reference files (`quirks.md`, `test-harness.md`, `capture.md`, and any `knowledge/*`) are loaded on demand from within stage files, not eagerly.

## Capabilities

| File | Purpose | When to read |
|------|---------|--------------|
| `visual-target.md` | Stage 1: art direction + Vision section | Pipeline start (no PLAN.md) |
| `decomposer.md` | Stage 2: PLAN.md authoring | After Stage 1 |
| `scaffold.md` | Stage 3: STRUCTURE.md + skeleton + marker | After Stage 2 |
| `asset-planner.md` | Stage 4: ASSETS.md sprite manifest | After Stage 3 |
| `asset-gen.md` | Stage 5: hex-string sprite implementation + verify | After Stage 4 |
| `task-execution.md` | Stage 6: gameplay implementation loop | After Stage 5 (or on resume) |
| `quality-gate.md` | Stage 7: stop-conditions + PASS/FAIL report | At end of Stage 6 |

### Phase names ↔ stage files

The quality gate's `gate-report.json` writes abstract phase names in `fail_route` so the artifact stays stable across stage-file renames. Use this table to route a FAIL to the right file:

| Abstract phase    | Stage file          |
|-------------------|---------------------|
| `visual-design`   | `visual-target.md`  |
| `spec`            | `decomposer.md`     |
| `scaffolding`     | `scaffold.md`       |
| `asset-planning`  | `asset-planner.md`  |
| `sprite-quality`  | `asset-gen.md`      |
| `playthrough`     | `task-execution.md` |
| `bundle`          | `capture.md`        |
| `quirks.md` | Pyxel API gotchas | When Pyxel behaves unexpectedly |
| `test-harness.md` | Milestone playthrough verification | Called from Stage 6 |
| `capture.md` | Proof bundle production | Called from Stage 6 / Stage 7 |
| `knowledge/pixel-art.md` | Sprite + palette + color hierarchy | Stage 4, Stage 5, Stage 7 |
| `knowledge/background.md` | Bg + parallax + screen layout | Stage 1, Stage 3, Stage 7 |
| `knowledge/game-feel.md` | Physics + jumps + hitboxes + camera + shake | Stage 6 |
| `knowledge/audio.md` | SE cookbook + MML + channel discipline | Stage 3, Stage 6 |
| `knowledge/patterns.md` | Title screen, scene SM, level/enemy, animation timing | Stage 3, Stage 6 |

## Persistent state

Four files at project root, written across stages, read on resume:

| File | First written by | Purpose |
|------|------------------|---------|
| `PLAN.md` | Stage 2 | Risk Tasks (Approach + Verify) + Main Build modules + Win/Lose milestone tables |
| `STRUCTURE.md` | Stage 3 | Architecture: modules, scene state machine, tuning constants, Vision (from Stage 1) |
| `ASSETS.md` | Stage 1 (Art direction line) → Stage 4 (sprite manifest) | Art direction + sprite manifest |
| `MEMORY.md` | Stage 6+ | Discoveries, gotchas, what worked / didn't |

If the conversation grows long, summarize relevant state into these files and continue from artifacts instead of conversational memory.

## Resume Detection

`ASSETS.md` is touched by **both** Stage 1 (writes the `**Art direction:**` line) and Stage 4 (appends the sprite manifest with `## Sprites` / `## Player` / etc. headings). Resume must inspect content, not just existence:

On entry, check (in order):

1. `PLAN.md` exists at project root → resume mode. Read PLAN / STRUCTURE / MEMORY / ASSETS, route to Stage 6 unless `screenshots/result/<latest>/gate-report.json` shows incomplete earlier stages.

2. `ASSETS.md` exists but `PLAN.md` does not:
   - If `ASSETS.md` contains any sprite-manifest heading (`## Player`, `## Sprites`, `## Hazard`, etc.) → re-enter Stage 2 (Stage 4 was started without Stage 2; reconcile: PLAN.md milestones must reference assets actually planned).
   - Else (only `**Art direction:**` line) → re-enter Stage 2.

3. `STRUCTURE.md` exists but `PLAN.md` and `ASSETS.md` do not → unusual. Treat as corrupted state; ask the user whether to discard and restart.

4. None exist → fresh pipeline, start at Stage 1.

## Anti-shortcut rules

These are the cheats this harness exists to catch. Do not commit any of them.

1. **Visual primacy.** When code says X happened but a captured frame shows Y, trust the capture.
2. **Trust media over code.** A passing `validate` and a non-crashing `run` only certify the script does not crash. They do not certify gameplay.
3. **No procedural fallback.** `pyxel.rect(x, y, 16, 16, 8)` in place of a declared sprite means asset-gen was skipped. Go back. The `pyxel.rect()` calls for player/enemy bodies are a red flag.
4. **Bundle integrity.** A `screenshots/result/<N>/` bundle whose first 3 seconds are correct and the rest is static is FAIL, not partial pass.
5. **Bias toward failure.** If behavior is not clearly visible in the capture, treat as not-done. Hidden or inferred behavior does not count.
6. **Closed-loop input only.** Open-loop scripted input drifts past ~200 frames. Issue `run` calls in segments per Pattern C (cumulative-replay), reading observed `state` snapshots between segments and recomputing the next input schedule from the actual position.
7. **No "looks fine".** Every verify is a specific predicate against an observed value, not a vibe check.
8. **No bundle, no done.** A `screenshots/result/<N>/` directory containing win-path.gif, lose-path.gif, frames, audio WAVs is the precondition for declaring "done". A green gate report without a bundle is FAIL.
9. **No user-handoff without agent visual review.** Before reporting "done" to the user, agent (you) must `Read` every key frame in the proof bundle, verbalize observations in 1–2 sentences each, and confirm against PLAN.md milestones. Bundle existence + 15-check gate PASS is necessary but not sufficient — the agent's own multimodal judgment is the final gate. "Did I look at the screenshot?" is a precondition for "is this done?". Tool-based checks (`read_image` verdicts, `state` snapshots) certify mechanics; only the agent's own eyes certify *recognizability* and *playability*. See `capture.md` "Pre-handoff agent review".

## Quality gate is the contract

Done is whatever `quality-gate.md`'s stop conditions say is done. The agent cannot skip ahead, cannot self-certify, and cannot claim "done" with unaddressed FAILs. Re-enter whichever phase the FAIL points to, remediate, re-run the gate.

The Stop hook (`hooks/stop_check_bundle.py`) fires at session boundary as a non-blocking tripwire. It surfaces missing bundles or unaddressed gate FAILs to the user — it does not replace the agent running the gate.

## What is NOT this skill's job

- Generic Python work, library development, non-game scripts.
- Non-Pyxel game engines (Godot, Unity, Pygame).
- Pure pyxel-mcp connector usage. If a user only needs verification tools without the harness, they should invoke `pyxel-mcp` directly without this skill.

## Reference

- Pyxel API: fetch via `pyxel://api-reference` MCP resource.
- Pyxel examples: `pyxel://examples/<name>` MCP resources (e.g., `02_jump_game`, `09_shooter`).
- Pyxel default palette: `pyxel://palette/default` MCP resource.
- `run` snapshot schema: `pyxel://run-snapshots-schema` MCP resource. Read before constructing complex `run` snapshot lists.
- pyxel-mcp tool catalog: see its loaded `instructions`.
- Design rationale: `docs/superpowers/specs/2026-05-01-pyxel-harness-design.md`.
