# Stage 2: Decomposer

Convert STRUCTURE.md "Vision" into a verifiable plan with risk isolation and milestone tables for the quality gate.

## Inputs

- `STRUCTURE.md` "Vision" subsection (from Stage 1).
- `ASSETS.md` "Art direction" (from Stage 1).
- The user's original brief.

## Output

`PLAN.md` at project root, with six sections in this order:

1. **Risk Tasks** — features that need isolation (omit entirely if no risks identified).
2. **Genre Identity** — 3–5 genre-defining rules with Verify predicates (`quality-gate.md` check #10).
3. **Main Build** — modules + cross-cutting verify criteria.
4. **Win Path Milestones** — input/assert table.
5. **Lose Path Milestones** — input/assert table.
6. **Audio Manifest** — restated from STRUCTURE.md "Vision → Audio" for downstream consumption.

(Asset Manifest is forward-referenced — Stage 4 fills `ASSETS.md` directly.)

## Pyxel-specific risk taxonomy

These features fail unpredictably and produce ambiguous bugs when mixed with other systems. Each becomes a Risk Task implemented in isolation first.

| Feature | Why risky |
|---------|-----------|
| Variable-jump physics | Tuning gravity vs. initial velocity hits "can't reach platform" or "skips platform above" |
| Sloped platform collision | Y has to follow `y = lerp(y0, y1, (x-x0)/(x1-x0))` while walking |
| Ladder snap + transition | Off-by-one on platform transition causes either fall-through or refusal-to-mount |
| Slope-aware moving hazard | Direction depends on slope sign; flip at edge or fall when running off; AI implementations frequently get the off-edge fall wrong |
| Multi-state animation transitions | walk → jump → land state machine with frame timing; easy to leave stuck-in-jump or flickering |

Anything *not* in this list is Main Build — implement directly, no isolation. Note: closed-loop input simulation, headless audio determinism, and image-bank init order are **harness concerns**, not game features — `test-harness.md` (Pattern C), `read_audio`, and `validate` (`assets_in_update`) cover them. Do not allocate Risk Tasks for them.

## Genre identity

A mostly green mechanics gate proves the game does not crash, has scenes,
reaches milestones, and has a non-empty background. It does NOT
prove the game is the genre the user asked for. A maze chase can still
be wrong if enemies do not pursue, a shooter can be wrong if bullets
are cosmetic, and a platformer can be wrong if jumps/collisions are not
meaningful.

The `## Genre Identity` section captures the genre-defining rules
that mechanic checks miss.

**The Verify line is a description of the agent's Python code, not a string for tool consumption.** The quality gate's check #10 evaluates each rule by having the agent (you) write a Python script that issues `run` calls, reads `result["snapshots"]`, and asserts predicates directly. There is no AST sandbox — use any Python you need (`abs`, `min`, `max`, list comprehensions, helper functions).

For the declared genre, list **3–5 mechanics that define the genre**.
Each gets a `Verify:` predicate testable via `run` snapshots.
`quality-gate.md` check #10 evaluates each; if PLAN.md lacks the
section or any predicate fails, the gate FAILs.

Example for a compact maze-chase game:

````markdown
## Genre Identity

### L1. Enemies reduce distance to the player when unobstructed.
- **Why genre-defining:** chase pressure is the core threat. If enemies
  wander randomly while the player stands still, the game is only a maze.
- **Verify:** run with no inputs for 90 frames, snapshot
  `player.x`, `player.y`, and `enemies[0].x/y` at frames 10, 50, 90.
  When line-of-sight is clear, Manhattan distance from enemy to player
  must decrease in at least two consecutive intervals.

### L2. Collectibles drive score and progression.
- **Why genre-defining:** the player needs a reason to enter risky spaces.
  If collectibles are decorative, the route has no objective.
- **Verify:** steer through the first collectible. Assert `score`
  increases, the collectible disappears from state, and the frame PNG no
  longer shows its sprite at the collected tile.

### L3. Contact with a hazard has immediate consequence.
- **Why genre-defining:** visible threats must matter. If contact has no
  state change, avoidance is unnecessary.
- **Verify:** run a lose-path segment where the player remains on the
  enemy route. Assert `lives` decreases or `scene == "GAME_OVER"` within
  the declared contact window.
````

If the genre's mechanics are unclear from the user brief, **ask the
user before continuing**. Do not guess and ship; this is the section
the gate cannot recover from automatically.

Genre identity rule starters worth considering:

- **Platformer:** do jumps, moving platforms, pickups, or power-ups
  affect traversal? Does jump height have a deliberate cap?
- **Shoot-em-up:** do bullets persist a finite distance, not
  forever? Do enemies spawn from off-screen, not in the player's
  lap?
- **Puzzle:** does the win condition require player input across
  N steps, or can a single key press solve it?
- **Racing / endless runner:** does the world scroll faster than
  the player can catch up? Are obstacles spaced for a reaction
  window of at least 12 frames at 30 FPS?
- **Beat-em-up:** is there a hit-stop / hitstun signature on
  successful hits? Are enemy AI states (idle / approach / attack)
  visibly distinct?

## Verify criteria — required structure

Every task gets a `Verify:` field with **specific, observable** criteria. "Looks right" is not a criterion. Each criterion names the tool that observes it and the predicate.

```
Verify (jump physics):
  - run with inputs [{frame:5, buttons:["KEY_SPACE"]},{frame:7, buttons:[]}],
    state snapshot at frames [30, 50]:
      frame 30: assert player.y < player_initial_y - 16
      frame 50: assert player.y == player_initial_y AND player.vy == 0

Verify (moving platform ride):
  - run with inputs holding KEY_RIGHT for 60 frames,
    state snapshot at frames [20, 40, 60]:
      for each: assert abs(player.y - platform_top_y(player.x) + player_h) < 2

Verify (hazard patrol collision):
  - run with no inputs while a patrol crosses the player spawn lane,
    state snapshot at frames [10, 20, 30, 40, 50, 60]:
      assert hazard.x changes monotonically along its lane
      assert lives decreases once collision boxes overlap
```

## Win Path Milestones table

```markdown
## Win Path Milestones

| Frame | Inputs (held until next row) | Asserts |
|-------|-----------------------------|---------|
| 30    | KEY_SPACE press (start)     | scene == "PLAY", player.x ≈ <start_x>, player.y ≈ <start_y> |
| 60    | KEY_RIGHT held              | player.x > <start_x> + 20 |
| 120   | KEY_RIGHT toward pickup     | player.x > <pickup_x> - 8 |
| 200   | KEY_RIGHT then KEY_UP       | score > 0, pickup_count decreased |
| ...   | ...                         | ... |
| 600   | KEY_RIGHT near goal         | player.x > <goal_x> - 8 |
| 660   | (no input)                  | scene == "WIN" |
```

Closed-loop note: the test harness reads observed values; if they don't match the planned trajectory within tolerance, the milestone FAILs. For paths longer than ~200 frames, the test harness will steer in segments (see `test-harness.md`).

**Frame numbers are guesses, not commitments.** Stage 2 produces best-effort milestone frames given the planned physics; in Stage 6 (task-execution) these are commonly off by 50-200 frames once the actual movement constants are tuned. Tightening a milestone in response to observed behaviour is fine — that is the closed-loop intent. Loosening one to dodge an otherwise-failing playthrough is Anti-shortcut rule #5 ("adjusting milestones to fit"); fix the game, not the spec. If the natural pace of the game falls outside any of the gate's bands (e.g. a survival game that genuinely takes 60 s to lose, well past the 10-14 s difficulty-floor band), record a contract override in PLAN.md alongside the rationale rather than gaming the milestone numbers.

## Lose Path Milestones table

```markdown
## Lose Path Milestones

| Frame | Inputs       | Asserts |
|-------|--------------|---------|
| 30    | KEY_SPACE    | scene == "PLAY", lives == 3 |
| 100   | (no input)   | at least one hazard is active and moving |
| 200   | (no input)   | hazard distance to player <= 16 |
| 240   | (no input)   | lives <= 2 (player got hit at least once) |
| 360   | (no input)   | lives == 0 |
| 420   | (no input)   | scene == "GAME_OVER" |
```

Standing still must lead to GAME_OVER within 10–14 seconds at the configured fps (≈ 300–420 frames at 30fps). Faster = unfair; slower = the lose path is poorly defined and won't reliably trigger. The quality gate enforces this window in stop condition #6 (Difficulty floor).

## Output template

````markdown
# PLAN: <Title>

## Risk Tasks

### R1. <feature>
- **Why isolated:** <one sentence — what makes this algorithmically hard>
- **Approach:** <algorithmic strategy or key constraints — enough for the implementor to know *how*, not just *what*>
- **Verify:** <bulleted observable checks per the structure above>
- **Status:** pending | in-progress | done

### R2. ...

(Omit the entire "Risk Tasks" section if no risks identified.)

## Genre Identity

### L1. <genre-defining mechanic>
- **Why genre-defining:** <one sentence — what would the game lose if this mechanic were absent?>
- **Verify:** <observable predicate evaluated via `run` snapshots — see the example earlier in this file>

### L2. ...

### L3. ...

(Required. At least 3 rules. The gate's check #10 evaluates each.)

## Main Build

### Modules
- <list each main file/class to be implemented and its responsibility>

### Verify (cross-cutting)
- Movement direction matches player input
- Animation direction matches movement direction
- Physics objects respond to gravity and collision
- UI readable, no overflow or overlap
- No missing-asset placeholder rectangles
- <game-specific checks>
- Win path scene transition fires
- Lose path scene transition fires

## Win Path Milestones
<table per format above>

## Lose Path Milestones
<table per format above>

## Audio Manifest
<from STRUCTURE.md "Vision → Audio", restated here for quality_gate consumption>
````

## Anti-patterns in this stage

- **Verify lines that say "looks right", "feels good", "matches reference"** — these cannot be automated and the gate cannot enforce them.
- **Milestones with no `inputs` column** — without scripted inputs there's no playthrough.
- **Lose path with no death trigger** — if hazards are too slow / random / cannot actually hit a stationary player, the lose path can't be verified.
- **Single milestone per path** — the gate needs intermediate milestones to detect early divergence (degenerate "first 30 frames look fine then static" bundles).
- **Risk tasks without `Approach`** — the implementor will hit the same risky pitfall the isolation was meant to catch.

## When this stage is done

- `PLAN.md` exists at project root with all six sections populated.
- Risk Tasks (if any) each have Why / Approach / Verify / Status.
- **Genre Identity** has at least 3 rules each with a Why / Verify predicate, evaluable via `run` snapshots.
- Main Build has at least one Module and at least the cross-cutting Verify list.
- Both Win Path and Lose Path tables have at least 5 rows including the start frame and the terminating-scene frame.
- Audio Manifest has one row per declared SE / BGM channel.
- Move to Stage 3 (read `scaffold.md`).
