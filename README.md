# pyxel-mcp

MCP server for [Pyxel](https://github.com/kitao/pyxel), a retro game engine for Python. Enables AI to autonomously run, verify, and iterate on retro game programs.

## Features

### Run & Capture

- **`run_and_capture`** — Run a Pyxel script and capture a screenshot
- **`capture_frames`** — Capture screenshots at multiple frame points for animation verification
- **`play_and_capture`** — Simulate keyboard/mouse input and capture screenshots

### Inspect & Debug

- **`validate_script`** — Check syntax and common anti-patterns without running Pyxel
- **`inspect_state`** — Read game object attributes at specific frames with timeline diff
- **`inspect_screen`** — Capture screen as a compact color index grid (no image tokens)
- **`compare_frames`** — Compare two frames and report pixel differences

### Visual Analysis

- **`inspect_sprite`** — Read sprite pixel data from image banks, report symmetry and colors
- **`inspect_layout`** — Analyze screen layout, text positioning, and visual balance
- **`inspect_palette`** — Analyze color usage, distribution, and contrast issues
- **`inspect_bank`** — Visualize an entire 256x256 image bank as a screenshot
- **`inspect_tilemap`** — Inspect tilemap content, tile usage, and layout

### Audio

- **`render_audio`** — Render a Pyxel sound to WAV and analyze notes, rhythm, and key

### Utility

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

## MCP Registry

mcp-name: io.github.kitao/pyxel-mcp

## License

MIT
