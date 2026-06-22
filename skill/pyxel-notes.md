# Pyxel Notes

Short reminders for common Pyxel mistakes. Read only when the current task touches the relevant area.

## Run and Input

- `pyxel.btn(KEY)` is continuous; `pyxel.btnp(KEY)` is a press edge.
- For deterministic tests, pass `random_seed` to `run` and avoid frame-dependent randomness that changes across different run lengths.
- Long input scripts can drift. Re-run from frame 0 with a cumulative schedule after reading observed state.

## Drawing

- Call `pyxel.cls(color)` at the start of `draw()`.
- Use `colkey=0` on `blt()` when sprite backgrounds should be transparent.
- Keep HUD outside the playfield unless overlap is intentional and verified in a screenshot.

## Assets

- Build image banks before `pyxel.run()` starts, usually in `App.__init__` or `_build_assets()`.
- Use `read_image(..., render_path=...)` for sprites that must be recognizable.
- Use `read_animation(..., region_count=2, direction=...)` for paired frames.
- Avoid visible content in source tile `(0, 0)` when tilemaps use it as blank.

## Audio

- For sounds that need verification, use `pyxel.sounds[N].set(...)`, not MML-only slots.
- In `.set(notes=...)`, notes need explicit octave digits such as `C2D2E2`; `R` is a rest.
- Render gateable audio with `read_audio(script=..., target={"sound": N}, output_path=...)`; music targets do not expose note lists.

## Visual Truth

A state snapshot can say the game is won while the frame shows an unreadable or wrong scene. Trust the captured pixels and fix the game.
