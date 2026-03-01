# pyxel-mcp

MCP server for [Pyxel](https://github.com/kitao/pyxel) that enables AI to autonomously run, verify, and iterate on retro game programs.

## Features

- **`run_and_capture`** — Run a Pyxel script and capture a screenshot for visual verification
- **`render_audio`** — Render a Pyxel sound to WAV and analyze the waveform (note detection, frequency, volume)
- **`pyxel_info`** — Get Pyxel installation paths (API stubs, examples)

## Requirements

- Python 3.10+
- [Pyxel](https://github.com/kitao/pyxel) (`pip install pyxel`)

## Installation

```bash
pip install pyxel-mcp
```

## Usage with Claude Code

Add to your project's `.mcp.json`:

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

Then copy `CLAUDE.md` to your project root to give the AI context about available tools and Pyxel workflows.

## MCP Registry

mcp-name: io.github.kitao/pyxel-mcp

## License

MIT
