# Pyxel MCP Quality Harness Design (godogen-modeled)

## Problem

The current pyxel-mcp (0.9.3) is a tool dump. AI using it can declare
"done" while shipping unplayable garbage:

- Sprites that aren't recognizable as anything
- Physics broken (jump-through-floor, no slope walking)
- Game flow broken (barrels never reach bottom, win never triggers)
- BGM/SE declared but never verified to actually play
- Verification = "I captured frame 30, looks fine"

Both my own dkong and a fresh subagent's dkong demonstrate this.

## Reference: godogen

[godogen](https://github.com/htdt/godogen) is a working autonomous
game-development pipeline for Godot/Bevy. Its harness is **not new
tools** — it's:

1. A pipeline definition in a top-level skill (orchestrator)
2. Phase-specific markdown files JIT-loaded when entering each phase
3. Persistent state files surviving compaction (PLAN, STRUCTURE,
   MEMORY, ASSETS)
4. A risk-slice / main-build two-phase execution
5. A stop hook that requires a final proof bundle to exist
6. Instructions explicitly forbidding shortcuts:
   - "When code and media disagree, trust the media"
   - "Placeholder primitives in gameplay code are a signal that the
     asset step was skipped"
   - "A bundle where the opening seconds look correct and the rest
     degenerates is failure, not partial pass"

This is the proven pattern. We adapt it to Pyxel.

## Architecture for Pyxel

### Pipeline (orchestrator → JIT phases)

```
User: "make a Pyxel game"
    │
    ▼
Read instructions.md (orchestrator) — defines pipeline + invariants
    │
    ▼
Phase 1: visual-target → REFERENCE.md (game's vision: palette, sprite
                                        list with sizes/positions, HUD,
                                        layout, audio cues)
    │
    ▼
Phase 2: decomposer → PLAN.md (risk tasks, main build, verify criteria
                                per task, win/lose milestone tables)
    │
    ▼
Phase 3: scaffold → STRUCTURE.md + skeleton main.py
    │
    ▼
Phase 4: asset-planner → ASSETS.md (sprite manifest with size, palette
                                     budget, what each represents)
    │
    ▼
Phase 5: asset-gen → images[N].set() implementations, inspect_sprite
                      after each sprite to verify identity
    │
    ▼
Phase 6: task-execution → implement gameplay/physics/scenes
                           validate_script → run_and_capture → iterate
    │
    ▼
Phase 7: test-harness → milestone assertion via inspect_state,
                         closed-loop input via play_and_capture
    │
    ▼
Phase 8: capture → screenshots/result/{N}/ proof bundle:
                    record_gameplay (full clear + full death),
                    capture_frames at key moments,
                    render_audio for each declared sound
    │
    ▼
Phase 9: quality-gate → final checklist; if any fail, return to
                         appropriate phase; PASS allows done declaration
```

Each phase is a separate markdown file. They're JIT-read — not in the
top-level `instructions.md`. This keeps context clean.

### Distribution: MCP Resources

Phase markdown files ship as MCP Resources:

- `pyxel://skills/visual-target`
- `pyxel://skills/decomposer`
- `pyxel://skills/scaffold`
- `pyxel://skills/asset-planner`
- `pyxel://skills/asset-gen`
- `pyxel://skills/task-execution`
- `pyxel://skills/test-harness`
- `pyxel://skills/capture`
- `pyxel://skills/quirks`
- `pyxel://skills/quality-gate`
- `pyxel://skills/pyxel-api` (existing — references Pyxel API)

The orchestrator in `instructions.md` tells the AI to read each
resource only when entering its phase.

### Persistent State Files

The AI maintains, at the project root:

| File | Created in phase | Purpose |
|------|------------------|---------|
| `REFERENCE.md` | visual-target | Vision anchor: palette, sprite list, layout, HUD, audio |
| `PLAN.md` | decomposer | Risk tasks, main build, verify criteria, win/lose milestones |
| `STRUCTURE.md` | scaffold | Architecture: classes, scene state machine, file layout |
| `ASSETS.md` | asset-planner | Sprite manifest with palette budgets and identity descriptions |
| `MEMORY.md` | task-execution | Discoveries, gotchas, what worked/didn't (cross-compaction memory) |

These are the AI's working state. The MCP doesn't manage them — the AI
maintains them via Read/Write tools. They survive compaction by being
on disk.

### One New MCP Tool: `quality_gate`

The only new tool. Composes existing tools per the gate criteria.

```
quality_gate(script_path) -> structured report
```

Behavior:

- Reads `PLAN.md` for declared milestones and verify criteria
- Reads `ASSETS.md` for sprite manifest
- Runs `validate_script`
- For each declared sprite: runs internal sprite-identity heuristics
  (silhouette boundedness, multi-region count, contrast against bg)
- Runs scripted milestone playthroughs (win path, lose path) and
  asserts state at each milestone via `inspect_state` equivalent
- For each declared sound: runs `render_audio`, asserts non-empty
- Verifies `screenshots/result/{N}/` bundle exists for current attempt
- Returns Tier 1 (Stability hard) / Tier 2 (Balance soft, 3/4 needed)
  / Tier 3 (Regression vs prior bundle) report
- Tier 1 FAIL → AI must return to relevant phase
- All Tier 1 PASS + ≥3/4 Tier 2 PASS → AI may declare done

The gate is the contract that prevents shortcuts. The orchestrator's
contract:

> Do not claim done until `quality_gate` returns "Overall: PASS".
> The result of `quality_gate` is the only authoritative signal of
> done; AI self-assessment does not count.

### Anti-Shortcut Rules in instructions.md

Borrowed from godogen patterns:

- **Visual primacy**: when code says X happened but capture shows Y,
  trust the capture
- **No procedural fallback**: rectangles/blobs in place of declared
  assets means asset-gen was skipped — go back
- **Bundle integrity**: `screenshots/result/{N}/video.gif` (or
  `record_gameplay` output) must show behavior across full duration,
  not just one good frame; static / looping / degenerating bundles fail
- **Bias toward failure**: if behavior is not clearly visible in
  capture, treat as not-done
- **Closed-loop input**: scripted playthrough reads observed state,
  steers toward next milestone — open-loop timed press/release fails
  due to drift

### What's NOT changing

- Existing tools (`run_and_capture`, `inspect_*`, `render_audio`,
  `play_and_capture`, `record_gameplay`) stay unchanged
- Pyxel as engine, Python as language, single-file `.py` outputs stay
- The MCP architecture (FastMCP + harnesses) stays
- Versioning stays conservative (this work targets `0.10.0`)

## Implementation Plan (revised)

1. **Phase skill markdown** — write 10 phase files in
   `src/pyxel_mcp/skills/` (new directory)
2. **Resource registration** — add `_resources/skills.py` exposing each
   phase markdown as `pyxel://skills/<name>`
3. **`quality_gate` tool** — new MCP tool composing existing ones,
   reads PLAN.md / ASSETS.md, returns tier report
4. **`instructions.md` rewrite** — orchestrator only:
   - Pipeline definition (phase order)
   - When to read each phase resource
   - Persistent state file contract
   - Anti-shortcut rules
   - Move existing quality content into the relevant phase files
5. **CHANGELOG, version 0.10.0** — describe the new harness model
6. **Validation: rebuild dkong using only the harness** — must end
   with `quality_gate: PASS`, user plays and confirms playable +
   recognizable

## Out of Scope for This Iteration

- Image-generation integration (godogen uses Gemini/Grok for
  reference.png; for Pyxel we use ASCII / palette-table descriptions
  in REFERENCE.md). Could be added later for AI-generated reference
  imagery converted to 16-color palette.
- Stop hook installation. godogen's stop hook is in Claude Code
  settings, not in the MCP server. We can document the recommended
  hook in instructions.md but cannot install it from the server side.
  Future: ship a hook config snippet under `_resources/`.
- Tripo3D / Grok video / Gemini integration. Not relevant for Pyxel
  16-color sprites; users author sprites via `pyxel.images[N].set()`.

## Success Criteria

The harness is successful if:

1. A subagent given only "make Donkey Kong" with this MCP cannot
   declare "done" until `quality_gate` returns PASS
2. `quality_gate` FAIL is informative enough that the agent
   self-corrects without human re-prompting
3. The previous dkong garbage outputs would FAIL the gate at
   verify_assets (single-blob), verify_physics (jump-fall-through),
   or verify_playthrough(win) (never reaches princess)
4. After harness-driven iteration, the same task produces a
   clearable, recognizable game in a single conversation
5. The user plays the result and confirms it's recognizable as
   the target genre + actually playable

## Risks

- **Spec authoring overhead** — REFERENCE.md and PLAN.md authoring
  takes context tokens before any code. Acceptable: it's the
  difference between garbage in 30s and a real game in 5min
- **AI may still skip phases**: harness rules are markdown, AI can
  technically ignore them. Mitigation: `quality_gate` requires
  artifacts (PLAN.md / ASSETS.md / screenshots/result/{N}/) to exist
  with proper structure. Missing artifact → tool returns FAIL with
  the specific missing piece. AI can't fake artifacts without
  filling them.
- **Bundle integrity check is heuristic**: detecting "frozen middle
  segment" requires per-frame state diff analysis. Initial version
  uses simple checks (file sizes, frame count, audio non-empty).

## Notes on Mimicking godogen

This design copies godogen's *structural patterns* (phase markdown +
persistent state + visual primacy + procedural-fallback prohibition +
proof bundle requirement). The actual content of phase markdown files
is written from scratch for Pyxel, not transplanted from godogen.

Specific patterns adopted:

| godogen pattern | Pyxel-mcp realization |
|-----------------|----------------------|
| `${GODOGEN_SKILL_DIR}/<phase>.md` | `pyxel://skills/<phase>` resource |
| `reference.png` from Gemini | `REFERENCE.md` ASCII / palette table |
| `PLAN.md` with risk tasks | Same name, same purpose, Pyxel risks |
| `screenshots/result/{N}/video.mp4` | `screenshots/result/{N}/video.gif` from `record_gameplay` |
| `dotnet build` + `godot --headless --import` | `validate_script` + run smoke test |
| SceneTree `TestT3.cs` with ASSERT PASS/FAIL | `play_and_capture` + `inspect_state` with milestone asserts |
| Telegram stop hook | (Future) Claude Code hook documented |
| "Placeholder primitives signal asset step skipped" | Same rule, applied to Pyxel rect-blob sprites |
