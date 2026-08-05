# pyxel-mcp

[![MCP Toplist](https://mcptoplist.com/badge/io.github.kitao%2Fpyxel-mcp.svg)](https://mcptoplist.com/server/io.github.kitao%2Fpyxel-mcp)

An MCP server for observing programs built with [Pyxel](https://github.com/kitao/pyxel). It runs trusted local scripts headlessly and returns structured state, pixels, assets, audio, and frame differences.

[![PyPI](https://img.shields.io/pypi/v/pyxel-mcp)](https://pypi.org/project/pyxel-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/pyxel-mcp)](https://pypi.org/project/pyxel-mcp/)
[![Tests](https://img.shields.io/github/actions/workflow/status/kitao/pyxel-mcp/test.yml?branch=main&label=tests)](https://github.com/kitao/pyxel-mcp/actions/workflows/test.yml)
[![License](https://img.shields.io/pypi/l/pyxel-mcp)](LICENSE)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-io.github.kitao%2Fpyxel--mcp-blue)](https://registry.modelcontextprotocol.io)

The server deliberately reports facts rather than a universal quality score. The agent using it chooses the checks that matter for the game.

## Install

With Claude Code:

```bash
claude mcp add pyxel -- uvx pyxel-mcp
```

For another MCP client, run `uvx pyxel-mcp install` or add:

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

Restart the client after changing its configuration. The server writes this diagnostic to stderr:

```text
[pyxel-mcp] starting - 8 tools
```

Python 3.11+ is required, and Pyxel >= 2.9.6 is installed as a dependency. Script tools execute local Python in subprocesses to isolate Pyxel state, but they do not sandbox untrusted code. See [SECURITY.md](SECURITY.md).

## Tools

Every `script` argument is a file path, not Python source.

| Tool | Returns |
|---|---|
| `validate` | Syntax errors and recognizable Pyxel code patterns. |
| `run` | Headless frames, scheduled input, logs, and `state`, `screen_image`, `screen_grid`, or `video` snapshots. |
| `pyxel_info` | Installed versions, paths, examples, and resource URIs. |
| `read_palette` | Palette colors and image-bank indices in use. |
| `read_image` | Image-bank pixels and an optional PNG render. |
| `read_tilemap` | Tile coordinates, source bank, usage counts, bounds, and an optional render. |
| `read_audio` | A rendered sound or music WAV plus measurable audio data. |
| `diff_frames` | Pixel differences between two PNG files. |

All tools declare input and output schemas. Every result includes `ok` and `errors`.

## Example

Capture state and the screen when a condition first becomes true:

```json
{
  "script": "/absolute/path/game.py",
  "frames": 600,
  "until": "score >= 1",
  "snapshots": [
    {"kind": "state", "frame": "end", "attrs": ["score", "player.x"]},
    {"kind": "screen_image", "frame": "end", "output": "/tmp/goal.png"}
  ]
}
```

Use absolute artifact paths. Read `log` even when `ok` is true, and inspect captured images directly when appearance matters.

## Resources

- `pyxel://run-snapshots-schema` — complete `run.snapshots` grammar.
- `pyxel://validation-patterns` — categories reported by `validate`.
- `pyxel://palette/default` — default palette table.
- `pyxel://examples/{name}` — source for an example bundled with the installed Pyxel package; discover names with `pyxel_info`.

Full game-building guidance lives in the separate [pyxel-skill](https://github.com/kitao/pyxel-skill) project; this package contains only the MCP server.

## Update

`uvx` caches packages. Force a refresh with:

```bash
uvx --refresh-package pyxel-mcp pyxel-mcp install
```

## Troubleshooting

- If tools do not appear, look for the `starting - 8 tools` diagnostic and restart the client.
- If `run` fails, inspect `errors`, `exit_status`, and `log`.
- If a validation category is unfamiliar, read `pyxel://validation-patterns`.

## MCP Registry

`mcp-name: io.github.kitao/pyxel-mcp`

## License

MIT — see [LICENSE](LICENSE).
