# pyxel skill

The bundled workflow skill for [`pyxel-mcp`](https://github.com/kitao/pyxel-mcp). Drives end-to-end production of **playable, clearable, recognizable-sprite** Pyxel games via a phased 7-stage pipeline with topical knowledge files and an enforcement hook that prevents the agent from declaring "done" with placeholder garbage.

This skill orchestrates the workflow; pyxel-mcp (≥ 1.0.0) provides the 9 observation verbs (`run`, `validate`, `read_*`, `diff_frames`, `pyxel_info`). Quality verification is the agent's responsibility — the agent asserts predicates directly in Python against `state` snapshots and uses `Read` on captured PNG bundles to verbalize against PLAN.md / ASSETS.md anchors. There are no judge tools and no hardcoded numerical thresholds.

## Status

`v1.0.0` — built on top of pyxel-mcp's 9-tool surface. 7-stage pipeline; 11-step quality gate. Donkey Kong is the canonical multi-hazard validation target.

## Pipeline

```
visual-target  →  decomposer  →  scaffold  →  asset-planner  →  asset-gen
                                                                     ↓
                                              quality-gate  ←  task-execution
```

Each stage writes / refines persistent state at project root (`PLAN.md`, `STRUCTURE.md`, `ASSETS.md`, `MEMORY.md`) so long sessions survive context compaction. Stage entry checks the existing files and resumes where you left off.

The quality gate is the **single source of "done"**. It runs 11 stop conditions: state files exist, validate clean, smoke run, win-path direct asserts, lose-path direct asserts, difficulty floor, audio peaks + notes, proof bundle + max-pairwise-diff dead-time, tilemap trap clean, genre-identity Python predicates, agent visual review of bundle frames. Emits `screenshots/result/<N>/gate-report.json`. The agent cannot self-certify completion — only a clean gate passes.

## Anti-shortcut enforcement

Built-in guard rails (see `SKILL.md`'s "Anti-shortcut rules"):

- **Visual primacy** — when code says X happened but the captured frame shows Y, the capture wins.
- **No procedural fallback** — `pyxel.rect(x,y,16,16,8)` for a player body means asset-gen was skipped; gate FAILs.
- **No "looks fine"** — every Verify is a specific Python predicate against an observed value.
- **Bundle integrity** — a bundle whose first 3 seconds are correct and the rest is static is FAIL, not partial pass.
- **No bundle, no done** — `screenshots/result/<N>/` with win-path GIF, lose-path GIF, frame PNGs, audio WAVs is the precondition for declaring complete.
- **No user-handoff without agent visual review** — agent must `Read` every bundle frame and verbalize against PLAN.md milestones before the gate PASSes.

## Install

The skill ships inside the `pyxel-mcp` package. Two activation paths:

1. **MCP resource channel** — already live once `pyxel-mcp` is installed. Reference any stage file as `@pyxel:workflow/<stage>` (Claude Code) or read via the `pyxel://workflow/*` URIs.

2. **Host skill channel** (auto-activates on Pyxel-related prompts):

   ```bash
   uvx pyxel-mcp publish-skill ~/.claude/skills/pyxel
   ```

   Restart your client. Then the skill activates on phrases like "make a Pyxel game", "build a retro shooter", "remake Donkey Kong in Pyxel".

3. (Optional) Install the Stop hook for a non-blocking tripwire if the quality gate is skipped:

   ```bash
   ~/.claude/skills/pyxel/hooks/install.sh
   ```

   Idempotent.

## Use

Activate the skill by asking your client:

> Make a Donkey Kong style platformer in Pyxel.

The skill walks the 7-stage pipeline, calls pyxel-mcp tools at each verification point, and produces a `screenshots/result/<N>/` proof bundle. A typical end-to-end run is hundreds of `run` / `read_*` / `diff_frames` calls — fast because pyxel-mcp's headless mode is sub-second per playthrough.

## Repo layout

```
SKILL.md                    Pipeline orchestrator
visual-target.md            Stage 1: art direction + Vision
decomposer.md               Stage 2: PLAN.md (risks + milestones + Genre Identity)
scaffold.md                 Stage 3: STRUCTURE.md + main.py skeleton
asset-planner.md            Stage 4: ASSETS.md sprite manifest
asset-gen.md                Stage 5: hex-string sprites + per-sprite verify
task-execution.md           Stage 6: gameplay implementation loop
quality-gate.md             Stage 7: 11 stop conditions + gate-report.json
test-harness.md             (reference) win/lose path playthrough patterns
capture.md                  (reference) proof-bundle production
quirks.md                   (reference) Pyxel API gotchas
knowledge/                  Topical: pixel-art, background, game-feel, audio, patterns
hooks/                      Stop hook + idempotent installer
```

## Compatibility

| skill | pyxel-mcp | Pyxel   | Python |
|-------|-----------|---------|--------|
| 1.0.0 | ≥ 1.0.0   | ≥ 2.9.5 | ≥ 3.10 |

## License

MIT. See `LICENSE`.
