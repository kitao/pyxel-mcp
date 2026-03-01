# pyxel-mcp

MCP server for [Pyxel](https://github.com/kitao/pyxel), a retro game engine for Python. Enables AI to autonomously run, verify, and iterate on retro game programs.

## Features

- **`run_and_capture`** — Run a Pyxel script and capture a screenshot for visual verification
- **`capture_frames`** — Capture screenshots at multiple frame points for animation verification
- **`inspect_sprite`** — Read sprite pixel data from image banks, report symmetry and colors
- **`inspect_layout`** — Analyze screen layout, text positioning, and visual balance
- **`render_audio`** — Render a Pyxel sound to WAV and analyze notes, rhythm, and key
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
