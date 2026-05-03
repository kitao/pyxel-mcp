# Stage 1: Visual Target

Anchor the art direction in text **before any code is written**. Every spatial and stylistic choice committed here becomes a downstream requirement: the asset planner enumerates objects from the Vision subsection, the test harness measures against milestones derived from win/lose definitions, and the quality gate compares output frames to the layout described here.

Pyxel runs in 16 colors at small resolutions. The visual target is a **structured text spec**, not an external image. Do not generate `reference.png`; do not invoke any AI image API.

## Inputs

- The user's natural-language brief.
- `knowledge/pixel-art.md` (palette + 3-layer hierarchy).
- `knowledge/background.md` (screen size derivation).
- `knowledge/audio.md` (channel discipline).

## Outputs

Two artifacts, both at project root:

1. **`ASSETS.md`** — create the file with one top-level heading and one **Art direction** line. Sprite manifest is filled by Stage 4; do not touch that here.

   ```markdown
   # Assets

   **Art direction:** <one-paragraph description of the visual identity, palette mood, and overall scene vibe>
   ```

2. **`STRUCTURE.md`** — create the file with one top-level heading and a **Vision** section containing the seven subsections below. Architecture details (modules, scene state machine, tuning constants) are filled by Stage 3.

   ```markdown
   # Architecture

   ## Vision

   ### Window contract
   ...

   ### Palette budget
   ...

   ### Layout
   ...

   ### Objects
   ...

   ### HUD
   ...

   ### Audio
   ...

   ### Win / lose conditions
   ...
   ```

## What goes in each Vision subsection

### Window contract

```
Screen: <W>x<H>  (e.g., 224x256 — portrait arcade aspect)
FPS:    30 or 60
Title:  "<game title shown in window bar>"
Background color (palette idx): <0–15>
```

Choose Pyxel's screen size from playfield content, not the other way around. Standard arcade-style portrait: 224x256 or 192x224. Standard side-scroller: 256x192 or 256x144. See `knowledge/background.md` "Screen & Text Layout" for the content-first sizing pattern.

### Palette budget

List the indices used and the role each plays. The 3-layer hierarchy (dark backgrounds, mid environment, bright interactive) from `knowledge/pixel-art.md` should be visible:

```
0  black     — background void / outline
1  navy      — background detail (sky / shadow)
3  green     — foliage / pickups
4  brown     — terrain / wood
8  red       — interactive (hazards, enemy projectiles)
10 yellow    — interactive (pickups, score)
14 pink      — characters (skin / accent)
15 peach     — characters (highlight)
```

A flat use of red on navy is a contrast failure and will FAIL the quality gate. Use 10-14 of the 16 colors.

### Layout

ASCII map at one cell per 8 px (or coarser if the screen is large). Mark static structure and the spawn position of each named object.

```
.................................   y=0
......BBB.HELP!.PP...............   y=8   B = boss, P = princess
......BBB.......PP...............
=================================   y=16  girder 0
.....l...........l...............   y=24  l = ladder
=================================   y=48  girder 1
.....l...........l...............
M================================   y=136 girder 4 (Mario start, M)
                                    y=144 (screen bottom)
```

Coordinates are exact — the decomposer reads them as numbers in Stage 2.

### Objects

For every distinct object in the layout, list once with:

```
- <name>:
  - represents: "<one-sentence description an outsider would identify>"
  - sprite size: <WxH> pixels
  - palette: <list of 3-5 palette indices used>
  - quantity in scene: <int> (e.g., 1 for player, "spawned by boss" for barrels)
  - initial position: (x, y)
  - states/frames: <e.g., "idle, walk1, walk2, jump, climb1, climb2">
```

The **represents** line is the asset-gen identity contract: a stranger shown the rendered sprite without context must be able to identify it as that thing. Single-color blobs do not satisfy this contract.

### HUD

Every text/UI element with screen position:

```
- score:     "1UP / <digits>"   at (4, 4),     color 8
- highscore: "HIGH / <digits>"  at (W/2-12, 4), color 7
- level:     "L=<dd>"           at (W-32, 4),  color 10
- bonus:     "BONUS <dddd>"     at (W-48, 12), color 10
- lives:     mini-Mario icons   at (4, 12),    color 14
- "HELP!" above princess         blinking, color 8
- "HOW HIGH CAN YOU GET?"        intro screen, color 10
```

### Audio

Every player-visible event needs SE. List each declared sound channel and what it triggers on:

```
ch0 (BGM melody):  loops while scene == PLAY
ch1 (BGM bass):    pairs with ch0
ch2 (BGM harmony): pairs with ch0
ch3 (SE):
  - SE jump:        on btnp(KEY_SPACE), ascending square wave
  - SE climb step:  on btn(UP/DOWN) every 8 frames while climbing
  - SE death:       on barrel collision, descending tone
  - SE win:         on princess reach, ascending arpeggio
```

BGM uses ch0–ch2; SE uses ch3 only. Volume 5–7 for SE so it cuts through BGM. Square or pulse tone for melodic SE; noise tone is inaudible over BGM and fails verification. See `knowledge/audio.md` for SE cookbook recipes.

### Win / lose conditions

```
Win condition:  player.y <= <int> AND |player.x - princess.x| < <int>
                 → scene = WIN within 30 frames
Lose condition: lives == 0
                 → scene = GAME_OVER within 30 frames
Death event:    barrel collision → lives -= 1, respawn at start, barrels cleared
```

These predicates feed the win/lose milestone tables that Stage 2 (decomposer) writes into PLAN.md.

## Anti-patterns in this stage

- **"Mario or Mario-like character"** — vague reference. The asset planner can't generate for vague references; commit to a specific look in `represents:`.
- **"Pretty background"** without enumerating *what* fills it. The background gets forgotten downstream and the result is plain navy.
- **Listing colors but not their role.** The contrast rule needs roles. Without them, palette hierarchy can't be checked.
- **Skipping HUD because "we'll add it later".** Layout coordinates change under HUD; plan it now.
- **Marking the screen as small (e.g., 128x128) and then trying to fit 4 platforms + ladders + HUD + DK + princess.** Pixel budget runs out. Pick screen from content (see `knowledge/background.md`).

## When this stage is done

- `ASSETS.md` exists with the `# Assets` heading and one `**Art direction:**` line.
- `STRUCTURE.md` exists with the `# Architecture` heading and a `## Vision` section containing all seven subsections above, populated.
- Move to Stage 2 (read `decomposer.md`).
