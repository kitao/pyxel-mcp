# Decomposer — PLAN.md authoring

**Phase 2.** Convert `REFERENCE.md` into a verifiable plan with risk
isolation and explicit milestones for `quality_gate`.

## Output

A single file `PLAN.md` at the project root. Two sections: Risk Tasks
(isolated proving grounds) and Main Build (everything else, with
verify criteria).

## Risk taxonomy for Pyxel games

These features fail unpredictably and produce ambiguous bugs when
mixed with other systems. Each one becomes a Risk Task implemented in
isolation first.

| Feature | Why risky |
|---------|-----------|
| Variable-jump physics | Tuning gravity vs. initial velocity hits "can't reach platform" or "skips platform above" |
| Sloped platform collision | Y-coordinate has to follow `y = lerp(y0, y1, (x-x0)/(x1-x0))` while walking |
| Ladder snap + transition | Off-by-one on platform transition causes either fall-through or refusal-to-mount |
| Object-on-tilted-girder rolling | Direction depends on slope sign; flip at edge or fall when running off; AI implementations frequently get the off-edge fall wrong (objects vanish or stick) |
| Multi-state animation transitions | walk→jump→land state machine with frame timing; easy to leave stuck-in-jump or flickering frames |
| Closed-loop input simulation | Open-loop key sequences drift over long playthroughs (200+ frames) |
| Headless audio determinism | Sounds defined but not heard in `render_audio` because timing slot wasn't populated before game loop start |
| Image bank initialization order | `pyxel.images[0].set()` must run before any `blt()`; AI sometimes puts sprite definitions inside `update()` |

Anything *not* in this list is Main Build — implement directly, no
isolation.

## Verify criteria — required structure

Every task gets a `Verify:` field with **specific, observable**
criteria. "Looks right" is not a criterion. Each criterion must name
the tool that observes it and the predicate.

Examples:

```
Verify (jump physics):
  - inspect_state at frame 30 (after btnp KEY_SPACE at frame 5):
      assert player.y < player_initial_y - 16  (rose at least 16px)
  - inspect_state at frame 50:
      assert player.y == player_initial_y     (returned to start)
      assert player.vy == 0                   (no NaN, no drift)

Verify (sloped girder walk):
  - play_and_capture inputs that hold KEY_RIGHT for 60 frames,
    capture inspect_state at frames 20, 40, 60:
      for each: assert abs(player.y - expected_slope_y(player.x)) < 2

Verify (ladder climb):
  - play_and_capture inputs hold KEY_UP at ladder x for 60 frames:
      inspect_state milestones every 10 frames:
        assert player.y monotonically decreases
        assert player.y reaches platform_above.y - player_h within 60f
```

## Milestone tables for `quality_gate`

PLAN.md must include two milestone tables — these are the input
sequences and assertions `quality_gate` runs to certify the win path
and lose path.

### Win path milestones

```markdown
## Win Path Milestones

| Frame | Inputs (held until next row) | Asserts |
|-------|-----------------------------|---------|
| 30    | KEY_SPACE press (start)     | scene == "PLAY", player.x ≈ <start_x>, player.y ≈ <start_y> |
| 60    | KEY_RIGHT held              | player.x > <start_x> + 20 |
| 120   | KEY_UP at ladder_a x        | player.y < <floor_y> - 8 |
| 200   | (continuing climb)          | player.y < <floor_y> - 32 |
| ...   | ...                         | ... |
| 600   | KEY_UP near princess         | player.y < 32 |
| 660   | (no input)                  | scene == "WIN" |
```

Closed-loop: AI may use observed state to choose next input, but the
table must be filled in advance with **expected** observations. The
test harness reads observed values; if they don't match the planned
trajectory within tolerance, the milestone FAILs.

### Lose path milestones

```markdown
## Lose Path Milestones

| Frame | Inputs       | Asserts |
|-------|--------------|---------|
| 30    | KEY_SPACE    | scene == "PLAY", lives == 3 |
| 100   | (no input)   | a barrel exists somewhere on a girder below the boss |
| 200   | (no input)   | barrel.y >= player.y - 8 (barrel close to floor) |
| 240   | (no input)   | lives <= 2 (player got hit at least once) |
| 360   | (no input)   | lives == 0 |
| 420   | (no input)   | scene == "GAME_OVER" |
```

Standing still must lead to GAME_OVER within ~14 seconds at 30 fps,
otherwise difficulty is too low (Tier 2 balance check).

## Output format

````markdown
# PLAN: <Title>

## Risk Tasks

### R1. <feature>
- Why isolated: <one sentence>
- Approach: <algorithmic strategy in 1-3 sentences>
- Verify: <bulleted observable checks per the structure above>
- Status: pending | in-progress | done

### R2. ...

## Main Build

### Modules
- <list each main file/class to be implemented and its responsibility>

### Verify (cross-cutting)
- <bulleted general criteria — controls respond, scene transitions
  fire, no missing-asset rectangles, etc.>

## Win Path Milestones
<table per format above>

## Lose Path Milestones
<table per format above>

## Audio Manifest
<from REFERENCE.md §6, restated here for quality_gate consumption>

## Asset Manifest
<reference to ASSETS.md, which asset-planner will fill>
````

## Anti-patterns in this phase

- Verify lines that say "looks right", "feels good", "matches
  reference". These cannot be automated and the gate cannot enforce
  them.
- Milestones with no `inputs` column. Without scripted inputs there's
  no playthrough.
- Lose path with no death trigger. If barrels are too slow / too
  random / can't actually hit a stationary player, lose path can't
  be verified.
- Single milestone per path. The gate needs intermediate milestones
  to detect early divergence (degenerate "first 30 frames look fine
  then static" bundles).
- Risk tasks listed but with no `Approach`. AI will implement and
  hit the same risky pitfall the isolation was meant to catch.

## When this phase is done

`PLAN.md` exists with risk tasks (each with verify criteria), main
build modules, win path milestones, lose path milestones, audio
manifest. Move to `scaffold` (read `pyxel://skills/scaffold`).
