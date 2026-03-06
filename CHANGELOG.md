# Change Log

## 0.4.0

- Restructured instructions: deduplicated content, reorganized 24→23 sections with logical grouping
- Merged Color Palette + Color Hierarchy + Genre Palettes → Color Palette & Hierarchy
- Merged Screen Layout + Text Layout → Screen & Text Layout
- Merged Common Mistakes + Game Polish Checklist → Quality Checklist (reference-based)
- Moved Screen Shake + Hitstop → Visual Feedback section
- Moved Parallax Scrolling → Background Design section
- Split Visual Design Guide into Background Design / Title Screen Design / Visual Feedback
- Added pixel art rules (3-color-per-material, outlines, size guidelines, anti-patterns)
- Added 8 ready-to-use 8x8 sprite templates (ship, character, slime, coin, heart, skull, shield, sword)
- Added sound effects cookbook with 10 copy-paste SE definitions
- Added game feel constants (platformer physics, variable jump, coyote time, knockback, shooter, puzzle, hitbox, camera)
- Added genre color palettes (space, forest, dungeon, castle, underwater, Game Boy)
- Fixed tilemap bltm example size mismatch (128x128 → 32x24)
- Fixed GRAVITY inconsistency between Game Patterns and Game Feel Constants

## 0.3.1

- Added visual design guide to instructions (background tiers, color hierarchy, title screen design, visual feedback patterns)
- Enhanced common mistakes table with visual design anti-patterns
- Improved game polish checklist with background art, color hierarchy, and HUD guidance
- Based on analysis of 142 Pyxel user examples

## 0.3.0

- Added common mistakes table to instructions
- Added animation timing guide with frame count recommendations
- Added game patterns (platformer, shooter, scene management)
- Added error recovery guidance for each tool
- Added tool output interpretation guide
- Added coordinate system documentation
- Added screen layout guidelines (center main play area, vertical/horizontal centering)
- Added game polish checklist (BGM, SE, title screen, game over, controls)
- Added SE design guidance (use square wave, volume 5-7, cover all core actions)
- Added venv execution guidance for letting users play games
- Added turbo mode to harnesses (FPS override + draw skip for non-target frames)
- Added uv.lock to .gitignore
- Removed unused variable in frames_harness.py

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
