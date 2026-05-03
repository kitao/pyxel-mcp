# Stage 7: Quality Gate

Final acceptance check. PASS gates "done"; FAIL routes back to the phase that owns the failed check. The gate is the contract that prevents shortcut "done" declarations.

In v1.0.0 the gate is split across two layers:

- **Layer 1 (`observe`)** — call `read_*`, `run`, `diff_frames`, etc. to capture raw observations.
- **Layer 2 (`judge`)** — pass each observation plus a contract dict (extracted from PLAN.md / ASSETS.md or omitted to use the module default) into `judge_*`. The verdict drives PASS / FAIL and produces a `fail_route` that names the phase to revisit.

Encoding the thresholds in `judge_*` instead of inline pseudo-code means the same numeric criterion is applied identically across attempts and across host harnesses. The gate's job is to assemble observations + contracts and write `gate-report.json`; the numerical judgment lives in the MCP server.

## Inputs

- `PLAN.md` (Stage 2) — milestone tables, win/lose-path inputs and frames, **and the `## Genre Identity` rules** (#16).
- `STRUCTURE.md` (Stage 3) — `FPS` constant (used to compute the difficulty-floor frame band).
- `ASSETS.md` (Stage 4) — sprite identity manifest (`min_distinct_colors`, `silhouette` band, paired-frame entries, `represents` strings) and audio manifest.
- `MEMORY.md` — gotchas accumulated across phases.
- `screenshots/result/<N>/` — proof bundle from `capture.md` (win-path.gif, lose-path.gif, frames/, audio/).
- `knowledge/pixel-art.md` — rationale for hierarchy 2/2 and contrast threshold.
- `knowledge/background.md` — rationale for H-balance ≥ 70% and quadrant density.
- `pyxel://run-snapshots-schema` (MCP resource) — snapshot field shapes the gate reads when assembling `judge_milestone` / `judge_layout` inputs.

## Output

`screenshots/result/<N>/gate-report.json` — structured PASS/FAIL per check with `fail_route` for any FAIL row. The gate-report.json is the single source of truth for "did this attempt pass?". Do not declare done without it. `<N>` is the bundle counter `task-execution` and `capture.md` produced — the gate writes its report inside the existing bundle directory rather than creating a new one.

## Order of execution

Run checks in numeric order:

1. **Structural (#1–#3)** — cheap, fail-fast. Rules out wholesale missing artifacts before spending tokens on `run` calls.
2. **Asset (#4, #7–#9, #11)** — single tool calls per asset; cheap relative to playthroughs.
3. **Gameplay (#5, #6, #10)** — `run` calls of the full win/lose path with `inputs` + `state` snapshots fed into `judge_milestone`. Most expensive.
4. **Bundle (#12)** — `judge_bundle` against the deliverable directory.
5. **Scene visuals (#14, #15)** — short `run` calls with `screen_grid` / `layout` snapshots; #14 also calls `diff_frames` for the dead-time check (now folded into `judge_bundle`'s default contract).
6. **Genre identity (#16)** — `run` calls evaluating each PLAN.md `## Genre Identity` rule via `judge_genre`. Comparable cost to #5/#6.
7. **Agent visual review (#17)** — agent (you) `Read`s each bundle frame PNG and verbalizes observations. Costs context tokens, not tool calls. Run last because it depends on the bundle (#12) and gives the agent's own multimodal judgment as the closing gate.

Stop and write gate-report.json with the FAIL even if later checks would have passed. Partial reports are valid input for routing — there is no benefit in running #5 and #6 when #2 or #3 has already failed.

## Stop conditions (flat list — all 17 must PASS)

| # | Check | Layer 1 observation | Layer 2 judge | Contract source | FAIL routes to |
|---|-------|---------------------|---------------|-----------------|----------------|
| 1 | State files | `os.path.exists` for `PLAN.md`, `STRUCTURE.md`, `ASSETS.md`, `MEMORY.md` (all non-empty) | (none — direct check) | the 4 file names | the owning phase (visual-design / spec / scaffolding / asset-planning) |
| 2 | Script validates | `validate(script="main.py")` | (none — `validate` is itself a checker) | (no contract) | playthrough |
| 3 | Smoke run | `run(script="main.py", frames=30, snapshots=[{"frame":29,"kind":"screen_image","output":"tmp/smoke.png"}])` returns `exit_status=="ok"` and the PNG is non-empty | (none — direct check on `exit_status` + file size > 0) | (no contract) | scaffolding / playthrough |
| 4 | Asset identity | Per ASSETS.md sprite entry: `read_image(...)` for the sprite region; for paired frames: `read_animation(...)` with `region_count=2` | `judge_sprite(image_obs, sprite_entry)` and `judge_animation(anim_obs, paired_entry)` per row | ASSETS.md sprite manifest (`min_distinct_colors`, `silhouette`, `diff_band`, `represents`) | sprite-quality |
| 5 | Win path | `run(script="main.py", frames=<final_milestone+1>, random_seed=42, inputs=<PLAN.md win inputs>, snapshots=[{"frames":[<every milestone>],"kind":"state","attrs":[<every attr referenced in PLAN.md milestone Asserts column>]}])` | `judge_milestone(run_result, win_path_milestones)` | PLAN.md Win Path Milestones table (`asserts: [{frame, kind:"state", predicate}, ...]`); `random_seed=42` is mandatory — see Anti-shortcut rule #8 | playthrough or spec |
| 6 | Lose path | `run(...)` with the lose-path inputs and `state` snapshots at every milestone | `judge_milestone(run_result, lose_path_milestones)` | PLAN.md Lose Path Milestones table | playthrough or spec |
| 7 | Audio renders | Per audio manifest entry: `read_audio(script="main.py", target={"sound": N}, output_path=...)`. **Always render against sound slots, not music slots** — `target={"music": N}` produces a WAV but no `notes` list, so `judge_audio` cannot verify it. Render BGM by walking the music slot's constituent sound IDs and rendering each as a sound. | `judge_audio(audio_obs, manifest_entry)` per slot | ASSETS.md Audio Manifest (`min_peak`, `min_notes`) | sprite-quality (empty slot) / scaffolding (under-spec) |
| 8 | Palette hierarchy | `read_palette` AND a runtime `screen_grid` snapshot (HUD / overlay colours are not visible to pre-loop palette inspection — see asset-planner.md). Build a merged observation: take `read_palette`'s result, replace its `used_indices` with the union of pre-loop indices and the runtime grid's indices. | `judge_palette(merged_obs)` — read `result["sub_verdicts"]["hierarchy"]` for this row | (default contract: `min_hierarchy_score=2`) | asset-planning / sprite-quality |
| 9 | Contrast | Same merged observation as #8 (no extra call) | `judge_palette(merged_obs)` — read `result["sub_verdicts"]["contrast"]` for this row | (default contract: `max_contrast_warnings=5`; band 6-9 = warn, ≥10 = fail) | asset-planning / sprite-quality |
| 10 | Difficulty floor | `run(...)` with the lose-path inputs and `state` snapshots tracking `scene` across the full lose window | `judge_milestone(run_result, difficulty_floor_contract)` where the contract's predicate is `scene == 'GAME_OVER' and lo <= frame <= hi` | PLAN.md + STRUCTURE.md `FPS` (band: `lo, hi = int(10*fps), int(14*fps)`) | playthrough / spec |
| 11 | Layout balance | TITLE: `run(script="main.py", frames=60, snapshots=[{"frame":30,"kind":"layout"}])` | `judge_layout(run_result)` | (default contract: `min_h_balance=0.70`, `min_quadrant_density=0.0001`) | scaffolding |
| 12 | Proof bundle | bundle dir at `screenshots/result/<N>/` | `judge_bundle({"bundle_dir": <path>}, bundle_contract)` | ASSETS.md audio manifest + frame coverage spec; `min_dead_time_diff=0.05` default | bundle |
| 13 | Tilemap trap clean | `read_tilemap(script="main.py", tilemap=N)` for every tilemap declared in STRUCTURE.md | (none — direct check on `trap_warning == False`) | (binary flag) | sprite-quality (source `(0,0)` non-empty) / scaffolding (tilemap usage wrong) |
| 14 | Background non-empty + no dead-time | (a) `run(...)` with `screen_grid` snapshot at PLAY frame 119; (b) bundle PNGs in `frames/` | (a) custom predicate: distinct dark-layer indices ≥ 2 (default-palette bg = `{0,1,5}`); (b) folded into `judge_bundle` (its dead-time check is the same `diff_frames` call this row used to do inline) | (a) `read_palette` colors + dark-layer set; (b) inherited from #12's `judge_bundle` | scaffolding / asset-planning / playthrough |
| 15 | Scene transitions are visual | WIN and GAME_OVER scenes: `run(...)` with `screen_grid` snapshot at `<scene_entry+30>` | (none — direct predicate: `len(set(grid_indices)) >= 5`) | min 5 distinct palette indices total | scaffolding |
| 16 | Genre identity | `run(...)` configured per PLAN.md `## Genre Identity` rules (each rule's Verify predicate names the snapshot scope) | `judge_genre(run_result, {"rules": [...]})` | PLAN.md `## Genre Identity` section (≥ 3 rules, each with `name` + `verify` predicate) | spec (rules absent) / playthrough (predicate fails) |
| 17 | Agent visual review | `Read` each `screenshots/result/<N>/frames/{title,play_start,mid_game,win,game_over}.png` | (none — agent verbalization, not a judge tool) | ASSETS.md `represents:` strings + PLAN.md milestone descriptions | playthrough / sprite-quality / scaffolding |

## judge_* call recipes

The Layer 2 calls in the table above all return:

```
{ok, verdict: "pass"|"warn"|"fail", evidence, fail_route, details}
```

Map the verdict to the gate-report row's `result` field:
- `pass` → `"PASS"`
- `warn` → `"PASS"` with `evidence` carried into the row (the user sees the warning but the gate does not block on it)
- `fail` → `"FAIL"` with the judge's `fail_route` copied into the row

For checks that have no Layer 2 (`#1, #2, #3, #13, #15, #17`), apply the binary check directly and synthesize the row inline.

## Building contract dicts from PLAN.md / ASSETS.md

Layer 2 judges are pure: they do not parse markdown. The agent extracts the contract dict from the spec files and passes it explicitly. Examples:

**ASSETS.md sprite entry → `judge_sprite` contract:**
```yaml
- name: mario_idle
  image: 0
  region: [0, 0, 16, 16]
  represents: "red-cap plumber, mid-stride"
  min_distinct_colors: 4
  silhouette: [0.20, 0.85]
```
becomes `{"min_distinct_colors": 4, "silhouette": [0.20, 0.85], "represents": "red-cap plumber, mid-stride"}` paired with `read_image(script="main.py", image=0, x=0, y=0, w=16, h=16)`.

**PLAN.md milestone table → `judge_milestone` contract:**
```
| frame | scene | asserts |
|-------|-------|---------|
| 60    | PLAY  | scene == "PLAY" and player.x > 10 |
| 300   | PLAY  | score >= 100 |
| 600   | WIN   | scene == "WIN" |
```
becomes
```python
{
    "asserts": [
        {"frame": 60, "kind": "state", "predicate": "scene == 'PLAY' and player.x > 10"},
        {"frame": 300, "kind": "state", "predicate": "score >= 100"},
        {"frame": 600, "kind": "state", "predicate": "scene == 'WIN'"},
    ],
}
```

> **Predicate sandbox constraints (judge_milestone / judge_genre)**
>
> Predicates must use comparisons (`==`, `<`, `>=`, `in`, ...), boolean
> ops (`and`, `or`, `not`), arithmetic (`+`, `-`, `*`, `/`, `//`, `%`),
> and attribute / subscript access only. **No function calls.** That
> means `abs(...)`, `len(...)`, `min(...)`, `max(...)`, `int(...)`, etc.
> all parse-fail.
>
> Workarounds:
> - "x within ε of target" — spell it out: `x >= 68 and x <= 76`
>   instead of `abs(x - 72) <= 4`.
> - "list size" — expose a derived attribute in `update()` rather than
>   computing it in the predicate: `self.n_barrels = len(self.barrels)`,
>   then read `n_barrels` in the predicate.
> - "min / max of two scalars" — use a comparison: `a if a < b else b`
>   isn't allowed either (no `IfExp` is — actually it IS, but for
>   clarity `min(a, b)` users should rewrite as `a < b and a or b`).
>
> Other guards: no dunder access (`__class__`, `__bases__`), no integer
> literals > 1,000,000, no exponentiation (`**`). Result must be exactly
> `bool` — `x.bit_length` (a method reference, no call) is rejected as
> "predicate must return bool" rather than silently truthy.

**PLAN.md `## Genre Identity` → `judge_genre` contract:**
```
## Genre Identity (Donkey-Kong-style platformer)

- L1 — gravity: jumping always returns to a girder. Verify: `'L1_GRAVITY' in assertions_passed`.
- L2 — barrel hazard: the lose path triggers GAME_OVER. Verify: `'lose_path_complete' in assertions_passed`.
- L3 — ladder traversal: Mario reaches each girder via a ladder. Verify: `'L3_LADDER' in assertions_passed`.
```
becomes `{"rules": [{"name": "L1 gravity", "verify": "'L1_GRAVITY' in assertions_passed"}, ...]}`.

The contract is data; the predicate is a string. The agent's job is to keep the spec files and the call sites in sync — the gate reads back what the spec promised.

## Computing the difficulty-floor frame window (#10)

Read `FPS` from STRUCTURE.md (commonly `30` or `60`). Build the predicate:

```python
fps = int(structure_constants["FPS"])
lo, hi = int(10 * fps), int(14 * fps)
contract = {
    "asserts": [
        {"frame": <some_late_frame>, "kind": "state",
         "predicate": f"scene == 'GAME_OVER'"},
    ],
}
verdict = judge_milestone(run_result, contract)
# Then locate the actual GAME_OVER frame from run_result.snapshots and assert lo <= frame <= hi.
```

Below the band → unfair (the player has no time to react). Above → the lose-path schedule isn't reliably triggering GAME_OVER, which means hazards or collision logic are too soft. Both route the same way, but fix the underlying cause — do not widen the band.

**Genre exception.** Some genres genuinely have a different time-to-lose: a survival game whose intended round length is 60 s, or a one-screen puzzle where the lose state is reached in 3-4 s. The default 10-14 s band is calibrated for action / platformer / shooter, not for those edge cases. If your game's design specifies a different time floor, declare it explicitly in PLAN.md alongside the lose-path table:

```markdown
## Difficulty floor override

This game is a survival round. Default 10-14 s band does not apply. Override:
- Acceptable lose-path duration: 50-70 s (1500-2100 frames at 30 fps)
- Rationale: the round is timed at 60 s by spec; <50 s indicates oversteer.
```

Then the gate's #10 evaluator reads the override band from PLAN.md instead of the FPS-derived default. Anti-shortcut rule #5 still applies: an override locks before the run begins, not after a failing run.

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
    {"id": 4, "label": "Asset identity", "result": "PASS", "evidence": "judge_sprite + judge_animation per ASSETS.md row all pass"},
    {"id": 5, "label": "Win path", "result": "FAIL", "evidence": "judge_milestone: 1 of 4 asserts failed at frame 660 (scene=='PLAY' expected 'WIN')", "fail_route": "playthrough"},
    {"id": 6, "label": "Lose path", "result": "PASS"},
    {"id": 7, "label": "Audio renders", "result": "PASS"},
    {"id": 8, "label": "Palette hierarchy", "result": "PASS"},
    {"id": 9, "label": "Contrast", "result": "PASS"},
    {"id": 10, "label": "Difficulty floor", "result": "PASS", "evidence": "GAME_OVER at frame 372 (12.4s @ 30fps, in 10–14s band)"},
    {"id": 11, "label": "Layout balance", "result": "PASS", "evidence": "judge_layout: TITLE H-balance 0.81"},
    {"id": 12, "label": "Proof bundle", "result": "PASS", "evidence": "judge_bundle: 12 frames, dead-time diff 0.18"},
    {"id": 13, "label": "Tilemap trap clean", "result": "PASS"},
    {"id": 14, "label": "Background non-empty + no dead-time", "result": "PASS", "evidence": "PLAY frame 119 grid has 4 distinct dark-layer indices; bundle dead-time diff 0.18"},
    {"id": 15, "label": "Scene transitions are visual", "result": "PASS", "evidence": "WIN frame N+30 grid: 7 distinct indices; GAME_OVER frame M+30 grid: 6 distinct indices"},
    {"id": 16, "label": "Genre identity", "result": "PASS", "evidence": "judge_genre: 3 of 3 rules passed"},
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

The `fail_route` field is required on every FAIL row — copy it from the judge tool's return value. PASS rows may omit `evidence` when the check is binary; FAIL rows must include enough evidence to act on (typically the judge's `evidence` string verbatim).

## Anti-shortcut rules (restated for the agent at gate time)

These are the cheats the gate is built to catch. Read them before writing the gate-report.json:

1. **"It compiles and runs, looks fine"** — checks #2 and #3 only certify no-crash. They do not certify gameplay. Checks #5 and #6 (with `judge_milestone`) are the gameplay certifications.
2. **"I added a sprite"** — without `read_image` + `judge_sprite` matching the `represents` description from ASSETS.md, the sprite is unverified. Render, look, judge; check #4 enforces this.
3. **"Bundle exists"** — `judge_bundle` certifies completeness AND dead-time absence; existence alone is not enough. Without #5 / #6 PASS the bundle could be a 30-frame loop with stale frames.
4. **"Audio plays"** — without `read_audio` + `judge_audio` returning `verdict == "pass"` (#7), the slot may be empty or inaudible. A silent `play()` call passes #2 and #3 but fails #7.
5. **Adjusting milestones to fit** — *most important.* If the game can't reach WIN by the planned frame, fix the game, not the milestone. Backward edits to PLAN.md require re-running #5 and #6 from scratch. Loosening the spec to dodge a FAIL is the failure mode this gate exists to prevent.
6. **"`trap_warning: True` is a silent killer."** Tilemap (0,0) trap means every "empty" cell shows a sprite. The visual artifact is "stair-step pattern across empty space" — easy to miss in a small screenshot, fatal in a 256x256 tilemap. Check #13 catches it.
7. **No mid-attempt threshold relaxation.** If a `judge_*` contract threshold is wrong, change it BEFORE a run begins, not during. Mid-run contract changes are documented in `gate-report.json["contract_overrides"]` and trigger automatic FAIL of the affected check unless the contract is restored.
8. **No unseeded gate playthroughs.** Win/lose paths use `random_seed=42` unless PLAN.md declares an alternative. If a script reads `random_seed=None` and the gate runs unseeded (i.e., `result["seeded"] is False`), mark #5 / #6 FAIL with reason `"non-deterministic playthrough"` — even if `judge_milestone` happens to pass this attempt, the next run may not. Determinism is a precondition for the gate, not an optimization.
9. **No bundle without honest agent review.** A 17/17 PASS gate-report.json with `agent_review` empty, boilerplate ("looks fine", "scene shown"), or contradicting ASSETS.md `represents:` strings is a contradiction in terms — check #17 should have FAILed. Fabricating observations to skip the review is the deepest form of the shortcut this gate exists to prevent: tool checks (`judge_*`) certify mechanics, agent verbalization certifies recognizability, and the harness needs both to certify "playable". Run the agent visual review honestly; if a frame is wrong, route to fix and re-run.

## What happens on FAIL

For each FAIL row in gate-report.json:

1. Route to the phase named in the row's `fail_route` field (copied from the judge tool's `fail_route`). The phase reads its own state files plus the FAIL evidence and decides what to change.
2. Apply the remediation (fix the bug, redraw the sprite, re-tune the difficulty, regenerate the bundle). Update `MEMORY.md` if the fix is non-obvious — future sessions will need it.
3. Bump the bundle counter `<N>` and produce a fresh `screenshots/result/<N>/` per `capture.md`. Stale bundles are not patched in place.
4. Re-run the gate from check #1. **Do not retry the gate without remediation** — re-running the same checks against the same artifacts produces the same gate-report.json.

If multiple checks FAIL, route to the earliest-stage owner first (e.g., #4 sprite-quality before #5 playthrough) — fixing upstream often resolves downstream failures. The gate is not a debugger; it tells you *which* phase owns the failure, not *what code* to change.

### Common FAIL patterns

- **#5 reaches PLAY but never WIN.** `judge_milestone` returns the failing assert; win-trigger logic missing → playthrough.
- **#6 reaches PLAY and stays there past the lose-path window.** Collision/hazard logic too soft → playthrough.
- **#4 paired-frame `judge_animation` fail (`diff_ratios` outside band).** Two frames are visually identical or wildly different → sprite-quality.
- **#10 `judge_milestone` shows GAME_OVER frame outside the FPS band.** Hazards spawn too aggressively or too gently → playthrough.
- **#11 `judge_layout` h_balance < 0.70 on TITLE.** Title text is left- or right-weighted → scaffolding to recenter.
- **#12 `judge_bundle` dead-time diff < 0.05.** Mid-bundle frames identical (frozen entity / frozen camera) → playthrough; or missing audio file → re-run capture.
- **#13 `trap_warning: True`.** Source-bank `(0,0)` has visible pixels and the tilemap uses `(0,0)` → sprite-quality (clear source) or scaffolding (remap empty cells).

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
