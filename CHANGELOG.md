# Change Log

## 0.10.0

- Redesign tool surface from 16 to 9 tools
- Add `run` primitive with scheduled inputs and 5 snapshot kinds
- Support `screen_image`, `screen_grid`, `state`, `layout`, `video` snapshots
- Support multi-frame snapshots via list or range string syntax
- Parse `ASSERT PASS|FAIL` lines from stdout into structured assertions
- Add `inspect_palette` with WCAG contrast and 3-layer hierarchy
- Add `inspect_image` for image bank region pixel analysis
- Add `inspect_animation` with cross-region Jaccard metrics
- Add `inspect_tilemap` with (0,0)-tile trap detection
- Add `compare_frames` for pixel-wise PNG diff
- Replace `validate_script` with `validate` (10 anti-pattern detectors)
- Read subprocess JSON payload from stdin instead of argv
- Inject `random_seed` at pre-loop checkpoint for deterministic runs
- Unify error shape across all tools as `errors: list[ToolError]`
- Bump Pyxel minimum version to 2.9.4
- Trim instructions.md and migrate design knowledge to pyxel-skill
- Add `pyxel://run-snapshots-schema` MCP resource
- Add Python 3.14 classifier
- Override Pyxel internal fps in headless harness for fast-forward runs
- Filter inspect_palette contrast warnings to co-located pixel pairs

## 0.9.2

- Add update notifications in pyxel_info for pyxel-mcp and pyxel
- Use marker prefix for harness JSON to prevent user print misdetection
- Extract run_harness_raw helper to reduce subprocess duplication
- Unify state_harness with patch_game_loop via on_run callback
- Make pyxel_info async to avoid blocking on version check
- Rename frames→frame parameter for single-frame tools
- Fix duplicate pyxel.run() warning when found in draw()
- Add inspect_animation and capture_frames to workflow instructions
- Clarify MML vs set() volume scale difference in instructions
- Add format_palette_report and analyze_wav tests
- Add integration marker to Pyxel-dependent tests

## 0.9.1

- Bump Pyxel minimum version to 2.8.9
- Replace monkey-patched input simulation with native set_btn/set_mouse_pos API
- Remove manual flip counters; use Pyxel's frame_count in headless flip path
- Add pre_update callback to patch_game_loop for input injection timing

## 0.9.0

- Split server.py into focused modules (_errors, _palette, _audio, _format, _validate, _subprocess)
- Extract instructions to external Markdown file loaded at startup
- Accelerate WAV frequency analysis ~50-100x with numpy FFT autocorrelation
- Add numpy as direct dependency
- Add inspect_animation tool for sprite sheet consistency checking
- Enhance inspect_sprite with outline detection, pillow shading, material hints
- Enhance inspect_palette with WCAG 2.0 contrast and 3-layer color hierarchy analysis
- Enhance inspect_layout with font height auto-estimation and grid alignment check
- Expand validate_script anti-patterns: blt without colkey, list mutation, run outside init
- Add unified output format with Analysis/Suggestions sections across all inspection tools
- Unify harness boilerplate via _headless.py helpers (setup_harness, patch_game_loop)
- Decompose layout_harness analysis into testable functions
- Add comprehensive test suite (174 tests covering all modules)

## 0.8.3

- Bump Pyxel minimum version to 2.8.8 (Tilemap u16 type change)
- Document headless mouse simulation as shadow attributes

## 0.8.2

- Fix Pyxel minimum version: require >=2.8.7 for screenshot(filename) API

## 0.8.1

- Add Beyond Defaults section documenting extensible resources
- Remove fixed upper-bound clamps on tool index parameters
- Support extended palette (16+ colors) in hex grid output
- Fix tilemap imgsrc serialization for custom Image instances
- Remove unused variables in _suggest_role
- Update example range from 01-18 to 01-19

## 0.8.0

- Optimize headless execution with fps override for near-instant captures
- Switch screenshot capture from pyxel.screen.save() to pyxel.screenshot()
- Change default scale from 2 to 1 to reduce image token usage
- Unify screen pixel reads to pyxel.pget() public API
- Add missing sys.stdout.flush() to audio and sprite harnesses
- Align README tool descriptions with server.py docstrings
- Upgrade Pyxel compatibility to 2.8.7

## 0.7.7

- Add pyxres-format.md to Pyxel Reference URLs

## 0.7.6

- Added SDL_AUDIODRIVER=dummy to suppress audio during headless execution
- Extracted common headless init and script execution into _headless.py

## 0.7.5

- Replaced inline API docs with references to official Pyxel docs
- Switched reference URLs from kitao.github.io JSON to GitHub docs/ markdown
- Added user guide URL to Pyxel Reference section

## 0.7.4

- Updated reference URLs from wasm/ to web/ path

## 0.7.3

- Bumped minimum Pyxel version to 2.8.0
- Added blt3d/bltm3d (Mode-7 perspective) to instructions
- Fixed harness hang caused by quit() no longer force-exiting in 2.8.0

## 0.7.2

- Added gen_bgm preset and instrumentation details to instructions

## 0.7.1

- Trimmed SE cookbook, genre palettes, and redundant constant tables
- Removed sprite templates to encourage original designs per game
- Added layout entries to quality checklist
- Changed layout guidance to derive screen size from content, not fixed dimensions
- Added ⚠ warnings for margin asymmetry, imbalance, and empty quadrants
- Enhanced inspect_layout with vertical balance, margins, quadrants, and center of mass

## 0.7.0

- Bumped minimum Pyxel version to 2.7.11
- Added headless init to audio and sprite harnesses
- Added music rendering support to render_audio
- Switched all harnesses from turbo mode to native headless mode

## 0.6.0

- Strengthened quality checklist with sprite/level/audio items
- Added decorative element patterns (torch flames, dripping water)
- Added genre background recipes (castle, forest, space)
- Added enemy design patterns (patrol, chase, sine float, swoop)
- Added level design principles (zone structure, pacing, enemy placement)
- Added guidance to mix gen_bgm with hand-written MML
- Added MML composition guide with genre mood table
- Added sprite design process with min animation frame requirements
- Documented tilemap (0,0) default trap and imgsrc property
- Added stdout capture (print output) to text-based tools
- Added multi-frame timeline support to inspect_state
- Added inspect_bank tool for image bank visualization
- Added inspect_tilemap tool for tilemap data inspection
- Added inspect_palette tool for color usage analysis
- Added compare_frames tool for visual regression testing
- Added inspect_screen tool for compact color grid capture
- Added validate_script tool for pre-run syntax and anti-pattern checks

## 0.5.0

- Fixed turbo-mode draw skipping in capture harnesses
- Added error hints for common Pyxel mistakes
- Added inspect_state tool for game state debugging
- Added play_and_capture tool for input simulation testing

## 0.4.2

- Fixed harness chdir for scripts using relative asset paths

## 0.4.1

- Strengthened Tilemap.collide() guidance over hand-rolled collision loops
- Added scene-specific gen_bgm pattern with per-scene preset/seed switching
- Added state-based Animator class pattern for multi-state character animation

## 0.4.0

- Fixed GRAVITY inconsistency between Game Patterns and Game Feel Constants
- Fixed tilemap bltm example size mismatch (128x128 → 32x24)
- Added genre color palettes (space, forest, dungeon, castle, underwater, Game Boy)
- Added game feel constants (platformer physics, variable jump, coyote time, knockback, shooter, puzzle, hitbox, camera)
- Added sound effects cookbook with 10 copy-paste SE definitions
- Added 8 ready-to-use 8x8 sprite templates (ship, character, slime, coin, heart, skull, shield, sword)
- Added pixel art rules (3-color-per-material, outlines, size guidelines, anti-patterns)
- Split Visual Design Guide into Background Design / Title Screen Design / Visual Feedback
- Moved Parallax Scrolling → Background Design section
- Moved Screen Shake + Hitstop → Visual Feedback section
- Merged Common Mistakes + Game Polish Checklist → Quality Checklist (reference-based)
- Merged Screen Layout + Text Layout → Screen & Text Layout
- Merged Color Palette + Color Hierarchy + Genre Palettes → Color Palette & Hierarchy
- Restructured instructions: deduplicated content, reorganized 24→23 sections with logical grouping

## 0.3.1

- Based on analysis of 142 Pyxel user examples
- Improved game polish checklist with background art, color hierarchy, and HUD guidance
- Enhanced common mistakes table with visual design anti-patterns
- Added visual design guide to instructions (background tiers, color hierarchy, title screen design, visual feedback patterns)

## 0.3.0

- Removed unused variable in frames_harness.py
- Added uv.lock to .gitignore
- Added turbo mode to harnesses (FPS override + draw skip for non-target frames)
- Added venv execution guidance for letting users play games
- Added SE design guidance (use square wave, volume 5-7, cover all core actions)
- Added game polish checklist (BGM, SE, title screen, game over, controls)
- Added screen layout guidelines (center main play area, vertical/horizontal centering)
- Added coordinate system documentation
- Added tool output interpretation guide
- Added error recovery guidance for each tool
- Added game patterns (platformer, shooter, scene management)
- Added animation timing guide with frame count recommendations
- Added common mistakes table to instructions

## 0.2.1

- Added .mcp.json for local development with Claude Code

## 0.2.0

- Fixed error messages to suggest pyxel-mcp instead of pyxel
- Overhauled MCP server instructions with comprehensive Pyxel API guide

## 0.1.11

- Added pyxel as a package dependency for seamless installation via uvx and pipx

## 0.1.10

- Restored mcp-name in README for MCP Registry verification

## 0.1.9

- Enhanced tilemap documentation with multi-row examples
- Updated README with MCP Registry as the primary setup path
- Removed CLAUDE.md (no longer needed as a separate file)
- Moved development guide from CLAUDE.md into MCP server instructions

## 0.1.8

- Added title and websiteUrl to MCP Registry metadata

## 0.1.7

- Added missing parameters to CLAUDE.md tool signatures
- Added fallback for sound.total_sec() in audio harness
- Added error handling for WAV analysis in render_audio
- Fixed screenshot timing to capture after draw instead of update

## 0.1.6

- Added PyPI metadata for discoverability

## 0.1.5

- Enhanced render_audio with musical analysis
- Added capture_frames tool for multi-frame screenshots
- Added inspect_layout tool for analyzing text positioning
- Added inspect_sprite tool for reading sprite pixel data

## 0.1.4

- Unified description text across project files
- Moved WAV analysis to a background thread
- Added safe stderr decoding and truncation
- Added parameter validation for all tool inputs
- Avoided importing Pyxel in the server process
- Prevented zombie processes on subprocess timeout

## 0.1.3

- Pinned mcp dependency to <2.0.0
- Added Pyxel installation check to run_and_capture and render_audio

## 0.1.2

- Added MCP Registry metadata

## 0.1.0

- Initial release with run_and_capture, render_audio, and pyxel_info tools
