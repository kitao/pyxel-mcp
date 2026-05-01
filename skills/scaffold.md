# Scaffold — STRUCTURE.md and skeleton main.py

**Phase 3.** Lock the architecture before writing gameplay logic.
Output: `STRUCTURE.md` (architecture reference) + a runnable
skeleton `main.py` (no gameplay yet, just scenes/transitions).

## Architecture contract

Every Pyxel game has the same outer shape:

```python
class App:
    def __init__(self):
        pyxel.init(W, H, title=TITLE, fps=FPS)
        self._build_assets()      # populate images / sounds before loop
        self._reset()
        pyxel.run(self.update, self.draw)

    def _build_assets(self): ...  # images[N].set(), sounds[N].set/mml()
    def _reset(self): ...         # initial state for TITLE scene
    def update(self): ...         # scene dispatch
    def draw(self):  ...          # scene dispatch

App()
```

Scenes go through a finite state machine. Minimal arcade game has 4:

```
TITLE  -- press_start -->  PLAY  -- die -->  GAME_OVER  -- press_start --> TITLE
                            PLAY  -- win -->  WIN        -- press_start --> TITLE
```

Some games add INTRO ("HOW HIGH CAN YOU GET?") between TITLE and PLAY.

## STRUCTURE.md required content

```markdown
# Architecture

## Module list (single-file game = single module)

- `main.py`
  - `App` class — entry point, scene dispatch, asset build
  - `Player` class — physics, animation state, draw
  - `Barrel` class (or whatever the hazard is)
  - `Boss` class (if applicable, simple state machine for spawn timer)
  - module-level constants: `W, H, FPS, GRAVITY, JUMP_VY, ...`
  - module-level layout: `PLATFORMS = [...]`, `LADDERS = [...]`

## Scene state machine

| State | Entry | Exit transitions |
|-------|-------|-----------------|
| TITLE | initial | btnp(SPACE) → PLAY (or INTRO) |
| INTRO | from TITLE | timer expiry → PLAY |
| PLAY  | from INTRO/TITLE | lives==0 → GAME_OVER; win predicate → WIN |
| WIN   | from PLAY | btnp(SPACE) after delay → TITLE |
| GAME_OVER | from PLAY | btnp(SPACE) after delay → TITLE |

## Constants from PLAN.md / REFERENCE.md

```python
W, H = 224, 256
FPS = 30
GRAVITY = 0.4
JUMP_VY = -3.6
WALK_SPEED = 1.0
CLIMB_SPEED = 1.0
MAX_FALL_SPEED = 6.0
TITLE, INTRO, PLAY, WIN, GAME_OVER = 0, 1, 2, 3, 4
```

These are committed values. Changing them invalidates milestones in
PLAN.md — re-lock the plan if physics constants shift.

## Update / draw dispatch shape

```python
def update(self):
    self.frame += 1
    if pyxel.btnp(pyxel.KEY_Q):
        pyxel.quit()
    s = self.scene
    if s == TITLE: self._update_title()
    elif s == INTRO: self._update_intro()
    elif s == PLAY: self._update_play()
    elif s == WIN: self._update_win()
    elif s == GAME_OVER: self._update_gameover()

def draw(self):
    pyxel.cls(BG)
    s = self.scene
    if s == TITLE: self._draw_title()
    elif s == INTRO: self._draw_intro()
    elif s == PLAY: self._draw_play()
    elif s == WIN: self._draw_win()
    elif s == GAME_OVER: self._draw_gameover()
```

## State persistence between scenes

The `App` instance owns:
- score, hi_score
- lives
- current_level
- player (instance recreated on level start)
- barrels list (cleared on level start, on death)
- frame counter (monotonic, used for animation timing)
```

## Skeleton main.py

The skeleton must run cleanly with no gameplay. Verify with:
- `validate_script <path>` — clean
- `run_and_capture <path> --frames=30` — TITLE screen captures (text
  visible, blink prompt working, BG color matches REFERENCE)

Skeleton produces a TITLE screen with a placeholder background and
"PRESS SPACE" prompt. Scenes stub out without gameplay logic. Asset
build is empty (assets come in asset-gen phase). Sounds are empty.

## Anti-patterns in this phase

- Putting gameplay code in scaffold. The skeleton must be empty of
  gameplay; verifying scaffold means verifying scene transitions and
  scene rendering, not whether Mario can jump.
- Embedding magic numbers in update/draw without lifting them to
  module-level constants. The decomposer's milestone tables reference
  constants by name; inlined numbers can't be cross-checked.
- Coupling scene update with rendering. Update reads input and changes
  state; draw reads state and renders. Mixed concerns make scene
  transitions hard to verify.

## When this phase is done

`STRUCTURE.md` written. `main.py` runs and shows TITLE without
errors. Move to `asset-planner` (read `pyxel://skills/asset-planner`).
