# Change Log

## 0.2.0

- Overhauled MCP server instructions with comprehensive Pyxel API guide
  - Added app structure patterns (class-based game loop, static image)
  - Added drawing API quick reference (all 16 drawing functions)
  - Added sprite drawing details (colkey, flip, rotate/scale, animation)
  - Added input API (btn/btnp/btnr, key constants, mouse)
  - Added audio playback (play/playm/stop with loop and resume)
  - Added math utilities (sin/cos use degrees, rndi/rndf, atan2)
  - Added camera & effects (camera, clip, pal, dither)
  - Added MML quick reference for music composition
  - Added Music class usage for multi-channel music
  - Added Advanced section (Tilemap.collide, custom Font, image/TMX loading, wavetable, PCM)
  - Improved existing sections: tilemap pget/pset, sound effects h/q, FONT_WIDTH constant
- Fixed error messages to suggest `pip install pyxel-mcp` instead of `pip install pyxel`

## 0.1.11

- Added pyxel as a package dependency for seamless installation via uvx and pipx

## 0.1.10

- Restored mcp-name in README for MCP Registry package ownership verification

## 0.1.9

- Moved development guide from CLAUDE.md into MCP server instructions for all AI agents
- Removed CLAUDE.md (no longer needed as a separate file)
- Updated README with MCP Registry as the primary getting started path
- Enhanced tilemap documentation with detailed format explanation and multi-row examples

## 0.1.8

- Added title and websiteUrl to MCP Registry metadata for search discoverability

## 0.1.7

- Fixed screenshot timing: capture after draw instead of after update for accurate frame content
- Added error handling for WAV analysis in render_audio
- Added fallback for sound.total_sec() in audio harness
- Added missing parameters (timeout, duration_sec) to CLAUDE.md tool signatures

## 0.1.6

- Added PyPI metadata (keywords, classifiers, author, project URLs) for discoverability

## 0.1.5

- Added `inspect_sprite` tool for reading sprite pixel data, symmetry, and colors
- Added `inspect_layout` tool for analyzing text positioning and layout balance
- Added `capture_frames` tool for capturing screenshots at multiple frame points
- Enhanced `render_audio` with musical analysis (key detection, intervals, rhythm, role suggestion)

## 0.1.4

- Prevented zombie processes on subprocess timeout
- Avoided importing Pyxel in the server process (use importlib.util.find_spec)
- Added parameter validation (frames, scale, timeout, sound_index, duration_sec)
- Added safe stderr decoding and truncation
- Moved WAV analysis to a background thread to prevent event loop blocking
- Unified description text across project files

## 0.1.3

- Added Pyxel installation check to run_and_capture and render_audio
- Pinned mcp dependency to <2.0.0

## 0.1.2

- Added MCP Registry metadata

## 0.1.0

- Initial release with run_and_capture, render_audio, and pyxel_info tools
