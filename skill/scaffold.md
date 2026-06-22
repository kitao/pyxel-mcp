# Stage 3: Scaffold

Lock the architecture before writing gameplay logic. Output: STRUCTURE.md filled in completely (modules, scene state machine, tuning constants — Vision is already there from Stage 1) plus a runnable skeleton `main.py` and a `.pyxel-skill/` project marker.

## Inputs

- `PLAN.md` (from Stage 2): module list, win/lose conditions.
- `STRUCTURE.md` "Vision" (from Stage 1): window contract, palette plan, scene transitions.
- `knowledge/background.md` (screen size derivation, text layout).
- `knowledge/patterns.md` (scene state-machine template, title-screen recipe).
- `knowledge/audio.md` (channel allocation only — SE definitions come in Stage 5/6).

## Outputs

1. **`STRUCTURE.md`** — append the architectural sections below the existing `## Vision` section.
2. **`main.py`** — runnable skeleton at project root.
3. **`.pyxel-skill/`** — directory at project root containing `stage-marker` (text file with the current stage name) and `gate-snapshots/` (empty subdirectory). The Stop hook (`hooks/stop_check_bundle.py`) detects projects by the presence of this directory.

## Architecture contract

Every Pyxel game has the same outer shape:

```python
class App:
    def __init__(self):
        pyxel.init(W, H, title=TITLE, fps=FPS)
        self._build_assets()      # populate images / sounds before loop
        self._reset()
        pyxel.run(self.update, self.draw)

    def _build_assets(self): ...  # images[N].set, sounds[N].set/mml
    def _reset(self): ...         # initial state for TITLE scene
    def update(self): ...         # scene dispatch
    def draw(self):  ...          # scene dispatch

App()
```

Scenes go through a finite state machine. Minimal arcade game has 4–5:

```
TITLE  -- press_start -->  PLAY  -- die -->  GAME_OVER  -- press_start --> TITLE
                            PLAY  -- win -->  WIN        -- press_start --> TITLE
```

Some games add INTRO (short goal or wave preview) between TITLE and PLAY.

## STRUCTURE.md sections to add

After the existing `## Vision` section, append:

```markdown
## Modules

- `main.py`
  - `App` class — entry point, scene dispatch, asset build.
  - `Player` class — physics, animation state, draw.
  - `<Hazard>` class (project-specific obstacle) — pattern + draw.
  - `<Boss>` class (if applicable) — simple state machine for spawn timer.
  - module-level constants (see Tuning).
  - module-level layout (`WALLS`, `ROUTES`, `HAZARD_ZONES`).

## Scene state machine

| State | Entry | Exit transitions |
|-------|-------|-----------------|
| TITLE | initial | btnp(SPACE) → PLAY (or INTRO) |
| INTRO | from TITLE | timer expiry → PLAY |
| PLAY  | from INTRO/TITLE | lives == 0 → GAME_OVER; win predicate → WIN |
| WIN   | from PLAY | btnp(SPACE) after delay → TITLE |
| GAME_OVER | from PLAY | btnp(SPACE) after delay → TITLE |

## Tuning (constants from PLAN.md / Vision)

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

These are committed values. Changing them invalidates milestones in PLAN.md — re-lock the plan if physics constants shift.

## State persistence between scenes

The `App` instance owns:
- score, hi_score
- lives
- current_level
- player (instance recreated on level start)
- hazards list (cleared on level start, on death)
- frame counter (monotonic, used for animation timing)

## Verification

- `validate(script="main.py")` — clean.
- `run(script="main.py", frames=30, snapshots=[{"frame": 29, "kind": "screen_image", "output": "tmp/scaffold-smoke.png"}])` — TITLE scene captures (text visible, blink prompt working, BG color matches Vision).
```

## Skeleton `main.py` shape

```python
import pyxel

W, H = 224, 256
FPS = 30
TITLE_SCENE, INTRO, PLAY, WIN, GAME_OVER = 0, 1, 2, 3, 4
BG = 0  # black; replace with Vision-specified value

class App:
    def __init__(self):
        pyxel.init(W, H, title="<Title from Vision>", fps=FPS)
        self._build_assets()
        self._reset()
        pyxel.run(self.update, self.draw)

    def _build_assets(self):
        # populated in Stage 5
        pass

    def _reset(self):
        self.scene = TITLE_SCENE
        self.frame = 0
        self.score = 0
        self.hi_score = 0
        self.lives = 3

    def update(self):
        self.frame += 1
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()
        s = self.scene
        if s == TITLE_SCENE:
            self._update_title()
        elif s == INTRO:
            self._update_intro()
        elif s == PLAY:
            self._update_play()
        elif s == WIN:
            self._update_win()
        elif s == GAME_OVER:
            self._update_gameover()

    def draw(self):
        pyxel.cls(BG)
        s = self.scene
        if s == TITLE_SCENE:
            self._draw_title()
        elif s == INTRO:
            self._draw_intro()
        elif s == PLAY:
            self._draw_play()
        elif s == WIN:
            self._draw_win()
        elif s == GAME_OVER:
            self._draw_gameover()

    def _update_title(self):
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.scene = PLAY  # or INTRO if applicable

    def _draw_title(self):
        t = "<TITLE>"
        pyxel.text((W - len(t) * 4) // 2, H // 2 - 16, t, 7)
        if self.frame % 40 < 28:
            t2 = "PRESS SPACE"
            pyxel.text((W - len(t2) * 4) // 2, H // 2 + 16, t2, 10)

    # Other scene update/draw methods are stubs — populated in Stage 6.
    def _update_intro(self): pass
    def _draw_intro(self): pyxel.text(8, 8, "INTRO (stub)", 7)
    def _update_play(self): pass
    def _draw_play(self): pyxel.text(8, 8, "PLAY (stub)", 7)
    def _update_win(self): pass
    def _draw_win(self): pyxel.text(8, 8, "WIN (stub)", 7)
    def _update_gameover(self): pass
    def _draw_gameover(self): pyxel.text(8, 8, "GAME OVER (stub)", 7)


App()
```

The skeleton must run cleanly. Verify:

- `validate(script="main.py")` is clean (no syntax errors, no anti-pattern warnings).
- `run(script="main.py", frames=30, snapshots=[{"frame": 29, "kind": "screen_image", "output": "tmp/scaffold-smoke.png"}])` returns a non-empty PNG showing the TITLE text and blinking prompt.

## Project marker

Create `.pyxel-skill/` at project root:

```bash
mkdir -p .pyxel-skill/gate-snapshots
echo "stage-3-scaffold-complete" > .pyxel-skill/stage-marker
```

The Stop hook reads this directory to identify pyxel-skill projects. Do not commit `.pyxel-skill/gate-snapshots/` — add to `.gitignore` of the *generated* game project (not pyxel-skill itself):

```
# .gitignore for game projects scaffolded by pyxel-skill
.pyxel-skill/gate-snapshots/
screenshots/
```

## Anti-patterns in this stage

- **Putting gameplay code in scaffold.** The skeleton must be empty of gameplay; verifying scaffold means verifying scene transitions and scene rendering, not whether the player can jump.
- **Embedding magic numbers in update/draw without lifting them to module-level constants.** PLAN.md milestones reference constants by name; inlined numbers can't be cross-checked.
- **Coupling scene update with rendering.** Update reads input and changes state; draw reads state and renders. Mixed concerns make scene transitions hard to verify.

## When this stage is done

- `STRUCTURE.md` has Modules, Scene state machine, Tuning, State persistence, Verification sections appended.
- `main.py` runs and shows TITLE without errors (`validate` clean, `run` with a 30-frame `screen_image` snapshot shows TITLE).
- `.pyxel-skill/stage-marker` exists and contains `stage-3-scaffold-complete`.
- Move to Stage 4 (read `asset-planner.md`).
