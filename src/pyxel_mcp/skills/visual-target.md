# Visual Target — REFERENCE.md authoring

**Phase 1.** Anchor the art direction *before* any code is written.
Every spatial and stylistic choice committed here becomes a downstream
requirement: the asset planner enumerates objects from this file, the
test harness measures against milestones derived from it, and the
quality gate compares output frames to the layout described here.

## Output

A single file `REFERENCE.md` at the project root. Pyxel runs in 16
colors at small resolutions; the reference is a structured text
document, not an external image.

## Content

The reference must enumerate, in order:

### 1. Window contract

```
Screen: <W>x<H>  (e.g., 224x256 — portrait arcade aspect)
FPS:    30 or 60
Title:  "<game title shown in window bar>"
Background color (palette idx): <0–15>
```

Choose Pyxel's screen size from the playfield content, not the
other way around. Standard arcade-style portrait: 224x256 or 192x224.
Standard side-scroller: 256x192 or 256x144.

### 2. Palette budget

Pyxel's default 16-color palette is the canvas. List the indices used
and what each role serves:

```
0 black     — background void / outline
1 navy      — background detail (sky / shadow)
3 green     — foliage / pickups
4 brown     — terrain / wood
8 red       — interactive (hazards, enemy projectiles)
10 yellow   — interactive (pickups, score, hammers)
14 pink     — characters (skin / princess accent)
15 peach    — characters (highlight)
...
```

The 3-layer hierarchy from `pyxel://api-reference` should be visible
in this list: dark backgrounds, mid environment, bright interactive.
A flat use of red on navy is a contrast failure and will FAIL the
gate.

### 3. Layout map (ASCII)

Draw the playfield as ASCII at one cell per 8 pixels (or coarser if
the screen is large). Mark static structure and the spawn position
of each named object.

```
.................................   y=0
......BBB.HELP!.PP...............   y=8   B = boss, P = princess
......BBB.......PP...............
=================================   y=16  girder 0
.....l...........l...............   y=24  l = ladder
.....l...........l...............
=================================   y=48  girder 1
.....l...........l...............
=================================   y=80  girder 2
.....l...........l...............
=================================   y=112 girder 3
.....l...........l...............
M================================   y=136 girder 4 (Mario start, M)
                                    y=144 (screen bottom)
```

Coordinates are exact — the decomposer reads them as numbers.

### 4. Object enumeration

For every distinct object in the layout, list it once with:

```
- <name>:
  - represents: "<one-sentence description an outsider would identify>"
  - sprite size: <WxH> pixels
  - palette: <list of 3-5 palette indices used>
  - quantity in scene: <int> (e.g., 1 for player, "spawned by boss" for barrels)
  - initial position: (x, y)
  - states/frames: <e.g., "idle, walk1, walk2, jump, climb1, climb2">
```

The "represents" line is the asset-gen identity contract: a stranger
shown the rendered sprite without context must be able to identify it
as that thing. Single-color blobs do not satisfy this contract.

### 5. HUD elements

Every text/UI element with screen position:

```
- score:    "1UP / <digits>"   at (4, 4),   color 8 (red)
- highscore: "HIGH / <digits>" at (W/2-12, 4), color 7 (white)
- level:    "L=<dd>"           at (W-32, 4), color 10
- bonus:    "BONUS <dddd>"     at (W-48, 12), color 10
- lives:    mini-Mario icons   at (4, 12), color 14
- "HELP!" above princess        blinking, color 8
- "HOW HIGH CAN YOU GET?"       intro screen, color 10
```

### 6. Audio cues

Every player-visible event needs SE. List each declared sound channel
and what it triggers on:

```
ch0 (BGM melody):  loops while scene == PLAY
ch1 (BGM bass):    pairs with ch0
ch2 (BGM harmony): pairs with ch0
ch3 (SE):
  - SE jump:         on btnp(KEY_SPACE), ascending square wave
  - SE climb step:   on btn(UP/DOWN) every 8 frames while climbing
  - SE barrel jump:  on jumping over barrel (+100 score)
  - SE death:        on barrel collision, descending tone
  - SE win:          on princess reach, ascending arpeggio
```

BGM uses ch0–ch2; SE uses ch3 only. Volume 5–7 for SE so it cuts
through BGM. Square or pulse tone for melodic SE; noise tone is
inaudible over BGM and fails verification.

### 7. Win / lose definitions

```
Win condition:  player.y <= <int> AND |player.x - princess.x| < <int>
                 → scene = WIN within 30 frames
Lose condition: lives == 0
                 → scene = GAME_OVER within 30 frames
Death event:    barrel collision → lives -= 1, respawn at start,
                                    barrels cleared
```

These predicates feed `quality_gate`'s playthrough verification.

## Anti-patterns in this phase

- "Mario or Mario-like character" — the asset planner can't generate
  for vague references. Commit to a specific look in `represents`.
- "Pretty background" without enumerating *what* fills it.
  Background gets forgotten downstream and the result is plain navy.
- Listing colors but not their role. The contrast rule needs roles.
- Skipping HUD because "we'll add it later". Layout coordinates change
  under HUD; plan it now.
- Marking the screen as small (e.g., 128x128) and then trying to fit
  4 platforms + ladders + HUD + DK + princess. Pixel budget runs out.
  Pick screen from content.

## When this phase is done

`REFERENCE.md` exists with all 7 sections. Move to `decomposer`
(read `pyxel://skills/decomposer`).
