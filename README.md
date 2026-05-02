# pyxel-mcp

MCP server for [Pyxel](https://github.com/kitao/pyxel), a retro game engine for Python. Gives AI agents the verbs to **run, observe, and verify** Pyxel programs without launching a window — headless, deterministic, gate-able.

## Tools (9)

### Dynamic driver

- **`run`** — Drive a script through N frames headless. Schedule input events (`set_btn` / `set_btnv` / `set_mouse_pos`) per frame; collect snapshots at chosen frames; parse `ASSERT PASS|FAIL` lines; seed RNG. Snapshot kinds: `screen_image` (PNG), `screen_grid` (palette-index 2D array), `state` (dotted-path attrs of the App instance), `layout` (text/region balance metrics), `video` (GIF/MP4 of a frame range). Multi-frame syntax (`{"frames": [10, 20, 30]}` or `"10..50:5"`) for cheap N-frame batches.

### Static inspectors

- **`inspect_palette`** — `pyxel.colors` analysis: 3-layer hierarchy (bg/env/interactive), WCAG contrast warnings filtered to **co-located pairs** (only colors actually adjacent in image-bank pixels), used-indices set.
- **`inspect_image`** — Image-bank region pixel data + identity metrics (`color_count`, `fill_ratio`, `symmetry`).
- **`inspect_animation`** — Cross-region Jaccard / per-pair diff metrics for paired sprite frames (walk1↔walk2 etc.).
- **`inspect_tilemap`** — Tilemap usage map + (0,0)-tile trap detection (catches the Pyxel footgun where empty tilemap cells render as whatever sprite happens to be at bank origin).

### Audit / discovery / audio

- **`validate`** — Static analysis: syntax + 10 anti-pattern detectors (`cls_missing`, `palette_animation`, `tilemap_zero_zero`, `update_in_draw`, `iter_modify`, …).
- **`pyxel_info`** — Versions (pyxel-mcp / Pyxel / Python), examples list, resource URIs.
- **`render_audio`** — Render a `pyxel.sounds[N]` or `pyxel.musics[N]` slot to WAV; return `notes`, `peak_amplitude`, `warnings`.

### Frame analyzer

- **`compare_frames`** — Pixel-wise diff of two PNGs: `identical`, `diff_ratio`, bounding box of changes.

## Resources

- `pyxel://run-snapshots-schema` — Full schema for the `run` tool's `snapshots` parameter (5 kinds × multi-frame syntax). Read once; reuse the patterns.
- `pyxel://api-reference`, `pyxel://user-guide`, `pyxel://mml-commands`, `pyxres://pyxres-format` — live-fetched official Pyxel docs (24h cache).
- `pyxel://palette/default` — 16-color default palette table with hex/RGB/use hints.
- `pyxel://examples/<name>` — Pyxel's bundled example scripts (`02_jump_game`, `09_shooter`, …).

In Claude Code, reference them with `@pyxel:examples/02_jump_game`, `@pyxel:run-snapshots-schema`.

## Why this exists

LLM agents writing Pyxel code without verification produce shortcut games — placeholder rectangles, stalled play loops, missing assets, or scripts that pass syntax checks but render a black screen. `pyxel-mcp` is the verb library that lets an agent **see** what its code does:

- **Headless + fast-forward.** A 600-frame run takes < 1 second. The harness overrides Pyxel's internal fps so `flip()` doesn't pace real-time.
- **Subprocess isolation.** Each tool call is a fresh Python subprocess. No leaked Pyxel state between calls; deterministic with `random_seed=`.
- **Structured output.** Every tool returns JSON with a consistent error shape; agents can chain calls and predicate on observed values, not on stdout strings.
- **Pyxel-specific footguns caught structurally.** The (0,0) tilemap trap, draw-without-cls ghost trails, palette animation in update, run-outside-init — all detected by `validate` and `inspect_*` rather than waiting for a screenshot to look wrong.

Pair this with [`pyxel-skill`](https://github.com/kitao/pyxel-skill) for end-to-end "make me a Donkey Kong" workflows, or use the verbs standalone for any Pyxel CI/QA pipeline.

## Install

```bash
pip install pyxel-mcp
# or use uvx for ephemeral runs
uvx pyxel-mcp --version
```

Register as an MCP server. For Claude Code, add to `.mcp.json`:

```json
{
  "mcpServers": {
    "pyxel": {
      "type": "stdio",
      "command": "pyxel-mcp"
    }
  }
}
```

Pyxel ≥ 2.9.4 required (the harness depends on `set_btn` / `set_btnv` / `set_mouse_pos` and `screen.save` APIs).

## MCP Registry

`mcp-name: io.github.kitao/pyxel-mcp`

## License

MIT
