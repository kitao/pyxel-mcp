# pyxel-skill

A [Claude Code](https://claude.com/claude-code) Skill that drives end-to-end production of **playable, clearable, recognizable-sprite** Pyxel games. Combines a phased workflow harness with topical knowledge files and an enforcement hook that prevents the agent from declaring "done" with placeholder garbage.

This skill orchestrates the workflow; [`pyxel-mcp`](https://github.com/kitao/pyxel-mcp) (≥ 1.0.0) provides the verification verbs across two layers — Layer 1 `observe` (`run`, `validate`, `read_*`, `diff_frames`) and Layer 2 `judge_*` (8 policy primitives).

## Status

`v0.2.0` — built on top of pyxel-mcp's 9-tool redesign (0.10.0). 7-stage pipeline; 13-check quality gate (15 in newer roadmap drafts). Donkey Kong is the canonical validation target — see `docs/validation/dk-reference.md`.

## Pipeline

```
visual-target  →  decomposer  →  scaffold  →  asset-planner  →  asset-gen
                                                                     ↓
                                              quality-gate  ←  task-execution
```

Each stage writes / refines persistent state at project root (`PLAN.md`, `STRUCTURE.md`, `ASSETS.md`, `MEMORY.md`) so long sessions survive context compaction. Stage entry checks the existing files and resumes where you left off.

The quality gate is the **single source of "done"**. It runs every sprite identity check, win-path playthrough, lose-path playthrough, audio render, and palette analysis; emits `screenshots/result/<N>/gate-report.json`. The agent cannot self-certify completion — only a clean gate passes.

## Anti-shortcut enforcement

Built-in guard rails (see `SKILL.md`'s "Anti-shortcut rules"):

- **Visual primacy** — when code says X happened but the captured frame shows Y, the capture wins.
- **No procedural fallback** — `pyxel.rect(x,y,16,16,8)` for a player body means asset-gen was skipped; gate FAILs.
- **No "looks fine"** — every Verify is a specific predicate against an observed value.
- **No bundle, no done** — `screenshots/result/<N>/` with win-path GIF, lose-path GIF, frame PNGs, audio WAVs is the precondition for declaring complete.
- **No mid-attempt threshold relaxation** — quality-gate thresholds are committed before a run; changing them during a run is documented in gate-report.json and forces an automatic FAIL.

## Install

1. Clone this repo:

   ```bash
   git clone https://github.com/kitao/pyxel-skill.git
   ```

2. Symlink it into your Claude Code skills directory:

   ```bash
   ln -s "$(pwd)/pyxel-skill" ~/.claude/skills/pyxel
   ```

3. Install the Stop hook (one-time per machine):

   ```bash
   ~/.claude/skills/pyxel/hooks/install.sh
   ```

   Non-blocking warning at session end if the quality gate was skipped. Idempotent.

4. Ensure `pyxel-mcp ≥ 0.10.0` is in your MCP config:

   ```json
   {
     "mcpServers": {
       "pyxel": { "command": "uvx", "args": ["pyxel-mcp"] }
     }
   }
   ```

## Use

Activate the skill by asking Claude Code:

> Make a Donkey Kong style platformer in Pyxel.

The skill walks the 7-stage pipeline, calls `pyxel-mcp` tools at each verification point, and produces a `screenshots/result/<N>/` proof bundle. A typical end-to-end run is hundreds of `run`/`read_*`/`judge_*` calls — fast because pyxel-mcp's headless mode is sub-second per playthrough.

## Repo layout

```
SKILL.md                    Pipeline orchestrator
visual-target.md            Stage 1: art direction + Vision
decomposer.md               Stage 2: PLAN.md (risks + milestones)
scaffold.md                 Stage 3: STRUCTURE.md + main.py skeleton
asset-planner.md            Stage 4: ASSETS.md sprite manifest
asset-gen.md                Stage 5: hex-string sprites + per-sprite verify
task-execution.md           Stage 6: gameplay implementation loop
quality-gate.md             Stage 7: 13+ stop conditions + gate-report.json
test-harness.md             (reference) win/lose path playthrough patterns
capture.md                  (reference) proof-bundle production
quirks.md                   (reference) Pyxel API gotchas
knowledge/                  Topical: pixel-art, background, game-feel, audio, patterns
hooks/                      Stop hook + idempotent installer
docs/                       Architecture, validation references, compatibility matrix
```

## Compatibility

| pyxel-skill | pyxel-mcp | Pyxel  | Python |
|-------------|-----------|--------|--------|
| 0.2.0       | ≥ 0.10.0  | ≥ 2.9.4| ≥ 3.10 |

## License

MIT. See `LICENSE`.
