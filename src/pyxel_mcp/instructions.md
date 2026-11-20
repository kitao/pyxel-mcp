# Pyxel MCP

Use the installed Pyxel runtime to inspect its API, run a trusted game, and examine its assets. Call `pyxel_info` for the runtime version and paths to runnable examples.

## Tools

- `lookup_api` returns declarations from the installed Pyxel and Cube stubs. Try `Image.blt`, `cube.Node`, or a partial name such as `raycast`.
- `validate` checks Python syntax and reports Pyxel code patterns without executing the script.
- `run` observes callbacks, static screens, and manual flip loops. Set `frames` as a budget. A `screen_image` with `frame: "end"` and `inline: true` returns the last completed frame as a PNG. Use a `screen_grid` with a small `bbox` for exact pixel indices.
- `read_palette`, `read_image`, `read_tilemap`, and `read_audio` accept either a trusted script or a .pyxres file in the `script` field. For scripts, assets are inspected at the first run, show, or flip. For .pyxres files, Pyxel loads the resource and its matching .pyxpal. Image regions use pixels and tilemap regions use tiles.
- `diff_frames` compares two saved PNGs and reports the changed pixel count and bounds.

## Contract

Each run starts a fresh process. Pass a local file path in `script` and absolute paths for output files. Game scripts execute with the server's permissions. Results carry `ok` and `errors`. Check `issues` for validation findings, and `exit_status` and `log` for a run.

Frames start at 0. Scheduled button sets, axis maps and mouse positions persist until replaced. Text input, wheel deltas and dropped files apply for one frame. Use `random_seed` to repeat Python and Pyxel random sequences. Use `until` for an event and request snapshots at `"end"` to inspect it. State paths and conditions start from the bound update object's attributes or the script's globals. Use `__main__.player.x` to reach script globals explicitly, including from class-based games. Cube attributes can be read by component, for example `scene.camera.transform.pos.x`.

A script's `pyxel.quit()` preserves completed frames. With manual loops each `flip()` completes a frame. Cleanup errors are reported with the observations already taken. Use `inline: true` for PNG previews or rendered WAV audio. The result also gives a local path.

## Resources

- `pyxel://run-snapshots-schema` documents frame selectors, inputs, snapshot formats, limits, and script lifecycle.
- `pyxel://validation-patterns` explains validation categories.
- `pyxel://palette/default` lists installed palette constants and RGB values.
- `pyxel://examples/{name}` and `pyxel://examples/cube/{name}` serve bundled example source. Append the name from `pyxel_info` to `pyxel://examples/`. Pass the returned file path to `run` to include the example's local assets.
