# pyxel-mcp

pyxel-mcp is an MCP server for observing Pyxel programs. It exposes 9 tools. They return facts; the agent decides whether those facts satisfy the current game.

Tools with a `script` argument execute trusted local Python in a fresh subprocess. pyxel-mcp is an observation adapter, not a sandbox for untrusted code. Every `script` argument is a file path to a Python script, not inline source code.

## Tools at a glance

- `validate(script)`: syntax plus common Pyxel anti-patterns. Run before the first dynamic check.
- `run(script, frames, inputs=[], snapshots=[], random_seed=None, timeout=10, stall_window_frames=None, until=None)`: drive the game headlessly and collect snapshots. Snapshot kinds are `state`, `screen_image`, `screen_grid`, `layout`, and `video`. Read `log` even when `ok` is true. `until="score >= 1"` stops at the first frame where the App-attribute expression holds (reported as `until_met`); `"frame": "end"` snapshots capture that stop frame.
- `pyxel_info()`: versions, paths, examples, and resource URIs.
- `read_palette(script)`: palette state, used indices, hierarchy hints, and contrast warnings.
- `read_image(script, image, x=0, y=0, w=None, h=None, render_path=None)`: image-bank pixels and optional PNG render for visual inspection.
- `read_animation(script, image, x, y, w, h, region_count, direction)`: adjacent sprite-frame consistency and per-pair diffs.
- `read_tilemap(script, tilemap, render_path=None)`: tile usage, non-empty region, and `(0, 0)` trap warning.
- `read_audio(script, target, output_path)`: render `{"sound": N}` or `{"music": N}` to WAV. Sound targets expose note lists; music targets are channel sound references.
- `diff_frames(frame_a, frame_b)`: pixel diff between two PNG files.

See `pyxel://run-snapshots-schema` for the complete `run.snapshots` grammar.

## Workflow patterns

A small Pyxel task usually needs only this loop:

1. `validate` the script.
2. `run` with one `state` snapshot and one `screen_image` at the frame being checked.
3. Inspect the PNG yourself. State proves mechanics; pixels prove what the player sees.
4. Add targeted `read_*` calls for assets, audio, palette, or tilemaps only when they matter.
5. Write task-specific assertions in Python against returned values; do not use universal quality scores.

Example snapshot pair:

```json
{
  "snapshots": [
    {"kind": "state", "frame": 60, "attrs": ["player.x", "score"]},
    {"kind": "screen_image", "frame": 60, "output": "/tmp/frame60.png"}
  ]
}
```

Use `random_seed` when randomness affects verification. For long input paths, rerun from frame 0 with the cumulative schedule after each observed state checkpoint. Prefer `until` over guessing frame numbers when you need "the moment X happens".

For full game-building workflow guidance, see `pyxel-skill`: https://github.com/kitao/pyxel-skill.

## Quirks

- `pyxel.btn(K)` is continuous; `pyxel.btnp(K)` is a press edge.
- Call `pyxel.cls(color)` at the start of `draw()`.
- Use `colkey=0` on `blt()` when sprite backgrounds should be transparent.
- Avoid visible content in source tile `(0, 0)` when tilemaps use it as blank.
- Build assets before `pyxel.run()` starts, usually in `App.__init__`.
- Prefer `pyxel.sounds[N].set(...)` for sounds that need note-list verification.
- Each tool call runs in a fresh subprocess; relative asset paths resolve from the script's parent directory.

## Resources

- `pyxel://run-snapshots-schema` - full snapshot schema.
- `pyxel://anti-patterns` - `validate` issue catalog.
- `pyxel://api-reference`, `pyxel://user-guide`, `pyxel://mml-commands`, `pyxel://pyxres-format` - Pyxel documentation, fetched live from GitHub with a 24h cache; offline reads fall back to the cached copy.
- `pyxel://palette/default` - default 16-color palette.
- `pyxel://examples/<name>` - bundled example scripts.
