# pyxel-mcp

pyxel-mcp exposes eight tools for observing trusted local Pyxel scripts. It reports facts; the caller decides what those facts mean for the current task.

## Contract

- A `script` is a Python file path, never inline source. Script tools execute it in a fresh subprocess and are not a sandbox.
- Every result has `ok` and `errors`. A successful call may still contain useful `log` or `warnings` fields.
- Artifact paths must be absolute. Relative assets used by a script resolve from the script's directory.
- Each call starts from a clean Pyxel process. Reproduce prior input from frame 0 when continuing a scenario.

## Tools

- `validate`: parse a script and report recognizable Pyxel code patterns without executing it.
- `run`: advance frames, schedule inputs, stop on an optional App-attribute condition, and capture `state`, `screen_image`, `screen_grid`, or `video` snapshots.
- `pyxel_info`: report installed versions, paths, examples, and resource URIs.
- `read_palette`: return palette colors and image-bank palette indices in use.
- `read_image`: return image-bank pixels for a region and optionally render a PNG.
- `read_tilemap`: return tile coordinates, source bank, usage counts, bounds, and optional rendered output.
- `read_audio`: render one sound or music target to WAV and return measurable audio data.
- `diff_frames`: compare two PNG files pixel by pixel.

Use `random_seed` when randomness affects a run. Use `until` with snapshots at `"end"` when the target is an event rather than a known frame. Inspect captured images directly when appearance matters.

## Resources

- `pyxel://run-snapshots-schema`: complete snapshot grammar.
- `pyxel://validation-patterns`: categories reported by `validate`.
- `pyxel://palette/default`: default palette table.
- `pyxel://examples/{name}`: source for a named example bundled with the installed Pyxel package.

`pyxel_info` discovers available example names. Full game-building guidance belongs in the separate pyxel-skill project.
