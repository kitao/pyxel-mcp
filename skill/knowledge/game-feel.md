# Knowledge: Game Feel

Used by Stage 6 (task-execution).

## Visual Feedback

Every player-visible event needs visual and audio feedback:

| Event | Visual | Sound |
|-------|--------|-------|
| Hit/damage | `pal()` flash to white 2-3f | Descending (snd 2) |
| Collect item | Sparkle particles | Ascending (snd 1) |
| Destroy enemy | Expanding explosion | Noise burst (snd 3) |
| Clear/combo | Screen flash with `dither()` | Fanfare (snd 5) |
| Death | Sprite blink then fade | Game over (snd 4) |
| Land | Screen shake 1-2px | Impact noise (snd 8) |

```python
# Damage flash (in draw)
if self.hit_timer > 0:
    pyxel.pal(player_color, 7)  # flash white
# After drawing player:
    pyxel.pal()  # reset

# Simple explosion particles
class Particle:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.dx = pyxel.rndf(-2, 2)
        self.dy = pyxel.rndf(-2, 2)
        self.life = 10
    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.life -= 1
    def draw(self):
        if self.life > 0:
            pyxel.pset(int(self.x), int(self.y), 10 if self.life > 5 else 9)
```

### Screen Shake

```python
# Trigger: self.shake_mag, self.shake_dur = magnitude, frames
# In update():
if self.shake_dur > 0:
    ox = pyxel.rndi(-int(self.shake_mag), int(self.shake_mag))
    oy = pyxel.rndi(-int(self.shake_mag), int(self.shake_mag))
    self.shake_mag *= 0.7
    self.shake_dur -= 1
    pyxel.camera(ox, oy)
else:
    pyxel.camera()

# Magnitudes: dash/land 1-2px 2-3f | hit 2-3px 3-5f | explosion 3-5px 5-8f | boss 5-8px 10-15f
```

### Hitstop (Freeze Frames)

```python
# On impact: self.hitstop = 2  (light) or 4 (heavy)
# In update():
if self.hitstop > 0:
    self.hitstop -= 1
    return  # skip physics, keep drawing effects
```

## Game Feel Constants

Tested physics values. At 30fps, 1 frame = 33ms. At 60fps, 1 frame = 16ms. Pyxel defaults to 30fps. Values below are for 30fps unless noted.

### Platformer Physics

```python
# Tight / responsive (Celeste-style)
GRAVITY = 0.35
JUMP_VEL = -4.5
MAX_FALL = 3.5
WALK_SPEED = 1.5
RUN_SPEED = 2.5
ACCEL = 0.5           # frames to top speed: ~5
DECEL = 0.8           # frames to stop: ~2

# Floaty / momentum platformer
GRAVITY = 0.25
JUMP_VEL = -3.5
MAX_FALL = 3.0
WALK_SPEED = 1.0
RUN_SPEED = 2.0
ACCEL = 0.15          # frames to top speed: ~13
DECEL = 0.1           # frames to stop: ~20 (slippery)
```

### Variable Jump Height

```python
if on_ground and pyxel.btnp(pyxel.KEY_SPACE):
    vy = JUMP_VEL
    jump_hold = JUMP_HOLD_MAX  # e.g., 8

if pyxel.btn(pyxel.KEY_SPACE) and jump_hold > 0:
    vy += JUMP_HOLD_BOOST  # e.g., -0.25
    jump_hold -= 1

if pyxel.btnr(pyxel.KEY_SPACE):
    jump_hold = 0

vy = min(vy + GRAVITY, MAX_FALL)
```

### Forgiveness Mechanics (Critical)

```python
COYOTE_FRAMES = 3          # jump after leaving edge
JUMP_BUFFER_FRAMES = 4     # pre-land jump input

# Coyote time
if on_ground:
    coyote = COYOTE_FRAMES
else:
    coyote = max(0, coyote - 1)

can_jump = on_ground or coyote > 0

# Jump buffer
if pyxel.btnp(pyxel.KEY_SPACE):
    jump_buffer = JUMP_BUFFER_FRAMES

if jump_buffer > 0:
    jump_buffer -= 1
    if can_jump:
        vy = JUMP_VEL
        jump_buffer = 0
```

### Hitbox Design

- **Hazards**: hitbox **smaller** than sprite (forgiving)
- **Rewards/Stomp targets**: hitbox matches sprite (accurate)
- Player: use 60-75% of sprite size as hitbox (e.g., 6x6 for 8x8 sprite)
- `abs(a.x - b.x) < HIT_W and abs(a.y - b.y) < HIT_H`

### Variability Budget (human-playability design constants)

A game that only clears via one frame-perfect input sequence is a memorization puzzle, not gameplay. Quality gate #4b enforces ±3-frame jitter tolerance and #4c demands 2+ winning strategies; design under these constants:

| Design dimension | Constant | Why |
|---|---|---|
| Hazard reaction window | ≥ 15 frames @ 30fps | 500ms human reaction (~6 frames) + decision margin (~9 frames) |
| Adjacent-input spacing | ≥ 10 frames between any 2 required inputs | ±3 jitter on each → 6-frame collision risk; 10 frames keeps separation under jitter |
| Hazard spawn period | ≥ 30 frames @ 30fps (1s) for "constant pressure" hazards | Faster + sustained ⇒ hazards-in-flight count grows, multiplicative difficulty |
| Player invuln after hit | ≥ 30 frames | Without this, multiple hazards in flight chain-kill |
| Pickup reach window | ≥ 20 frames overlap with player path | Allows ±3 jitter on traversal timing without missing pickup |
| Multi-strategy paths | ≥ 2 viable winning paths | If only one specific timing clears, you've designed memorization, not gameplay |
| Boss fire / enemy spawn telegraph | visible for ≥ 15 frames before hazard activates | Player needs to see the warning to react |

**Math worked example.** A rolling hazard travels at 2 px/frame. The player's jump arc clears 24 px horizontally over 18 frames. So the **earliest** jump that clears the hazard must start when the hazard is ≥ 36 px away (18 frames × 2 px). At a 15-frame reaction window, the hazard must be visible to the player at distance ≥ 36 px + 15 frames × 2 px = 66 px. If your screen is 224 px wide and hazards spawn off-screen, that's `224/2 - 66 = 46` px of "decision space" between visible and must-jump. Tune so this is positive — a non-positive decision space means the player loses on every hazard they didn't pre-plan for.

**Pattern C is solvability proof, not playability proof.** Pattern C's cumulative-replay (rewind to frame 0 with adjusted inputs) finds the *one* clearing trajectory. The gate's #4b/#4c demand the trajectory survive jitter and admit alternatives — those approximate human reactive play. If Pattern C clears but #4b/#4c fail, the design has only a pinpoint clearance and is not human-playable; fix the design constants in this table, not the gate thresholds.

### Hazard Distribution (gate #4d)

If hazards spawn from the same column / one side / one path every time, the player only learns one dodge motion — the game is a memorization shortcut, not reactive play. Quality-gate #4d enforces hazards spread across ≥70% of usable playfield width with stddev ≥18% (no clustering).

**Avoid:**

```python
# Anti-pattern: every hazard spawns from the same x-position and moves right
if self.frame % HAZARD_PERIOD == 0:
    self.spawn_hazard(x=SPAWNER_X, vx=+HAZARD_SPEED)
```

The source is fixed; every hazard originates there; player learns one response. Clustered, fails #4d.

**Use one of these patterns:**

```python
# Pattern 1: multi-spawn point — rotate through left/center/right sources
SPAWN_POINTS = [40, 112, 184]  # left/center/right of usable width
if self.frame % HAZARD_PERIOD == 0:
    spawn_x = SPAWN_POINTS[(self.frame // HAZARD_PERIOD) % len(SPAWN_POINTS)]
    self.spawn_hazard(x=spawn_x, vx=+HAZARD_SPEED)
```

```python
# Pattern 2: deterministic-by-frame randomized spawn x within a visible source zone
import random
if self.frame % HAZARD_PERIOD == 0:
    rng = random.Random(self.frame)
    spawn_x = SOURCE_CENTER_X + rng.randint(-32, +32)
    self.spawn_hazard(x=spawn_x, vx=+HAZARD_SPEED)
```

```python
# Pattern 3: alternating direction — left-moving and right-moving hazards alternate
if self.frame % HAZARD_PERIOD == 0:
    n = self.frame // HAZARD_PERIOD
    if n % 2 == 0:
        self.spawn_hazard(x=USABLE_LEFT,  vx=+HAZARD_SPEED)
    else:
        self.spawn_hazard(x=USABLE_RIGHT, vx=-HAZARD_SPEED)
```

**Telegraph the distribution.** Player must be able to see / predict where the next hazard comes from (source marker faces the lane, warning flash, audio cue, etc.) so reaction is informed, not blind. A hazard that appears at random with no warning isn't reactive — it's a chance dice roll.

**Multi-strategy implication.** When you tune for #4c (≥2 distinct winning strategies), at least one strategy should naturally use the hazard distribution: e.g. Strategy A takes the long outer route with a pickup, Strategy B cuts through the center during telegraphed gaps. If hazards cluster on one side, only one strategy is viable — #4d FAIL is also a #4c FAIL trigger.

### Climb / Vertical-Route Mechanics

Any climbable route (rope, vine, elevator column, stairs-like lane) needs three things, in order:

1. **Engage / disengage tolerance.** When the player overlaps the route column AND presses UP/DOWN, switch to climb/ride state. Don't require pixel-perfect alignment — a ±2 px tolerance on `x` against the route centre prevents "ignored on the second-to-last pixel" frustration. Lock `x` to the route centre on engage so vertical movement stays straight.

2. **Snap-on-release at exits.** When the player releases UP/DOWN near an exit ledge or route endpoint, snap the player to the exit and return to normal movement. Without this, releasing between the last climb pixel and the exit leaves the player floating in neither state.

```python
ROUTE_SNAP_PX = 12   # tested at 30fps with CLIMB_SPEED=1; raise for faster climbs

if state == "CLIMB":
    if pyxel.btn(pyxel.KEY_UP):
        y -= CLIMB_SPEED
    elif pyxel.btn(pyxel.KEY_DOWN):
        y += CLIMB_SPEED
    elif pyxel.btnr(pyxel.KEY_UP):
        upper = route_exit_above(y)
        if upper is not None and (y - upper.y) <= ROUTE_SNAP_PX:
            y = upper.y
            state = "WALK"
    elif pyxel.btnr(pyxel.KEY_DOWN):
        lower = route_exit_below(y)
        if lower is not None and (lower.y - y) <= ROUTE_SNAP_PX:
            y = lower.y
            state = "WALK"
```

3. **Alternate movement must respect the route's role.** If the genre says this route is the only way to reach a layer, tune jump/dash/teleport values so they cannot bypass the route. Quality-gate.md check #10 should encode that genre identity rule explicitly.

### Camera (Side-Scroller)

```python
# Smooth follow (lerp)
camera_x += (player_x - camera_x - pyxel.width // 2) * 0.1
# 0.1 = smooth, 0.2 = responsive, 0.05 = cinematic
```

## Reference

- Animation timing is in `knowledge/patterns.md` "Animation Timing".
- Audio feedback (SE per event) is in `knowledge/audio.md` "Sound Effects Cookbook".
