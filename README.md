[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/kitao-pyxel-mcp-badge.png)](https://mseep.ai/app/kitao-pyxel-mcp)

# pyxel-mcp

MCP server for [Pyxel](https://github.com/kitao/pyxel), a retro game engine for Python. Enables AI to autonomously run, verify, and iterate on retro game programs.

## Features

### Run & Capture

- **`run_and_capture`** — Run a Pyxel script and capture a screenshot after N frames
- **`capture_frames`** — Capture screenshots at multiple frame points for animation verification
- **`play_and_capture`** — Play a game by sending simulated input and capture screenshots

### Inspect & Debug

- **`validate_script`** — Validate a Pyxel script without running it
- **`inspect_state`** — Read game object attributes at specific frames for debugging
- **`inspect_screen`** — Capture screen as a compact color index grid
- **`compare_frames`** — Compare screenshots at two frames and report pixel differences

### Visual Analysis

- **`inspect_sprite`** — Inspect sprite pixel data from a Pyxel image bank
- **`inspect_layout`** — Analyze screen layout, text alignment, and visual balance
- **`inspect_palette`** — Analyze color usage and contrast in a Pyxel screenshot
- **`inspect_bank`** — Visualize an entire Pyxel image bank as a single screenshot
- **`inspect_tilemap`** — Inspect tilemap content, tile usage, and layout
- **`inspect_animation`** — Check sprite sheet consistency across animation frames

### Audio

- **`render_audio`** — Render a Pyxel sound or music to WAV and return waveform analysis

### Utility

- **`pyxel_info`** — Get Pyxel installation info: package location, examples path, and API stubs path

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
