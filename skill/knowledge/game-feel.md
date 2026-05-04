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

# Floaty / momentum (Mario-style)
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

### Ladder Mechanics

Climbing a ladder needs three things, in order:

1. **Engage / disengage tolerance.** When the player overlaps a ladder column AND presses UP/DOWN, switch to climb state. Don't require pixel-perfect alignment — a ±2 px tolerance on `x` against the ladder centre prevents "ladder ignored on the second-to-last pixel" frustration. Lock `x` to the ladder centre on engage so vertical movement stays straight.

2. **Snap-on-release at top / bottom.** When the player releases UP near the top of the ladder (i.e. the player's `y` is within `LADDER_SNAP_PX` of the upper girder), snap the player up onto the girder and exit climb state. Without this, releasing UP between the last climb pixel and the girder leaves the player stuck floating on the ladder, neither climbing nor walking. Same shape for DOWN release near the bottom.

```python
LADDER_SNAP_PX = 12   # tested at 30fps with CLIMB_SPEED=1; raise for faster climbs

if state == "CLIMB":
    if pyxel.btn(pyxel.KEY_UP):
        y -= CLIMB_SPEED
    elif pyxel.btn(pyxel.KEY_DOWN):
        y += CLIMB_SPEED
    elif pyxel.btnr(pyxel.KEY_UP):
        # Snap onto the girder ABOVE if close enough; else stay (keep climbing)
        upper = girder_above(y)
        if upper is not None and (y - upper.y) <= LADDER_SNAP_PX:
            y = upper.y
            state = "WALK"
    elif pyxel.btnr(pyxel.KEY_DOWN):
        lower = girder_below(y)
        if lower is not None and (lower.y - y) <= LADDER_SNAP_PX:
            y = lower.y
            state = "WALK"
```

3. **Jump must NOT bypass a girder upward.** If the genre is "ladders are the only floor-to-floor path" (DK-style), gate jump height: `JUMP_VEL` must be small enough that the apex stays below `GIRDER_PITCH_Y - PLAYER_H`. Otherwise quality-gate.md check #10 (genre identity L1) catches the regression.

### Camera (Side-Scroller)

```python
# Smooth follow (lerp)
camera_x += (player_x - camera_x - pyxel.width // 2) * 0.1
# 0.1 = smooth, 0.2 = responsive, 0.05 = cinematic
```

## Reference

- Animation timing is in `knowledge/patterns.md` "Animation Timing".
- Audio feedback (SE per event) is in `knowledge/audio.md` "Sound Effects Cookbook".
