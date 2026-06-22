# pyxel-mcp

MCP server for [Pyxel](https://github.com/kitao/pyxel), a retro game engine for Python. It gives AI agents a compact set of verbs to run and observe Pyxel programs without a window: headless, deterministic, and scriptable.

The server is deliberately an observation adapter. It does not judge whether a game is good. Agents use the returned state, pixels, audio, docs, and diffs to make task-specific decisions.

## Why this exists

LLM agents writing Pyxel code without feedback often stop at "the script runs". pyxel-mcp closes that loop:

- **Headless runs.** Drive frame counts and scheduled inputs without opening a window.
- **Subprocess isolation.** Each tool call starts fresh; Pyxel state cannot leak between calls.
- **Structured output.** Tools return JSON with uniform `ok` / `errors` fields.
- **Pyxel footguns.** `validate` and resource readers expose common mistakes such as missing `cls`, missing `colkey`, tilemap `(0, 0)` traps, and ragged image rows.
- **No universal quality score.** The agent writes the predicates that matter for the current game and visually inspects captured PNGs.

## Install

Register as an MCP server in your client. The CLI prints the exact snippet:

```bash
uvx pyxel-mcp install
```

Paste the printed JSON into your client's MCP config:

- **Claude Code**: `~/.claude/.mcp.json` or per-project `.mcp.json`
- **Cursor**: `~/.cursor/mcp.json`
- **Codex CLI**: `~/.codex/mcp.json`

Snippet:

```json
{
  "mcpServers": {
    "pyxel": {
      "command": "uvx",
      "args": ["pyxel-mcp"]
    }
  }
}
```

Restart your client. The server logs a startup line to stderr so you can confirm it loaded:

```text
[pyxel-mcp] starting - 9 tools
```

Pyxel >= 2.9.6 is installed as a dependency.

For workflow guidance, install the separate `pyxel-skill` repository. pyxel-mcp does not ship or publish skills.

## Tools

| Tool | Purpose |
|---|---|
| `run` | Drive N frames headlessly. Supports inputs plus `screen_image`, `screen_grid`, `state`, `layout`, and `video` snapshots. |
| `validate` | Syntax and common Pyxel anti-pattern checks. |
| `pyxel_info` | Version, path, example, and resource discovery. |
| `read_palette` | Palette state, used indices, hierarchy hints, and contrast warnings. |
| `read_image` | Image-bank region pixels and optional rendered PNG. |
| `read_animation` | Adjacent sprite-frame consistency and per-pair diffs. |
| `read_tilemap` | Tile usage, non-empty region, and `(0, 0)` trap warning. |
| `read_audio` | Render a sound or music target to WAV and return duration, peak, notes, warnings. |
| `diff_frames` | Pixel-wise diff between two PNG files. |

## Minimal loop

1. Run `validate` before the first dynamic run.
2. Use `run` with a `state` snapshot and a `screen_image` at the frame being verified.
3. Inspect the captured PNG yourself; pixels are the player-facing truth.
4. Add `read_*` or `diff_frames` only when the task needs that specific observation.
5. Keep proof bundles and long reports for release/audit requests, not for every small game.

## Resources

- `pyxel://run-snapshots-schema` - full grammar for `run.snapshots`.
- `pyxel://anti-patterns` - `validate` issue catalog.
- `pyxel://api-reference`, `pyxel://user-guide`, `pyxel://mml-commands`, `pyxel://pyxres-format` - Pyxel docs.
- `pyxel://palette/default` - default palette table.
- `pyxel://examples/<name>` - bundled Pyxel examples.

## Update

`uvx` caches packages. Force a refresh with:

```bash
uvx --refresh-package pyxel-mcp pyxel-mcp install
```

## Troubleshooting

**Tools do not appear.** Look for `[pyxel-mcp] starting - 9 tools` in client logs, then restart the client if the config changed.

**A script crashes on `pyxel.init()`.** User scripts should call `pyxel.init()` once. Tool calls are isolated subprocesses, so repeated runs should go through pyxel-mcp rather than re-importing a script in the same process.

**A validation issue is unfamiliar.** Read `pyxel://anti-patterns`.

## MCP Registry

`mcp-name: io.github.kitao/pyxel-mcp`

## License

MIT
