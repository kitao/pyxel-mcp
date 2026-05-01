# Pyxel App Development

## Workflow

1. Call `pyxel_info` to locate API stubs and examples.
2. Read stubs for API details. Read examples for coding patterns (01-19, 99).
3. Write code.
4. Verify with tools:
   - `run_and_capture` after every visual change.
   - `render_audio` for each sound channel separately.
   - `play_and_capture` to test input-dependent logic (menus, movement).
   - `inspect_state` to debug logic bugs by inspecting variable values.
   - `validate_script` before running to catch syntax errors and anti-patterns.
   - `inspect_palette` to check color usage and contrast issues.
   - `inspect_tilemap` to verify tilemap content and detect (0,0) trap.
   - `inspect_bank` to see all sprites/tiles in an image bank.
   - `compare_frames` for visual regression testing between frames.
   - `inspect_screen` for compact color grid (no image tokens).
   - `capture_frames` for multi-frame animation and transition verification.
   - `record_gameplay` for animation flow as a single GIF (clearer than multiple PNGs for transitions, AI motion, parallax).
   - `inspect_animation` for sprite animation consistency (palette, silhouette, frame diffs).
5. Fix and re-verify.

### Error Recovery

- **`run_and_capture` timeout**: Script has an infinite loop or heavy computation. Check `update()`/`draw()` for blocking logic. Reduce `frames` parameter to test earlier.
- **`run_and_capture` black screen**: `cls()` called but nothing drawn, or drawing with the same color as background. Check draw coordinates are within screen bounds.
- **`render_audio` empty output**: Sound slot not populated. Verify the script calls `pyxel.sounds[N].set()` or `.mml()` before the game loop.
- **`inspect_sprite` all zeros**: Image bank not populated. Ensure `pyxel.images[N].set()` or `.load()` runs before the game loop starts.
- **`inspect_layout` no text detected**: Text may be too small, overlapping, or same color as background. Try a different frame number.
- **`inspect_layout` margin warnings**: Content not centered. Adjust screen size to match content, or reposition content to center it. Margins should be symmetric.
- **`validate_script` false positive**: Anti-pattern checks are heuristic. If a warning seems wrong, it's safe to ignore and run the script.
- **`inspect_tilemap` all zeros**: Tilemap not populated. Ensure `tilemaps[N].set()` runs before the game loop. Check `imgsrc` matches the image bank with tile data.

### Reading Tool Output

- **`run_and_capture`**: Returns a screenshot image. Visually verify layout, colors, and sprite positions.
- **`render_audio`**: Returns note sequence with timing/frequency. Check that notes match the intended melody and rhythm feels correct.
- **`inspect_sprite`**: Returns a pixel grid + symmetry report. Asymmetric pixels are listed by row — fix those coordinates in `images[N].set()`.
- **`inspect_layout`**: Returns margins, horizontal/vertical balance, quadrant density, center of mass, and text positions. Check margins for symmetry, balance > 70%, and quadrant distribution. Warnings (⚠) flag specific issues.
- **`capture_frames`**: Returns multiple screenshots. Compare frames to verify animation progresses smoothly without jumps or flicker.
- **`record_gameplay`**: Returns a GIF of N frames. Visually verify motion smoothness, transition timing, and that input events trigger expected state changes over time.
- **`play_and_capture`**: Returns screenshots with simulated input. Verify that input causes expected state changes (player moved, menu changed, bullet spawned).
- **`inspect_state`**: Returns game object attributes at a specific frame. Check that variable values match expectations (score, position, game state). Use comma-separated frames for timeline diff: `frames="10,30,60"`.
- **`validate_script`**: Returns syntax errors and anti-pattern warnings. Run before `run_and_capture` to catch issues without Pyxel execution overhead.
- **`inspect_screen`**: Returns screen as hex color grid. Compact token usage. Good for programmatic comparison.
- **`compare_frames`**: Returns changed pixel count, percentage, and region between two frames. Use to verify only intended areas changed.
- **`inspect_palette`**: Returns color distribution and contrast warnings. Check that foreground colors have sufficient contrast against background.
- **`inspect_tilemap`**: Returns tile grid, usage stats, and bounding box. Check `imgsrc` matches your image bank. Verify (0,0) tiles are empty.
- **`inspect_bank`**: Returns image bank as screenshot (up to 256x256). Verify sprite/tile placement and find available space.
- **`inspect_animation`**: Returns per-frame pixel diffs, palette consistency, and silhouette stability. Check that frames share a consistent outline and palette — large diffs between adjacent frames indicate flickering or misaligned sprites.

### Output Format

Analysis tools (`inspect_sprite`, `inspect_layout`, `inspect_palette`,
`inspect_animation`, `validate_script`) output two sections:
- **=== Analysis ===**: Objective data and measurements
- **=== Suggestions ===**: Actionable improvements (`Fix:` for critical issues, `Tip:` for recommendations)

### Testing Input-Dependent Logic

Use `play_and_capture` to test input-dependent logic by simulating key presses:

```python
# Press SPACE at frame 30, release at frame 50, capture at frames 29,31,51
play_and_capture("game.py",
    inputs='[{"frame":30,"keys":["KEY_SPACE"]},{"frame":50,"keys":[]}]',
    frames="29,31,51")
```

```python
# Analog stick (gamepad): tilt left stick X to 50% right at frame 10
play_and_capture("game.py",
    inputs='[{"frame":10,"btnv":{"GAMEPAD1_AXIS_LEFTX":16384}}]',
    frames="11,30,60")
```

`btnv` values are int analog values matching SDL gamepad ranges
(typically `-32768`...`32767` for sticks, `0`...`32767` for triggers).

Input events persist until changed by a later entry. Use this for:
- Menu navigation (KEY_RETURN to start, verify game screen)
- Movement (KEY_LEFT/RIGHT held for multiple frames)
- Shooting (KEY_SPACE press, check bullet spawns)
- Mouse clicks (set mouse_x/mouse_y with MOUSE_BUTTON_LEFT)

For simple one-shot tests, the frame-based trigger approach also works:
```python
# Original:  if pyxel.btnp(pyxel.KEY_SPACE): jump()
# Test:      if pyxel.frame_count == 30: jump()
```

### Debugging Game Logic

Use `inspect_state` to read variable values at a specific frame:

```python
inspect_state("game.py", frames="60", attributes="score,lives,player_x,player_y")
```

This captures the App instance (the class calling `pyxel.run()`) and dumps its attributes. Useful for:
- Physics bugs: check position/velocity values
- Score/state bugs: verify counter values
- Collision issues: check object positions relative to each other

Note: `inspect_state` does not support input simulation. It captures state at a given frame without any key presses. To test input-dependent logic, temporarily replace input conditions with frame-based triggers in the script, then revert.

### Letting the User Play

When suggesting the user run a script directly, check for a virtual environment (`.venv/bin/python` or similar) and include the full path in the command. Users may not have Pyxel installed globally.

## Pyxel Reference

Official docs (fetch for API details, usage guides, and syntax):
- API reference: https://raw.githubusercontent.com/kitao/pyxel/main/docs/api-reference.md
- User guide: https://raw.githubusercontent.com/kitao/pyxel/main/docs/user-guide.md
- MML commands: https://raw.githubusercontent.com/kitao/pyxel/main/docs/mml-commands.md
- Resource format: https://raw.githubusercontent.com/kitao/pyxel/main/docs/pyxres-format.md
- Local stubs and examples: call `pyxel_info`.
- User-created games: https://github.com/kitao/pyxel/wiki/Pyxel-User-Examples

## Pyxel Reference via MCP Resources

In addition to fetching the URLs above directly, this MCP server
exposes Pyxel docs and official examples as MCP Resources for
faster access:

- `pyxel://api-reference` — full API reference
- `pyxel://user-guide` — concepts and patterns
- `pyxel://mml-commands` — MML syntax for procedural music
- `pyxel://pyxres-format` — `.pyxres` file structure
- `pyxel://examples/<name>` — official examples (e.g. `02_jump_game`, `09_shooter`, `10_platformer`)
- `pyxel://palette/default` — 16-color reference with use hints

In Claude Code, reference them with `@pyxel:api-reference` or
`@pyxel:examples/02_jump_game` directly in chat.

## Essential Tips

Common gotchas not obvious from the API reference:

- `colkey`: transparent color index (e.g., `colkey=0` treats black as transparent)
- Negative `w` flips horizontally, negative `h` flips vertically in `blt()`
- Animation: `u = pyxel.frame_count // 4 % frame_count * SPRITE_W`
- `sin()`/`cos()` use **degrees**, not radians
- Font size: `FONT_WIDTH=4`, `FONT_HEIGHT=6`
- Use `btnp()` for one-shot actions, `btn()` for continuous hold
- Always call `pyxel.cls(col)` at the start of `draw()`
- Iterate over a copy when removing: `for e in list(enemies):`

### Pyxel 2.9 APIs Worth Knowing

- **`pyxel.resize(w, h)`** — change the screen size at runtime. Use cases: options menus, responsive layouts, "fullscreen" toggle.

  ```python
  pyxel.resize(256, 192)  # widescreen
  ```

- **`pyxel.screencast(filename)`** — save a GIF of recent frames. Pyxel buffers frames automatically. The MCP exposes this via `record_gameplay`; you can also call it directly from your script:

  ```python
  if pyxel.btnp(pyxel.KEY_F9):
      pyxel.screencast("clip")  # saves clip.gif
  ```

- **`pyxel.set_btnv(key, val)`** — set an analog input value (gamepad axes/triggers). Mainly for headless testing — invoked automatically by `play_and_capture` and `record_gameplay` when you pass a `btnv` event.

### Beyond Defaults

Pyxel's default resource slots (3 images, 8 tilemaps, 64 sounds, etc.) are starting points, not hard limits. All global lists (`images`, `tilemaps`, `sounds`, `musics`, `channels`, `tones`, `colors`) support `append()` and slice assignment to grow beyond defaults.

| Feature | How | Example |
|---------|-----|---------|
| Custom-size images | `Image(w, h)`, `Image.from_image(file)` | Offscreen rendering (ex. 11) |
| Custom-size tilemaps | `Tilemap(w, h, img)`, `Tilemap.from_tmx(file, layer)` | Large maps, Tiled editor (ex. 15) |
| More sounds/musics | `Sound()`, `Music()` as standalone instances | Beyond 64/8 slot limit |
| More channels | `Channel()` with gain/detune, append to `pyxel.channels` | Polyphony expansion (ex. 14) |
| Custom waveforms | `Tone()` with wavetable, append to `pyxel.tones` | Synth sounds (ex. 14) |
| Extended palette | `pyxel.colors.append(0xRRGGBB)` — up to 256 colors | Richer color range (ex. 05) |
| Custom fonts | `Font(file, size)` — BDF/OTF/TTF/TTC | Japanese text, styled text (ex. 13) |
| Audio file playback | `Sound.pcm("file.wav")` — WAV/OGG | BGM from audio files (ex. 18) |
| Rotation & scaling | `blt(..., rotate=deg, scale=n)` | Sprite transforms (ex. 16) |
| 3D perspective | `blt3d()`, `bltm3d()` with camera pos/rot/fov | Pseudo-3D rendering (ex. 19) |

Suggest these when users hit default limits or need features like multilingual text, richer audio, larger worlds, or visual effects. See the referenced examples for working code.

### Audio Channel Management

Pyxel defaults to 4 audio channels (0-3), but more can be added via `pyxel.channels.append(Channel())`. `playm()` assigns music tracks to channels starting from ch0. `play(ch, snd)` on the same channel **interrupts** the music on that channel. Plan channel allocation to avoid BGM/SE conflicts:

- **BGM on ch0-2, SE on ch3**: Use 3-channel music so SE never interrupts BGM.
- **Title/menu screens**: Can safely use all 4 channels for BGM (no frequent SE).
- Use `resume=True` for non-critical SE to avoid cutting off other sounds.

### Tilemap Gotchas

**Important**: All tilemap cells default to tile (0, 0). Keep position (0, 0) in the image bank empty (transparent) — if you place a visible tile there, it fills the entire tilemap as background.

If tiles are in a different image bank than sprites, set `imgsrc`:

```python
pyxel.tilemaps[0].imgsrc = 1  # draw tiles from image bank 1
```

## Quality Checklist

Quick-reference of common mistakes. See linked sections for details.

| Category | Don't | Do |
|----------|-------|----|
| Layout | Pick screen size first, then fit content | Derive screen size from content + margins |
| Layout | Ignore inspect_layout warnings | Fix all ⚠ warnings before proceeding |
| Code | Hardcode pixel positions | Calculate from `width`/`height` |
| Code | Forget `cls()` in `draw()` | Always call `pyxel.cls(col)` first |
| Code | Use radians with `sin()`/`cos()` | Pyxel trig uses degrees |
| Code | `btn()` for one-shot action | Use `btnp()` for press-once events |
| Code | Modify list while iterating | Iterate over a copy: `for e in list(enemies):` |
| Drawing | Draw UI before sprites | Draw order: bg → objects → UI |
| Drawing | Omit `colkey` in `blt()` | Add `colkey=0` for transparency |
| Drawing | Static animation frame | See Animation Timing |
| Visual | Plain black background | See Background Design |
| Visual | No title screen | See Title Screen Design |
| Visual | No visual feedback on actions | See Visual Feedback |
| Visual | Player blends into bg | See Color Palette & Hierarchy |
| Audio | `play()` on BGM channel | SE on ch3, BGM on ch0-2 |
| Audio | Noise tone for melodic SE | Square or pulse, vol 5-7 |
| Audio | Skip SE for core actions | SE for every player event |
| Audio | Only gen_bgm, no MML | Mix gen_bgm with hand-written MML for variety |
| Sprite | Single static player frame | Min 5 images (idle/walk:2/jump/attack) |
| Sprite | Single static enemy frame | Min 2 animation frames per enemy |
| Level | Random platform placement | Zone-based progression (see Level Design) |
| Level | Enemies floating in void | Ground enemies on ground, flyers in open space |

Before release, verify: BGM present (MML or gen_bgm), distinct SE for all events, title screen with animation, game over with score, non-solid background, HUD with score/lives, player has walk animation, enemies have 2+ frames.
