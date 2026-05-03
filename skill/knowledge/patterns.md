# Knowledge: Patterns

Used by Stage 3 (scaffold — scene state machine, title-screen recipe) and Stage 6 (task-execution — level/enemy archetypes, animation timing).

## Title Screen Design

A plain text title looks amateur. Good title screens include:

1. **Pixel art game name** — larger than regular text, styled
2. **Animated elements** — bouncing sprites, scrolling background
3. **Controls hint** — key bindings visible
4. **Blinking prompt** — "PRESS ENTER" toggled with `frame_count`

```python
def draw_title(self):
    # Animated sprite decoration
    for i in range(5):
        x = 20 + i * 28
        y = 20 + pyxel.sin(pyxel.frame_count * 3 + i * 72) * 3
        pyxel.blt(x, int(y), 0, i * 8, 0, 8, 8, colkey=0)
    # Game title (centered)
    t = "MY GAME"
    pyxel.text((pyxel.width - len(t) * 4) // 2, 48, t, 7)
    # Controls
    pyxel.text(40, 70, "ARROWS:MOVE  Z:JUMP", 13)
    # Blinking prompt
    if pyxel.frame_count % 40 < 28:
        t2 = "PRESS ENTER"
        pyxel.text((pyxel.width - len(t2) * 4) // 2, 100, t2, 10)
```

## Game Patterns

### Platformer

```python
# Gravity + jump (see Game Feel Constants for tuned variants)
GRAVITY = 0.35
JUMP_VEL = -4.5
vy = min(vy + GRAVITY, 3.5)  # terminal velocity
if on_ground and pyxel.btnp(pyxel.KEY_SPACE):
    vy = JUMP_VEL
y += vy

# Tilemap collision for solid ground
dx, dy = pyxel.tilemaps[0].collide(x, y, w, h, dx, dy, wall_tiles)
```

### Shooter (top-down / side-scroll)

```python
# Bullet management
if pyxel.btnp(pyxel.KEY_SPACE):
    bullets.append({"x": player_x, "y": player_y})
for b in list(bullets):
    b["y"] -= BULLET_SPEED
    if b["y"] < 0:
        bullets.remove(b)

# Enemy-bullet collision
for e in list(enemies):
    for b in list(bullets):
        if abs(e["x"] - b["x"]) < 8 and abs(e["y"] - b["y"]) < 8:
            enemies.remove(e)
            bullets.remove(b)
            break
```

### Scene Management

```python
# Simple state machine for title/game/gameover
SCENE_TITLE, SCENE_GAME, SCENE_GAMEOVER = 0, 1, 2
scene = SCENE_TITLE

def update(self):
    if self.scene == SCENE_TITLE:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.scene = SCENE_GAME
    elif self.scene == SCENE_GAME:
        self.update_game()
    elif self.scene == SCENE_GAMEOVER:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.scene = SCENE_TITLE

def draw(self):
    pyxel.cls(0)
    if self.scene == SCENE_TITLE:
        self.draw_title()   # see Title Screen Design
    elif self.scene == SCENE_GAME:
        self.draw_game()
    elif self.scene == SCENE_GAMEOVER:
        pyxel.text(60, 40, "GAME OVER", 8)
        t = f"SCORE: {self.score}"
        pyxel.text((pyxel.width - len(t) * 4) // 2, 55, t, 7)
        if pyxel.frame_count % 40 < 28:
            pyxel.text(44, 80, "PRESS ENTER", 13)
```

### Level Design

Never place platforms, enemies, or items randomly. Every placement serves a purpose.

**Zone-based structure** — divide the map into 3-5 zones with escalating challenge:

| Zone | Purpose | Elements |
|------|---------|----------|
| 1 (Start) | Teach mechanics safely | Wide platforms, 1 weak enemy, first item |
| 2 (Build) | Introduce combinations | Narrower gaps, 2 enemy types, vertical platforms |
| 3 (Challenge) | Test skill | Enemies on platforms, timed jumps, fewer items |
| 4 (Climax) | Peak difficulty | Multiple hazards at once, tight spacing |
| 5 (Reward) | Resolution | Boss or clear condition, generous items |

**Pacing rules:**
- After a hard section, add a brief safe zone (empty platform, health item)
- First enemy encounter should be solvable without jumping
- Candles/items near new mechanics hint at the correct approach
- Place checkpoints (candles/hearts) before difficult jumps, not after

**Enemy placement:**
- Ground enemies on flat ground (never floating in air)
- Flying enemies in open vertical space (not crammed in corridors)
- Never place enemies where the player spawns or lands from a required jump
- Pair enemies with terrain: skeleton patrols platform edges, bats guard gaps

### Enemy Design

Every enemy needs: a **behavior pattern**, **visual distinction** from the player, and at least **2 animation frames**.

| Pattern | Movement | Good For | Example |
|---------|----------|----------|---------|
| Patrol | Walk left/right, turn at edges | Ground enemies | Skeleton, Slime |
| Sine float | Sinusoidal Y + X orbit around base | Flying enemies | Bat, Ghost |
| Chase | Move toward player when in range | Aggressive enemies | Ghost, Dog |
| Stationary | Fixed position, fires projectiles | Turrets, traps | Cannon, Spike |
| Swoop | Hover, then dive at player | Air enemies | Eagle, Demon |

```python
# Patrol: turn at platform edges
e["x"] += e["vx"]
if not tile_solid(edge_x, below_y):  # no ground ahead
    e["vx"] = -e["vx"]              # reverse

# Chase: drift toward player within range
if abs(player_x - e["x"]) < 100:
    e["x"] += (player_x - e["x"]) * 0.01

# Sine float: orbit around base position (never use += for x/y)
e["x"] = e["base_x"] + pyxel.sin(pyxel.frame_count * 2) * 16
e["y"] = e["base_y"] + pyxel.sin(pyxel.frame_count * 4) * 12
```

## Animation Timing

Recommended sprite image counts for smooth animation (ideal targets; see Sprite Design Process for minimums):

| Animation | Sprite Images | Speed (game frames per image) |
|-----------|--------|-----------------------|
| Idle breathing | 2-4 | 20-30 |
| Walk cycle | 4-6 | 4-6 |
| Run cycle | 4-6 | 2-3 |
| Attack | 3-5 | 2-4 |
| Jump | 3-4 | 3-5 |
| Explosion | 4-8 | 3-4 |
| Coin spin | 4 | 5-8 |

```python
# Standard animation pattern
ANIM_FRAMES = 4
ANIM_SPEED = 5  # change sprite every 5 game frames
frame = pyxel.frame_count // ANIM_SPEED % ANIM_FRAMES
u = frame * SPRITE_W  # offset into sprite sheet
pyxel.blt(x, y, 0, u, v, SPRITE_W, SPRITE_H, colkey=0)
```

### State-Based Animator

For games with multiple character states (idle, walk, attack), use a state-machine animator instead of inline frame math:

```python
SPRITE_W, SPRITE_H = 8, 8  # adjust to match your sprite size

class Animator:
    ANIMS = {
        "idle":   {"u": 0,  "frames": 2, "speed": 20, "loop": True},
        "walk":   {"u": 16, "frames": 4, "speed": 5,  "loop": True},
        "attack": {"u": 48, "frames": 3, "speed": 4,  "loop": False},
        "jump":   {"u": 72, "frames": 2, "speed": 6,  "loop": False},
    }

    def __init__(self):
        self.state = "idle"
        self.tick = 0
        self.flip = False  # True = face left

    def set(self, state):
        if state != self.state:
            self.state = state
            self.tick = 0

    def update(self):
        anim = self.ANIMS[self.state]
        self.tick += 1
        if self.tick >= anim["frames"] * anim["speed"]:
            if anim["loop"]:
                self.tick = 0
            else:
                self.tick = anim["frames"] * anim["speed"] - 1

    def draw(self, x, y):
        anim = self.ANIMS[self.state]
        frame = self.tick // anim["speed"]
        u = anim["u"] + frame * SPRITE_W
        w = -SPRITE_W if self.flip else SPRITE_W
        pyxel.blt(x, y, 0, u, 0, w, SPRITE_H, colkey=0)
```

Usage: call `animator.set("walk")` on state change, `animator.update()` every frame, `animator.draw(x, y)` in draw. Set `animator.flip = True` to face left.
