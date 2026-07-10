# pyxel-mcp

MCP server for [Pyxel](https://github.com/kitao/pyxel), the retro game engine for Python. It gives AI agents a compact set of verbs to run and observe Pyxel programs without a window — headless, deterministic, and scriptable — so an agent can close the verification loop on the game it just wrote.

[![PyPI](https://img.shields.io/pypi/v/pyxel-mcp)](https://pypi.org/project/pyxel-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/pyxel-mcp)](https://pypi.org/project/pyxel-mcp/)
[![Tests](https://img.shields.io/github/actions/workflow/status/kitao/pyxel-mcp/test.yml?branch=main&label=tests)](https://github.com/kitao/pyxel-mcp/actions/workflows/test.yml)
[![License](https://img.shields.io/pypi/l/pyxel-mcp)](LICENSE)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-io.github.kitao%2Fpyxel--mcp-blue)](https://registry.modelcontextprotocol.io)

## Why this exists

LLM agents writing Pyxel code without feedback stop at "the script runs". pyxel-mcp closes that loop with facts, not judgments:

- **Headless runs.** Drive frame counts, schedule inputs, and stop on a condition (`until="score >= 1"`) without opening a window.
- **Subprocess isolation.** Each tool call starts fresh; Pyxel state cannot leak between calls.
- **Structured output.** Every tool returns JSON with uniform `ok` / `errors` fields and a declared schema.
- **Pyxel footguns.** `validate` and the resource catalog surface common mistakes such as missing `cls`, missing `colkey`, and the tilemap `(0, 0)` trap.
- **No universal quality score.** The agent writes the predicates that matter for the current game and visually inspects captured PNGs.

## See it work

One `run` call takes the game to the moment a condition holds and captures proof:

```json
{
  "script": "/abs/path/game.py",
  "frames": 600,
  "until": "score >= 1",
  "snapshots": [
    {"kind": "state", "frame": "end", "attrs": ["score", "player.x"]},
    {"kind": "screen_image", "frame": "end", "output": "/tmp/goal.png"}
  ]
}
```

Result (excerpt):

```json
{
  "ok": true,
  "until_met": true,
  "frame_count": 42,
  "snapshots": [
    {"kind": "state", "frame": 41, "values": {"score": 1, "player.x": 88.0}},
    {"kind": "screen_image", "frame": 41, "path": "/tmp/goal.png", "size": [160, 120]}
  ]
}
```

The agent then reads `/tmp/goal.png` with its own eyes. State proves mechanics; pixels prove what the player actually sees.

## Quick start

1. Register the server. For Claude Code:

   ```bash
   claude mcp add pyxel -- uvx pyxel-mcp
   ```

   For any other MCP client, `uvx pyxel-mcp install` prints this snippet and where to put it:

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

   - **Claude Code**: `~/.claude/.mcp.json` or per-project `.mcp.json`
   - **Cursor**: `~/.cursor/mcp.json`
   - **Codex CLI**: `~/.codex/mcp.json`

2. Restart your client.

3. Confirm it loaded — the server logs one line to stderr:

   ```text
   [pyxel-mcp] starting - 9 tools
   ```

Pyxel >= 2.9.6 is installed as a dependency. Tools that accept `script` execute that file as trusted local Python — pyxel-mcp isolates Pyxel state per subprocess, but it is not a sandbox for untrusted code (see [SECURITY.md](SECURITY.md)).

For full game-building workflow guidance, pair the server with the separate [pyxel-skill](https://github.com/kitao/pyxel-skill) repository. pyxel-mcp does not ship or publish skills.

## Tools

Every `script` parameter is a path to a Python file, not source code.

| Tool | Purpose |
|---|---|
| `run` | Drive N frames headlessly — or stop early with `until="<condition>"`. Supports scheduled inputs plus `screen_image`, `screen_grid`, `state`, `layout`, and `video` snapshots, including at the `"end"` frame. |
| `validate` | Syntax and common Pyxel anti-pattern checks. |
| `pyxel_info` | Version, path, example, and resource discovery. |
| `read_palette` | Palette state, used indices, hierarchy hints, and contrast warnings. |
| `read_image` | Image-bank region pixels and optional rendered PNG. |
| `read_animation` | Adjacent sprite-frame consistency and per-pair diffs. |
| `read_tilemap` | Tile usage, non-empty region, and `(0, 0)` trap warning. |
| `read_audio` | Render a sound or music target to WAV and return duration, peak, notes, warnings. Music renders a fixed 10-second window. |
| `diff_frames` | Pixel-wise diff between two PNG files. |

## Minimal loop

1. Run `validate` before the first dynamic run.
2. Use `run` with a `state` snapshot and a `screen_image` at the frame being verified — or `until` plus `"frame": "end"` snapshots when the target is "the moment X happens".
3. Inspect the captured PNG yourself; pixels are the player-facing truth.
4. Add `read_*` or `diff_frames` only when the task needs that specific observation.
5. Keep proof bundles and long reports for release/audit requests, not for every small game.

## Resources

- `pyxel://run-snapshots-schema` - full grammar for `run.snapshots`, `until`, and the `"end"` token.
- `pyxel://anti-patterns` - `validate` issue catalog.
- `pyxel://api-reference`, `pyxel://user-guide`, `pyxel://mml-commands`, `pyxel://pyxres-format` - Pyxel docs, fetched live from GitHub with a 24h cache (stale cache served offline).
- `pyxel://palette/default` - default palette table.
- `pyxel://examples/<name>` - the examples bundled with the installed Pyxel; discover names via `pyxel_info`.

## Update

`uvx` caches packages. Force a refresh with:

```bash
uvx --refresh-package pyxel-mcp pyxel-mcp install
```

## Troubleshooting

**Tools do not appear.** Look for `[pyxel-mcp] starting - 9 tools` in client logs, then restart the client if the config changed.

**`run` returns `ok: false`.** Check `exit_status`: `crashed` (script raised), `timeout` (wall-clock cap), `stalled` (no observable change for `stall_window_frames`), or `invalid` (payload rejected before execution). Read `log` even when `ok` is true.

**A script crashes on `pyxel.init()`.** User scripts should call `pyxel.init()` once. Tool calls are isolated subprocesses, so repeated runs should go through pyxel-mcp rather than re-importing a script in the same process.

**A validation issue is unfamiliar.** Read `pyxel://anti-patterns`.

## MCP Registry

`mcp-name: io.github.kitao/pyxel-mcp`

The line above is this repo's ownership marker for the [MCP Registry](https://registry.modelcontextprotocol.io).

## License

MIT — see [LICENSE](LICENSE).
