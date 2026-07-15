# Run Snapshot Schema

Reference for the `run` tool's `snapshots` parameter. Use this to construct
snapshot entries when calling `run`.

`snapshots` is a `list[dict]` — each dict is one snapshot entry. The entry
must include `"kind"` plus kind-specific fields described below.

## Output paths — always absolute

Snapshot fields that name output files (`output` for `screen_image` /
`video`, `output_pattern` for multi-frame `screen_image`) **must be
absolute paths**. Relative paths and unexpanded `~` paths are validation
errors. Construct paths with `os.path.abspath(...)`,
`pathlib.Path(...).resolve()`, or an already-expanded absolute temp path.

---

## Snapshot Kinds (4)

### state — `attrs` path syntax

The `state` snapshot kind reads attributes from the App instance (or the
imported module if no App class was found). Each entry in `attrs` is a
dotted path resolved against the target — there are two consistent
mistakes worth flagging up front:

- **Do not include `self.`**. The path is evaluated against the App
  instance directly, so write `player.x`, not `self.player.x`.
- **No function calls or expressions**. `len(hazards)` and similar
  derived values are not allowed in the path. Expose the value as a
  plain attribute first (`self.n_hazards = len(self.hazards)` in
  `update`), then read it as `n_hazards`.

Both mistakes are reported in the snapshot's `warnings` list with a
specific hint message, so they surface without having to trace silent
zero values.

### 1. screen_image

Saves a PNG screenshot of the Pyxel screen at a given frame.

**Input — single-frame:**
```json
{
  "kind": "screen_image",
  "frame": <int>,
  "output": "<absolute path>.png",
  "scale": 1
}
```

**Input — multi-frame:**
```json
{
  "kind": "screen_image",
  "frames": <list[int] | range-string>,
  "output_pattern": "<absolute path>/{frame}_screen.png",
  "scale": 1
}
```

- `scale`: integer zoom factor; nearest-neighbor only (no smoothing). Default `1`.
- `output` and `output_pattern` are mutually exclusive (validation error if both present).
- Both output forms must end with `.png`.
- `output_pattern` must contain `{frame}` — substituted as a 5-digit zero-padded integer
  (e.g. frame 3 → `00003`).
- Single-frame uses `frame` + `output`; multi-frame uses `frames` + `output_pattern`.

**Output per frame:**
```json
{
  "kind": "screen_image",
  "frame": <int>,
  "path": "<absolute-path>.png",
  "size": [<width>, <height>]
}
```

---

### 2. screen_grid

Returns the screen as a 2-D grid of palette indices, row-major.
Useful for verifying exact pixel-level state without image files.

**Input — single-frame:**
```json
{
  "kind": "screen_grid",
  "frame": <int>,
  "bbox": [x, y, w, h]
}
```

**Input — multi-frame:**
```json
{
  "kind": "screen_grid",
  "frames": <list[int] | range-string>,
  "bbox": [x, y, w, h]
}
```

- `bbox`: `[x, y, w, h]` — pixel rectangle to capture. `null` or omitted → full screen.

**Output per frame:**
```json
{
  "kind": "screen_grid",
  "frame": <int>,
  "region": {"x": <int>, "y": <int>, "w": <int>, "h": <int>},
  "grid": [[<palette-index>, ...], ...]
}
```

- `grid`: list of rows, each row a list of palette indices 0–15.
- Input field `bbox` (list `[x, y, w, h]`) is preserved for ergonomic call
  sites; output emits `region` (dict `{x, y, w, h}`), matching the shape used
  by `read_image`, `read_tilemap`, and `diff_frames` so consumers can
  read region geometry uniformly across tools.
- `region` in output reflects the actual region captured (full screen dimensions if input `bbox` was null).

---

### 3. state

Reads attribute values from the running `App` instance. Useful for verifying
game logic (scores, positions, flags) without image comparison.

**Input — single-frame:**
```json
{
  "kind": "state",
  "frame": <int>,
  "attrs": ["player.x", "score", "hazards[0].y"]
}
```

**Input — multi-frame:**
```json
{
  "kind": "state",
  "frames": <list[int] | range-string>,
  "attrs": ["player.x", "score"]
}
```

**Output per frame:**
```json
{
  "kind": "state",
  "frame": <int>,
  "values": {"player.x": 64, "score": 100},
  "warnings": []
}
```

**Attr path syntax:**
- Dotted: `"player.x"` resolves to `app.player.x`
- Indexed: `"hazards[0].y"` resolves to `app.hazards[0].y`
- Combinations: `"enemies[2].pos.x"` resolves to `app.enemies[2].pos.x`
- `attrs: null` (or omit key): returns the App's top-level scalar primitives only
  (int, float, str, bool, None). Lists, dicts, and custom objects are skipped.
- `attrs: []` (explicit empty list): returns `values: {}` (reads nothing).
- Aggregate functions such as `len(...)` are NOT supported.

**Value serialization rules:**
- Primitive types (int, float, str, bool, None): passed through as-is.
- Lists and dicts of primitives: serialized as JSON.
- Custom objects: `repr()` result, truncated to 200 characters with `<truncated>` appended.
- NumPy arrays: converted to nested Python lists.

---

### 4. video

Encodes a frame range to GIF or MP4. Unlike other kinds, `video` does not
accept `frames` (range-string or list). Use `start_frame`/`end_frame` instead.

**Input:**
```json
{
  "kind": "video",
  "start_frame": 0,
  "end_frame": 60,
  "fps": 30,
  "output": "<absolute path>.gif",
  "scale": 1
}
```

- `start_frame`: first frame to include (inclusive). Must be >= 0.
- `end_frame`: last frame (exclusive). Must be <= `frames` (the `run` `frames` parameter).
- `start_frame` must be strictly less than `end_frame`.
- `fps`: frames per second for playback. Default `30`.
- `output`: file path; extension determines format — `.gif` or `.mp4`.
- `scale`: integer zoom factor; nearest-neighbor only. Default `1`.
- `frames` range syntax NOT accepted for video — use `start_frame`/`end_frame` only.

**Output:**
```json
{
  "kind": "video",
  "path": "<absolute-path>",
  "format": "gif",
  "frames_encoded": 60,
  "duration_seconds": 2.0,
  "warnings": []
}
```

**Encoding details:**
- `.gif`: PIL `Image.save()` with `append_images`, `loop=0`,
  `duration=int(1000/fps)`.
- `.mp4`: ffmpeg invoked via subprocess.
- **ffmpeg fallback**: if ffmpeg is unavailable, the harness rewrites `path` to `.gif`,
  sets `format: "gif"`, and appends a warning to `warnings`.

---

## Multi-Frame Syntax

Use `frames` (instead of `frame`) to capture multiple frames in a single snapshot entry.
Applies to: `screen_image`, `screen_grid`, `state`.
Does NOT apply to: `video` (use `start_frame`/`end_frame`).

### Range-string grammar

```
range  := "all" | num ":" num [ ":" num ]
num    := non-negative integer (no sign, no whitespace)
```

| Form | Meaning |
|------|---------|
| `"all"` | Equivalent to `"0:frames"` (all game frames) |
| `"start:end"` | Half-open interval `range(start, end)` |
| `"start:end:step"` | Explicit step, equivalent to `range(start, end, step)` |

**Valid examples:**
- `"0:10"` → frames 0–9
- `"5:20:3"` → frames 5, 8, 11, 14, 17
- `"all"` → every frame the game ran

**Not supported (validation error):**
- `":10"` (open-ended start)
- `"100:"` (open-ended end)
- `":"` (fully open)

**Constraints:**
- `start >= 0`
- `end <= frames` (the `run` `frames` parameter)
- `start < end`
- `step >= 1`

### frames as a list

`frames` may also be a plain list of integers:
```json
{ "kind": "state", "frames": [0, 5, 10, 29], "attrs": ["score"] }
```

List normalization: the harness sorts ascending and deduplicates. A warning is
appended if either operation changed the list.

### Field consistency rules

Single-frame mode:
- Use `frame: int`
- For `screen_image`: use `output: str`

Multi-frame mode:
- Use `frames: list[int] | range-string`
- For `screen_image`: use `output_pattern: str` (must contain `{frame}`)

Mismatches are validation errors:
- `frame` + `output_pattern` → error
- `frames` + `output` → error
- `frame` and `frames` both present → error
- `output` and `output_pattern` both present → error

---

## Frame-Bounds Validation

Every resolved frame index must satisfy:

```
0 <= frame < frames
```

where `frames` is the `run` tool's `frames` parameter (total frame count).

This applies to all snapshot kinds:
- Single-frame: the `frame` value is checked directly.
- Multi-frame: every element of the resolved list is checked.
- Video: `start_frame >= 0`, `end_frame <= frames`, `start_frame < end_frame`.

Out-of-bounds frames are validation errors returned in `errors` — the run
aborts before executing.

---

## Result Ordering

Per-frame snapshot results appear in chronological frame order. Requests for the
same frame retain their input order. Deferred `"end"` snapshots follow per-frame
results, and video results are appended last; each group retains input order.

**Example:** if `snapshots` is:
```json
[
  { "kind": "state", "frames": "0:3", "attrs": ["score"] },
  { "kind": "screen_image", "frame": 5, "output": "/tmp/end.png" }
]
```
The result list contains state@0, state@1, state@2, then screen_image@5.

## The `"end"` frame token

`state`, `screen_image`, and `screen_grid` accept `"frame": "end"`.
The snapshot fires at the last completed frame, whatever stopped the run: the
`frames` cap, an `until` condition match, or stall detection. Crashed runs
skip `"end"` snapshots because their final frame did not complete. The result
reports the concrete frame number, not the string `"end"`.

`"end"` is valid only in the single `frame` field — not inside `frames` lists
or ranges, and not for `video`.

Combine with `run(until=...)` to capture the moment a condition first holds:

```json
{
  "until": "score >= 1",
  "snapshots": [
    {"kind": "state", "frame": "end", "attrs": ["score"]},
    {"kind": "screen_image", "frame": "end", "output": "/tmp/goal.png"}
  ]
}
```

`until` is a Python expression over App attributes, evaluated after each
frame. Undefined names count as "not yet satisfied" (warned once in `log`).
The run result reports `until_met` and the reached `frame_count`.
