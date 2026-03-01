# pyxel-mcp

MCP server for [Pyxel](https://github.com/kitao/pyxel), a retro game engine for Python. Enables AI to autonomously run, verify, and iterate on retro game programs.

## Features

- **`run_and_capture`** — Run a Pyxel script and capture a screenshot for visual verification
- **`capture_frames`** — Capture screenshots at multiple frame points for animation verification
- **`inspect_sprite`** — Read sprite pixel data from image banks, report symmetry and colors
- **`inspect_layout`** — Analyze screen layout, text positioning, and visual balance
- **`render_audio`** — Render a Pyxel sound to WAV and analyze notes, rhythm, and key
- **`pyxel_info`** — Get Pyxel installation paths (API stubs, examples)

## Getting Started

Just ask your AI agent (e.g. Claude Code) to create a Pyxel game. The agent will automatically discover and set up pyxel-mcp from the [MCP Registry](https://registry.modelcontextprotocol.io/).

## Manual Installation

1. Install the package:

```bash
pip install pyxel-mcp
```

2. Register `pyxel-mcp` as an MCP server in your AI agent. For Claude Code, add to your project's `.mcp.json`:

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

## License

MIT
