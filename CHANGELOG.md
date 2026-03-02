# Change Log

## 0.2.1

- Added .mcp.json for local development with Claude Code

## 0.2.0

- Overhauled MCP server instructions with comprehensive Pyxel API guide
- Fixed error messages to suggest pyxel-mcp instead of pyxel

## 0.1.11

- Added pyxel as a package dependency for seamless installation via uvx and pipx

## 0.1.10

- Restored mcp-name in README for MCP Registry verification

## 0.1.9

- Moved development guide from CLAUDE.md into MCP server instructions
- Removed CLAUDE.md (no longer needed as a separate file)
- Updated README with MCP Registry as the primary setup path
- Enhanced tilemap documentation with multi-row examples

## 0.1.8

- Added title and websiteUrl to MCP Registry metadata

## 0.1.7

- Fixed screenshot timing to capture after draw instead of update
- Added error handling for WAV analysis in render_audio
- Added fallback for sound.total_sec() in audio harness
- Added missing parameters to CLAUDE.md tool signatures

## 0.1.6

- Added PyPI metadata for discoverability

## 0.1.5

- Added inspect_sprite tool for reading sprite pixel data
- Added inspect_layout tool for analyzing text positioning
- Added capture_frames tool for multi-frame screenshots
- Enhanced render_audio with musical analysis

## 0.1.4

- Prevented zombie processes on subprocess timeout
- Avoided importing Pyxel in the server process
- Added parameter validation for all tool inputs
- Added safe stderr decoding and truncation
- Moved WAV analysis to a background thread
- Unified description text across project files

## 0.1.3

- Added Pyxel installation check to run_and_capture and render_audio
- Pinned mcp dependency to <2.0.0

## 0.1.2

- Added MCP Registry metadata

## 0.1.0

- Initial release with run_and_capture, render_audio, and pyxel_info tools
