# Change Log

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
