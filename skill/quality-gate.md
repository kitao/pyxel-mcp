# Stage 7: Quality Gate

Final acceptance check. PASS gates "done"; FAIL routes back to the phase that owns the failed check. The gate is the contract that prevents shortcut "done" declarations.

## Inputs

- `PLAN.md` (Stage 2) — milestone tables, win/lose-path inputs and frames.
- `STRUCTURE.md` (Stage 3) — `FPS` constant (used to compute the difficulty-floor frame window).
- `ASSETS.md` (Stage 4) — sprite identity contract (`color_count` minimum, `fill_ratio` band, paired-frame entries) and audio manifest.
- `MEMORY.md` — gotchas accumulated across phases.
- `screenshots/result/<N>/` — proof bundle from `capture.md` (win-path.gif, lose-path.gif, frames/, audio/).
- `knowledge/pixel-art.md` — rationale for hierarchy 2/2 and contrast threshold.
- `knowledge/background.md` — rationale for H-balance ≥ 70% and quadrant density.
- `pyxel://run-snapshots-schema` (MCP resource) — snapshot field shapes the gate reads when parsing `run` results.

## Output

`screenshots/result/<N>/gate-report.json` — structured PASS/FAIL per check, with `fail_route` for any FAIL row. The gate-report.json is the single source of truth for "did this attempt pass?". Do not declare done without it. `<N>` is the same bundle counter `task-execution` and `capture.md` produced — the gate writes its report inside the existing bundle directory rather than creating a new one.

## Order of execution

Run checks in numeric order:

1. **Structural (#1–#3)** — cheap, fail-fast. Rules out wholesale missing artifacts before spending tokens on `run` calls.
2. **Asset (#4, #7–#9, #11)** — single tool calls per asset; cheap relative to playthroughs.
3. **Gameplay (#5, #6, #10)** — `run` calls of the full win/lose path with `inputs` + `state` snapshots. Most expensive.
4. **Bundle (#12)** — verify `capture.md` produced the deliverable.
5. **Scene visuals (#14, #15)** — short `run` calls with `screen_grid` snapshots at PLAY early/mid/late frames and at WIN/GAME_OVER entry+30. Cheap; they share the playthrough infrastructure but read pixel grids rather than state. #14 also calls `compare_frames` for the dead-time check.
6. **Genre identity (#16)** — `run` calls evaluating each PLAN.md `## Genre Identity` rule's Verify predicate. Comparable cost to #5/#6 since the predicates use `run` snapshots.
7. **Agent visual review (#17)** — agent (you) `Read`s each bundle frame PNG and verbalizes observations. Costs context tokens, not tool calls. Run last because it depends on the bundle (#12) and gives the agent's own multimodal judgment as the closing gate.

Stop and write gate-report.json with the FAIL even if later checks would have passed. Partial reports are valid input for routing — there is no benefit in running #5 and #6 when #2 or #3 has already failed.

## Stop conditions (flat list — all 17 must PASS)

| # | Check | How (concrete pyxel-mcp calls) | FAIL routes to |
|---|-------|--------------------------------|----------------|
| 1 | All four state files present | `os.path.exists` for `PLAN.md`, `STRUCTURE.md`, `ASSETS.md`, `MEMORY.md`; all non-empty | the owning phase (visual-design / spec / scaffolding / asset-planning) |
| 2 | Script validates | `validate(script="main.py")` returns `ok: True` (no syntax errors; anti-pattern warnings reviewed) | playthrough |
| 3 | Smoke run | `run(script="main.py", frames=30, snapshots=[{"frame": 29, "kind": "screen_image", "output": "tmp/smoke.png"}])` returns `exit_status="ok"` and the PNG is non-empty | scaffolding / playthrough |
| 4 | Asset identity | Per ASSETS.md entry: `inspect_image(script="main.py", image=0, x=, y=, w=, h=)` reports `verdict == "pass"` (which encodes `len(color_count) >= 3` AND `0.15 <= fill_ratio <= 0.95`); the underlying fields remain available as fallback documentation. For paired frames: `inspect_animation(script="main.py", image=0, x=, y=, w=, h=, region_count=2, direction=<"horizontal" or "vertical" per ASSETS.md bank layout>)` reports `region_diffs[0]["diff_ratio"]` in `0.05–0.50` | sprite-quality |
| 5 | Win path | `run(script="main.py", frames=<final_milestone+1>, random_seed=42, inputs=<PLAN.md win-path inputs>, snapshots=[{"frames": [<every milestone frame>], "kind": "state", "attrs": ["scene"] + <every attribute referenced in PLAN.md milestone Asserts column, e.g., "player.x", "lives", "score">}])` returns: keying snapshots with Pattern D, the snapshot at the final milestone has `values["scene"] == "WIN"`. **Optionally also passes if `result["assertions"]` contains `{"name": "win_path_complete", "passed": True}`** (Pattern B augmentation, only meaningful if the script writes the ASSERT line). The `random_seed` argument is mandatory — see Anti-shortcut rule #8 | playthrough or spec |
| 6 | Lose path | `run(script="main.py", frames=<final_milestone+1>, random_seed=42, inputs=[{"frame":30,"buttons":["KEY_SPACE"]},{"frame":32,"buttons":[]}], snapshots=[{"frames": [<every milestone frame>], "kind": "state", "attrs": ["lives", "scene"]}])` returns: snapshot at final milestone has `values["scene"] == "GAME_OVER"`. Optionally augmented by `result["assertions"]` containing a `lose_path_complete` PASS. The `random_seed` argument is mandatory — see Anti-shortcut rule #8 | playthrough or spec |
| 7 | Audio renders | Per audio manifest entry: `render_audio(script="main.py", target={"sound": N}, output_path=...)` returns `notes` non-empty and `peak_amplitude` ≥ the manifest's minimum threshold (manifest threshold lives in ASSETS.md audio table). Same with `target={"music": N}` for BGM | sprite-quality / scaffolding |
| 8 | Palette hierarchy | `inspect_palette(script="main.py")` returns `verdict in ("pass", "warn")` (which encodes `hierarchy.score == 2`); the underlying `hierarchy.score` field remains available as fallback documentation | asset-planning / sprite-quality |
| 9 | Contrast | `inspect_palette(script="main.py")` returns `verdict == "pass"` (which encodes `len(contrast_warnings) <= 1`); the underlying `contrast_warnings` list remains available as fallback documentation | asset-planning / sprite-quality |
| 10 | Difficulty floor | (mechanism unchanged — same 10-14s band) but: `game_over_frame` is now extracted by Pattern D — find the `state` snapshot whose `values["scene"]` first equals `"GAME_OVER"` and read its `frame`. If no such snapshot exists, FAIL | playthrough / spec |
| 11 | Layout balance | TITLE: `run(script="main.py", frames=60, snapshots=[{"frame": 30, "kind": "layout"}])` returns `snapshots[0]["h_balance"] ≥ 0.70`. (Frame 30 lets the TITLE blink prompt and any intro animation settle.) For text-less PLAY scenes, fall back to `{"frame": F, "kind": "screen_grid"}` and assert that no quadrant of the returned `grid` is empty | scaffolding |
| 12 | Proof bundle | `screenshots/result/<N>/` directory exists with `win-path.gif`, `lose-path.gif`, `frames/`, `audio/` — see `capture.md` | bundle |
| 13 | Tilemap trap clean | `inspect_tilemap(script="main.py", tilemap=N)` returns `trap_warning: False` for every tilemap declared in STRUCTURE.md. The trap fires when a tilemap uses tile `(0,0)` AND the source bank's `(0,0)` tile has visible content. Route to sprite-quality if the source-bank `(0,0)` is non-empty; route to scaffolding if the tilemap usage is wrong | sprite-quality / scaffolding |
| 14 | Background non-empty + no dead-time | (a) PLAY frame 119 (well after INTRO/transition) must show variety beyond a flat single-color void. `run(...)` with `screen_grid` snapshot at frame 119, then assert the returned `grid` contains at least 2 distinct dark-layer palette indices (default-palette bg = `{0,1,5}`; fall back to that set if `inspect_palette` was not run). The PLAY scene need not have a parallax skyline — but it must show texture, gradient, scaffolding pattern, etc. (b) PLAY scene must not stall mid-bundle. Capture three `screen_image` frames at PLAY early/mid/late within the win-path (e.g., frames 90, 240, 420), then call `compare_frames(frame_a=early, frame_b=mid)` and `compare_frames(frame_a=mid, frame_b=late)`. **Both pairs must return `identical: False` AND `ratio > 0.05`.** Identical PLAY frames mid-bundle indicates a dead-time signature (frozen entity, frozen camera, broken state) and is FAIL even if (a) passes. | scaffolding / asset-planning / playthrough |
| 15 | Scene transitions are visual | WIN and GAME_OVER scenes must contain at least one sprite blit (not just `pyxel.text` on `cls(0)`). `run(script="main.py", frames=<scene_entry_frame+30>, inputs=<inputs leading to WIN or GAME_OVER>, snapshots=[{"frame":<scene_entry_frame+30>,"kind":"screen_grid","bbox":[0,0,W,H]}])`, then assert the returned `grid` contains at least 5 distinct palette indices total (text alone on cls produces 2 — bg + text color; sprites add at least 3 more layers). Run for both WIN and GAME_OVER scenes; both must pass | scaffolding |
| 16 | Genre identity | PLAN.md must declare a `## Genre Identity` section with at least 3 rules specific to the declared game genre, each with a `Verify:` predicate testable via `run` snapshots (see `decomposer.md` for the section's required structure). The gate evaluates each predicate against a `run` result. Example for a Donkey-Kong-style platformer: "ladders are the only floor-to-floor path (jump cannot bypass a girder above by more than 1 floor height)", "hammer pickup grants temporary invincibility (sprite swap visible AND barrel collision is no-op for K frames)", "barrels respect girder slopes (barrel.x changes monotonically along the slope sign)". If PLAN.md lacks the section, FAIL routes to `spec`; if any Verify predicate fails, FAIL routes to `playthrough`. | spec / playthrough |
| 17 | Agent visual review | Read each `screenshots/result/<N>/frames/{title,play_start,mid_game,win,game_over}.png` with the `Read` tool. For each frame, write a 1–2 sentence agent-authored observation covering sprite identity (per ASSETS.md `represents:`), scene state (per the corresponding PLAN.md milestone), HUD content, animation state, and background. Record the observations in `gate-report.json["agent_review"]` keyed by frame name. Empty values, generic boilerplate ("looks fine", "scene shown"), or descriptions that contradict ASSETS.md `represents:` strings or PLAN.md milestone descriptions = FAIL. This is SKILL.md Anti-shortcut rule #9 enforcement — tool checks certify mechanics, agent verbalization certifies recognizability. See `capture.md` "Pre-handoff agent review" for the procedure. | playthrough / sprite-quality / scaffolding |

## Computing the difficulty-floor frame window (#10)

Read `FPS` from STRUCTURE.md (commonly `30` or `60`). Compute the band:

```python
fps = int(structure_constants["FPS"])
lo, hi = int(10 * fps), int(14 * fps)
# Find the first state snapshot whose scene == "GAME_OVER" (Pattern D scan):
state_snaps = [s for s in run_result["snapshots"] if s["kind"] == "state"]
game_over_frame = next(
    (s["frame"] for s in state_snaps if s["values"].get("scene") == "GAME_OVER"),
    None,
)
result = "PASS" if game_over_frame is not None and lo <= game_over_frame <= hi else "FAIL"
```

Below the band → unfair (the player has no time to react). Above → the lose-path schedule isn't reliably triggering GAME_OVER, which means hazards or collision logic are too soft. Both route the same way, but fix the underlying cause — do not widen the band.

## gate-report.json schema

One row per check. The gate writes this file regardless of PASS/FAIL — it is the artifact the user reviews when the gate concludes.

```json
{
  "attempt": 1,
  "fps": 30,
  "checks": [
    {"id": 1, "label": "State files", "result": "PASS", "evidence": "all 4 files present"},
    {"id": 2, "label": "Validate", "result": "PASS"},
    {"id": 3, "label": "Smoke run", "result": "PASS", "evidence": "frame 30 captured, no crash"},
    {"id": 4, "label": "Asset identity", "result": "PASS"},
    {"id": 5, "label": "Win path", "result": "FAIL", "evidence": "scene at frame 660 = PLAY (expected WIN)", "fail_route": "playthrough"},
    {"id": 6, "label": "Lose path", "result": "PASS"},
    {"id": 7, "label": "Audio renders", "result": "PASS"},
    {"id": 8, "label": "Palette hierarchy", "result": "PASS"},
    {"id": 9, "label": "Contrast", "result": "PASS"},
    {"id": 10, "label": "Difficulty floor", "result": "PASS", "evidence": "GAME_OVER at frame 372 (12.4s @ 30fps, in 10–14s band)"},
    {"id": 11, "label": "Layout balance", "result": "PASS", "evidence": "TITLE H-balance 81%"},
    {"id": 12, "label": "Proof bundle", "result": "PASS"},
    {"id": 13, "label": "Tilemap trap clean", "result": "PASS"},
    {"id": 14, "label": "Background non-empty + no dead-time", "result": "PASS", "evidence": "PLAY frame 119 grid has 4 distinct dark-layer indices; play_start vs mid_game ratio=0.31, mid_game vs late ratio=0.18"},
    {"id": 15, "label": "Scene transitions are visual", "result": "PASS", "evidence": "WIN frame N+30 grid: 7 distinct indices; GAME_OVER frame M+30 grid: 6 distinct indices"},
    {"id": 16, "label": "Genre identity", "result": "PASS", "evidence": "L1 (jump cannot bypass girder) passed; L2 (hammer invincibility) passed; L3 (barrel slope) passed"},
    {"id": 17, "label": "Agent visual review", "result": "PASS", "evidence": "5 frames Read; observations recorded in agent_review section"}
  ],
  "agent_review": {
    "title": "TITLE scene with the game name centered, 'PRESS SPACE' blinking below, no gameplay sprites visible",
    "play_start": "Mario in red cap and blue overalls at bottom-left girder; DK boss at top with scaffolding visible; princess and 'HELP!' text on top platform; HUD shows 1UP 0000 / HIGH 0000 / L=01",
    "mid_game": "Mario climbing ladder on girder 3; one barrel mid-air falling between girders 1 and 2; another rolling on girder 2; HUD shows score 0300, lives 3",
    "win": "Mario adjacent to princess on top platform; 'YOU WIN!' overlay text visible; HUD shows final score 8500",
    "game_over": "Mario sprite shows death frame at floor; 'GAME OVER' overlay text; HUD shows score 1200, lives 0"
  },
  "summary": {"pass": 16, "fail": 1, "total": 17}
}
```

The `fail_route` field is required on every FAIL row. PASS rows may omit `evidence` when the check is binary; FAIL rows must include enough evidence to act on.

## Anti-shortcut rules (restated for the agent at gate time)

These are the cheats the gate is built to catch. Read them before writing the gate-report.json:

1. **"It compiles and runs, looks fine"** — checks #2 and #3 only certify no-crash. They do not certify gameplay. Checks #5 and #6 are the gameplay certifications.
2. **"I added a sprite"** — without `inspect_image` matching the `represents` description from ASSETS.md, the sprite is unverified. Render, look, compare; check #4 enforces this.
3. **"Bundle exists"** — without playthrough completion (#5 and #6 PASS), the bundle could be a 30-frame loop with stale frames. Existence alone is not enough.
4. **"Audio plays"** — without `render_audio` returning `notes` non-empty AND `peak_amplitude` above the manifest threshold (#7), the slot may be empty or inaudible. A silent `play()` call passes #2 and #3 but fails #7.
5. **Adjusting milestones to fit** — *most important.* If the game can't reach WIN by the planned frame, fix the game, not the milestone. Backward edits to PLAN.md require re-running #5 and #6 from scratch. Loosening the spec to dodge a FAIL is the failure mode this gate exists to prevent.
6. **"`trap_warning: True` is a silent killer."** Tilemap (0,0) trap means every "empty" cell shows a sprite. The visual artifact is "stair-step pattern across empty space" — easy to miss in a small screenshot, fatal in a 256x256 tilemap. Check #13 catches it.
7. **No mid-attempt threshold relaxation.** If a check threshold is wrong, change it BEFORE a run begins, not during. CI for skill should reject diffs to quality-gate.md thresholds during an active validation attempt. Mid-run threshold changes are documented in `gate-report.json["threshold_overrides"]` and trigger automatic FAIL of the affected check unless the threshold is restored.
8. **No unseeded gate playthroughs.** Win/lose paths use `random_seed=42` unless PLAN.md declares an alternative. If a script reads `random_seed=None` and the gate runs unseeded (i.e., `result["seeded"] is False`), mark #5 / #6 FAIL with reason `"non-deterministic playthrough"` — even if the snapshot at the final milestone *happens* to satisfy the predicate this attempt, the next run may not. Determinism is a precondition for the gate, not an optimization.
9. **No bundle without honest agent review.** A 17/17 PASS gate-report.json with `agent_review` empty, boilerplate ("looks fine", "scene shown"), or contradicting ASSETS.md `represents:` strings is a contradiction in terms — check #17 should have FAILed. Fabricating observations to skip the review is the deepest form of the shortcut this gate exists to prevent: tool checks certify mechanics, agent verbalization certifies recognizability, and the harness needs both to certify "playable". The previous validation cycle taught the project that 15/15 mechanics PASS produced "100 中 5" gameplay because the agent never looked at a frame. Run the agent visual review honestly; if a frame is wrong, route to fix and re-run.

## What happens on FAIL

For each FAIL row in gate-report.json:

1. Route to the phase named in the row's `fail_route` field. The phase reads its own state files plus the FAIL evidence and decides what to change.
2. Apply the remediation (fix the bug, redraw the sprite, re-tune the difficulty, regenerate the bundle). Update `MEMORY.md` if the fix is non-obvious — future sessions will need it.
3. Bump the bundle counter `<N>` and produce a fresh `screenshots/result/<N>/` per `capture.md`. Stale bundles are not patched in place.
4. Re-run the gate from check #1. **Do not retry the gate without remediation** — re-running the same checks against the same artifacts produces the same gate-report.json.

If multiple checks FAIL, route to the earliest-stage owner first (e.g., #4 sprite-quality before #5 playthrough) — fixing upstream often resolves downstream failures. The gate is not a debugger; it tells you *which* phase owns the failure, not *what code* to change.

### Common FAIL patterns

- **#5 reaches PLAY but never WIN.** Win-trigger logic missing; route to playthrough.
- **#6 reaches PLAY and stays there past the lose-path window.** Collision/hazard logic too soft; route to playthrough.
- **#4 paired-frame diff < 5%.** Two frames are visually identical; route to sprite-quality to redraw one.
- **#10 lose path < 10s.** Hazards spawn too aggressively; route to playthrough to slow spawn rate.
- **#11 H-balance < 70% on TITLE.** Title text is left- or right-weighted; route to scaffolding to recenter.
- **#13 trap_warning True.** Source-bank (0,0) has visible pixels and the tilemap uses (0,0). Route to sprite-quality to clear source (0,0), or to scaffolding to remap empty tilemap cells to a different tile coord.

## When this gate PASSes

All 17 checks PASS in gate-report.json. Then:

- `PLAN.md` shows all milestone rows marked `done` with verified-by notes.
- `MEMORY.md` has any non-obvious gotchas captured for next session.
- The latest `screenshots/result/<N>/` bundle is the deliverable, and `screenshots/result/<N>/gate-report.json` proves the bundle was accepted.

Report to the user (concise; the bundle and gate-report.json carry the detail):

- **Bundle path** — `screenshots/result/<N>/`. The user opens the GIFs and WAVs from there.
- **One-line summary** of what was implemented (game title, win condition, lose condition).
- **Any caveats** — known limitations, out-of-scope items deferred to a later attempt, anything the gate did not check.

Then stop. Done. Do not start the next iteration speculatively; if the user wants polish or a new feature, they will say so.
