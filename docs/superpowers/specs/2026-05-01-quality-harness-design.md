# Pyxel MCP Quality Harness Design

## Problem

The current pyxel-mcp (0.9.3) provides tools but no enforcement. AI using
the MCP can declare "done" while shipping unplayable garbage:

- Sprites that aren't recognizable as anything (single-blob shapes)
- Physics broken (jump-through-floor, no slope walking)
- Game flow broken (barrels never reach bottom, win never triggers)
- BGM/SE declared but never verified to actually play
- Verification = "I captured frame 30 and frame 200, looks fine"

Both my own dkong and a fresh subagent's dkong demonstrate this:
each looked superficially complete, neither was playable to clear.

The MCP must stop being a tool dump and become a **harness** in the
sense established by harness-engineering literature: an environment
that constrains the agent so quality cannot be shortcut.

## References

This design is anchored to existing solutions, not invented:

- **[godogen](https://github.com/htdt/godogen)** — autonomous Godot/Bevy
  game generation with frame-grounded self-repair. Proven that the
  Plan→Code→Asset-gen→Engine-run→Screenshot-capture→Visual-verify-and-repair
  loop produces working games when the AI is *prompted* to evaluate
  visible output, not code metrics.
- **[Harness Engineering for AI Coding Agents](https://www.augmentcode.com/guides/harness-engineering-ai-coding-agents)** —
  three-layer model (Constraint, Feedback, Quality Gate) with PEV
  (Plan-Execute-Verify) phase gates between transitions. Hard gates
  via "error" not "warn". No inline suppression.
- **[Quality Gates 3-tier](https://dev.to/yurukusa/why-your-ai-agent-needs-a-quality-gate-not-just-tests-42eo)** —
  Stability hard-gate, Balance-band soft-gate (4 sub-checks, need 3/4),
  Regression vs baseline. Externalized config thresholds.
- **[TITAN](https://arxiv.org/html/2509.22170v1)** — LLM-driven MMORPG
  testing. Symbolic state abstraction, action templates, multiple
  oracles (crash / stall / time monitor), Reflective Reasoning when
  progress stalls.
- **[Godot MCP Pro](https://github.com/youichi-uda/godot-mcp-pro)** —
  proves a 172-tool game-dev MCP organized around runtime analysis,
  input simulation, screenshot compare, assertion-driven testing is
  feasible and useful.

## Non-Goals

- Reproducing arcade ROMs verbatim. The harness ensures *playable
  faithful homages*, not byte-for-byte clones.
- Subjective "fun" judgment. Tier-2 balance band gives objective
  proxies; "is the dodge satisfying" remains a human call.
- Replacing existing tools. `inspect_*`, `render_audio`,
  `play_and_capture`, `record_gameplay` stay. The harness composes them.

## The Harness Architecture

### Phase Order (PEV applied to game dev)

```
PLAN ─→ BUILD ─→ VERIFY ─→ GATE ─→ DONE
        ↑          │        │
        └──────────┴────────┘
        (each FAIL bounces back to BUILD with actionable remediation)
```

Phase transitions are gated. The next phase refuses to start until
the current phase reports PASS.

### Phase 1: PLAN — `lock_game_spec`

**Tool:** `lock_game_spec(spec_json: str) -> str`

**Schema enforced:**

```json
{
  "title": "string",
  "genre": "string",
  "screen": {"w": 128..256, "h": 128..256},
  "physics": {
    "gravity": float,
    "jump_initial_vy": float,
    "max_fall_speed": float,
    "walk_speed": float,
    "climb_speed": float
  },
  "controls": {
    "left": "KEY_*", "right": "KEY_*",
    "up": "KEY_*", "down": "KEY_*",
    "jump": "KEY_*"
  },
  "layout": {
    "platforms": [{"name": "...", "y0": int, "y1": int, "x0": int, "x1": int}],
    "ladders": [{"x": int, "top_platform": "...", "bottom_platform": "..."}]
  },
  "win_condition": {
    "description": "...",
    "predicate": "player.y < 32 and abs(player.x - princess.x) < 16"
  },
  "lose_condition": {
    "description": "...",
    "predicate": "lives <= 0"
  },
  "assets": [
    {
      "name": "player_walk_1",
      "image_index": 0,
      "u": int, "v": int, "w": int, "h": int,
      "represents": "Mario walking, frame 1",
      "min_distinct_colors": 3,
      "must_have_outline": true
    },
    ...
  ],
  "audio": [
    {"sound_index": 10, "represents": "jump SE", "trigger": "on jump"},
    {"sound_index": 0, "represents": "BGM melody channel 0", "trigger": "looping during play"},
    ...
  ],
  "milestones_win": [
    {"frame": 60, "input_until_now": "...", "asserts": {"scene": "==PLAY"}},
    {"frame": 600, "asserts": {"player.y": "<32"}},
    {"frame": 700, "asserts": {"scene": "==WIN"}}
  ],
  "milestones_lose": [
    {"frame": 30, "asserts": {"lives": "==3"}},
    {"frame": 300, "asserts": {"lives": "==0"}},
    {"frame": 360, "asserts": {"scene": "==LOSE"}}
  ]
}
```

**Behavior:**
- Validates schema (missing required field → FAIL with field name)
- Persists to `.pyxel-mcp-spec.json` next to the script
- Returns spec_id (hash). Downstream tools take spec_id and refuse if
  the script's spec hash doesn't match (re-lock required if spec changes).

**Why required first:** without numeric layout/physics/milestones,
verification has nothing to assert against. Locking the spec also
forces the AI to commit to specific values before writing code.

### Phase 2: BUILD

No new tool. AI writes the script. Reference the locked spec for
constants. `validate_script` already exists for syntax/anti-patterns.

### Phase 3: VERIFY (the four gates)

#### 3a. `verify_assets(script_path) -> str`

For each asset declared in spec.assets:
- Capture pixels via existing sprite reading
- Run heuristic checks:
  - **Bounded silhouette**: pixels do not fill > 95% of bounding box
    (single-blob detection)
  - **Multi-region**: at least `min_distinct_colors` distinct colors
    used in non-transparent pixels
  - **Outline present**: if `must_have_outline`, perimeter pixels are
    color-distinct from interior majority color
  - **Animation diff** (for paired walk/run frames): adjacent frames
    must differ in 5-50% of pixels (else static or unrelated)

Report per asset: PASS / FAIL with specific failed check.

#### 3b. `verify_physics(script_path) -> str`

Run deterministic invariant scenarios (auto-derived from locked spec):

- **jump_lands**: at known platform, press jump; assert player returns
  to a platform y within 30 frames; vy returns to 0; no NaN/divergence
- **no_fall_through**: stand on each platform for 60 frames; assert y
  variance < 1px and player.y stays at platform top
- **slope_follow** (if any platform has y0 != y1): walk left/right,
  assert y interpolates linearly with x along slope
- **ladder_climb**: at each ladder x, press up; assert y decreases
  monotonically until reaching top platform
- **ladder_descend**: same with down
- **gravity_terminal**: drop from height; assert vy caps at
  `max_fall_speed`

Each scenario uses scripted `set_btn` schedules and reads
`inspect_state`-equivalent attributes. Report per scenario: PASS / FAIL
with measured values + expected.

#### 3c. `verify_playthrough(script_path, scenario: "win"|"lose") -> str`

- Read `milestones_win` or `milestones_lose` from locked spec
- Build input schedule from milestones (each milestone has
  `input_until_now` describing inputs leading up to it; harness
  concatenates)
- Run the script with input injection
- At each milestone frame, capture state (App attributes)
- Evaluate each `asserts` predicate; aggregate PASS/FAIL

TITAN-style monitors run concurrently:
- **Crash monitor**: subprocess returncode != 0 anywhere → FAIL
- **Stall monitor**: state hash unchanged for 60 frames despite input
  → FAIL with last-stable-state report
- **Time monitor**: any frame > 100ms execution → FAIL (perf bug)

#### 3d. `verify_audio(script_path) -> str`

For each entry in spec.audio:
- Run existing `render_audio` for the declared sound
- Assert duration > 0, peak > some minimum threshold
- For BGM channel-mapped sounds, assert at least one note
- For SE, assert non-empty render

### Phase 4: GATE — `quality_gate`

**Tool:** `quality_gate(script_path) -> str`

Runs all of the above in order. Composes a Tier 1/2/3 report:

- **Tier 1 (hard, must-pass)**: spec locked, validate_script clean,
  verify_assets PASS, verify_physics PASS, verify_playthrough(win) PASS,
  verify_playthrough(lose) PASS, verify_audio PASS, no crashes/stalls
- **Tier 2 (soft, 3/4 sub-checks)**:
  - `inspect_palette` hierarchy_score == 2/2
  - `inspect_palette` low_contrast_warnings == 0 (or ≤ 1 with waiver)
  - `inspect_layout` margin imbalance < 20% on intended-centered scenes
  - HUD coverage: at least one text element matches each of the
    declared HUD pieces in spec
- **Tier 3 (regression, optional)**: compare to last passing baseline
  saved alongside spec; warn if any metric regresses > 25%

Return value structure:

```
=== Quality Gate Report ===
Spec: <title> (locked at <time>)

Tier 1 (Stability — HARD):
  [PASS] spec locked
  [PASS] validate_script
  [FAIL] verify_assets — asset 'player_walk_1' FAIL: single-blob (one color region)
  [SKIP] verify_physics  (depends on assets)
  [SKIP] verify_playthrough(win)
  [SKIP] verify_playthrough(lose)
  [PASS] verify_audio

Tier 2 (Balance — SOFT):
  [SKIP] (Tier 1 not green)

Overall: FAIL — fix Tier 1 first. Remediation:
  - asset 'player_walk_1': sprite has only 1 color region. Pyxel sprites
    need at least 3 distinct colors (cap, face, body) to be recognizable.
    See Pixel Art Rules section in instructions.md.
```

**Critical rule:** the AI cannot tell the user "done" until
`quality_gate` reports `Overall: PASS` with all Tier 1 PASS and ≥3/4
Tier 2 PASS.

### Phase 5: instructions.md as Rules File

Restructured as an `always_apply` rules file (per the AGENTS.md
pattern). Content order:

1. **MANDATORY WORKFLOW** (top of file, can't miss):
   - lock_game_spec FIRST. No coding before spec lock.
   - Build referencing locked spec constants.
   - Run quality_gate. Address every FAIL.
   - "DONE" can only be claimed after quality_gate PASS.
2. **GATES** explanation (each phase's PASS criteria, remediation flow)
3. **NO SHORTCUTS**: explicit list of behaviors that fail review
   - "I captured a frame, looks fine" — not verification
   - "Sprite added" without verify_assets PASS — not done
   - "Game runs" without verify_playthrough(win) AND (lose) PASS — not done
4. Existing quality content (visual design, SE design, pixel rules,
   gen_bgm) reorganized as REFERENCE under each phase

The Quality Checklist section becomes redundant once gates exist; it
either gets pulled into the gate criteria themselves, or remains as
a glossary.

## Tool Surface Summary (new)

| Tool | Phase | Inputs | Output |
|------|-------|--------|--------|
| `lock_game_spec` | PLAN | spec_json | spec_id, validation report |
| `verify_assets` | VERIFY | script_path | per-asset PASS/FAIL with specifics |
| `verify_physics` | VERIFY | script_path | per-invariant PASS/FAIL |
| `verify_playthrough` | VERIFY | script_path, "win"\|"lose" | per-milestone PASS/FAIL + monitor signals |
| `verify_audio` | VERIFY | script_path | per-sound PASS/FAIL |
| `quality_gate` | GATE | script_path | tier-1/2/3 report, overall PASS/FAIL |

Six new tools. All are subprocess-driven over the existing harness
plumbing (`_common/subprocess.py` + new `_harnesses/` files).

## Implementation Plan

1. `_harnesses/playthrough.py` — combine input + state capture at
   milestone frames + monitor signals
2. `_harnesses/physics.py` — predefined invariant scenarios
3. `_harnesses/assets.py` — pixel reading for asset checks
4. `_common/spec.py` — spec schema, validation, persistence
5. `_tools/quality.py` — registers the six new tools
6. `instructions.md` — rewritten per Phase 5 above
7. Tests covering each tool with known-bad scripts (single-blob sprite,
   broken jump, missing milestone, etc.)
8. **Validation**: rebuild dkong using only the harness; iterate until
   `quality_gate` PASS; user plays and confirms

## Rollout

- Branch: `feat/quality-harness` (current worktree)
- New version: `0.10.0` (semver minor: substantive new functionality)
  — but not 1.0.0; "stable" claim still requires field validation
- CHANGELOG: explicit "introduces mandatory quality harness; behaviors
  that previously declared 'done' will now FAIL gate"

## Open Questions

- **Spec authoring overhead**: requiring a 30+ field spec before coding
  may feel heavy. Can the MCP provide a `propose_game_spec(genre)` tool
  that drafts a starter spec the AI can refine? (Yes — Phase 9 stretch.)
- **Subjective quality**: who defines "this sprite is recognizable"?
  Heuristic checks catch obvious garbage (single-blob) but not
  "looks like a person but a really bad one". Consider adding a
  separate-LLM-judge mode in a later phase.
- **Author intent vs gate strictness**: a deliberately abstract game
  may legitimately fail "must have outline" or "must have 3 colors".
  Spec-level waivers (`override_check: "must_have_outline = false"`)
  let intent override default heuristics.

## Success Criteria

The harness is successful if:

1. A subagent given only "make Donkey Kong" + this MCP cannot declare
   "done" until quality_gate PASS
2. quality_gate FAIL is informative enough that the agent self-corrects
3. The dkong I (or the subagent) made earlier would FAIL the gate at
   verify_assets (single-blob), verify_physics (jump-fall-through), or
   verify_playthrough(win) (never reaches princess)
4. After harness-driven iteration, the same task produces a clearable,
   recognizable game in a single conversation
