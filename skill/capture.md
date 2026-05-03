# Reference: Proof Bundle Production

Called from `task-execution.md` (intermediate captures) and
`quality-gate.md` (final bundle check). Produces a
`screenshots/result/<N>/` directory containing runnable evidence
that the game functions end-to-end.

## References

- `pyxel://run-snapshots-schema` (MCP resource) — full schema for `video`, `screen_image`, `screen_grid`, `state`, `layout` snapshot kinds used in bundle production.
- `task-execution.md` — calls into this file for intermediate captures.
- `quality-gate.md` — gates final bundle existence + dead-time (check #8) and agent visual review of bundle frames (check #11).

## Bundle structure

For attempt `<N>` (start at 1, increment each new final attempt):

```
screenshots/result/<N>/
├── win-path.gif         — `run` `video` snapshot of full clear
├── lose-path.gif        — `run` `video` snapshot of full death
├── frames/
│   ├── title.png        — `run` `screen_image` snapshot
│   └── ...              (5 frames at TITLE, play_start, mid_game, win, game_over)
├── audio/
│   ├── bgm_ch*.wav      — read_audio with target={"sound": <bgm sound id>}
│   └── se_*.wav         — read_audio per SE manifest entry (target={"sound": N})
└── notes.md             — summary, observations, known issues
```

A single `run` call per path writes the GIF (via a `video` snapshot) and
the milestone frame PNGs (via a multi-frame `screen_image` snapshot)
atomically. `read_audio` writes WAVs via its `output_path` argument.

## Win-path GIF requirements

- Duration: at least the full win-path scenario, typically 20–30 seconds at 30 fps = **600–900 frames**.
- Must show the player traversing from start to goal and ending on the WIN scene.
- Production: `run` `video` snapshot with `start_frame=0, end_frame=<frames>, fps=30, output="screenshots/result/<N>/win-path.gif"`. The `.gif` extension triggers PIL-based encoding (no ffmpeg dependency).
- A bundle whose first 5 seconds look right and then sits static for 20 seconds is FAIL — `diff_frames` between mid and late frames must show meaningful change (Pattern G).

## Lose-path GIF requirements

- Duration: at least until GAME_OVER triggers, typically **≥ 360 frames** (~12 s at 30 fps).
- Must show a hazard appearing, hitting the player, and `lives` decrementing on screen.
- Must end on the GAME_OVER scene.
- Production: `run` `video` snapshot, same shape as win-path with shorter `end_frame`.

For `.mp4` output, the harness falls back to GIF if ffmpeg is unavailable on PATH (spec §6.4.5) — emits a warning and rewrites the path to `.gif`. Either format is accepted by `quality-gate.md` check #8.

## Frame snapshots

Capture key scene transitions in the **same `run` call** that produces the GIF, so the inputs and frame timing are guaranteed to match. Add a multi-frame `screen_image` snapshot to the `snapshots` list:

```python
{
    "frames": [30, 90, 180, 360, 720],
    "kind": "screen_image",
    "output_pattern": "screenshots/result/1/frames/{frame}.png",
    "scale": 2,
}
```

The `{frame}` token expands to a 5-digit zero-padded integer (only this token is supported — `{frame:03d}` and unknown tokens are validation errors). After the run, the files are at `00030.png`, `00090.png`, etc. Rename to `title.png`, `play_start.png`, `mid_game.png`, `win.png`, `game_over.png` per the bundle layout, OR pre-name by issuing five separate single-frame `screen_image` snapshots with literal `output` paths (longer snapshot list, no rename).

## Audio rendering

For every audio cue declared in `ASSETS.md`, render to WAV. **Render against sound slots, not music slots, when you intend the result to satisfy quality-gate check #7** — see the next paragraph for why.

```python
# SE — render the sound slot directly.
read_audio(script="main.py", target={"sound": 10},
             output_path="/abs/path/screenshots/result/1/audio/se_jump.wav")

# BGM — Pyxel's music slot is an aggregate of constituent sound IDs.
# Render each constituent sound (the IDs the music slot points at) so
# `notes` is populated and quality-gate check #7 can verify them.
read_audio(script="main.py", target={"sound": 32},   # bgm channel 0 sound id
             output_path="/abs/path/screenshots/result/1/audio/bgm_ch0.wav")
read_audio(script="main.py", target={"sound": 33},   # bgm channel 1
             output_path="/abs/path/screenshots/result/1/audio/bgm_ch1.wav")

# Whole-mix BGM render (informational only — note: `notes: []`).
read_audio(script="main.py", target={"music": 0},
             output_path="/abs/path/screenshots/result/1/audio/bgm_mix.wav")
```

`target` accepts exactly one of `"sound"` or `"music"` (validation error otherwise). Both produce `peak_amplitude` and a WAV file, but **only `target={"sound": N}` populates `notes`** — `target={"music": N}` returns `notes: []` because Pyxel's music object is a list-of-channel-sound-IDs, not a note sequence. The audio gate (quality-gate.md check #7) requires `len(notes) >= 1` per cue, which only `target={"sound": N}` populates. Treat the music-target render as a peak-amplitude sanity check; render the per-channel sound IDs as sounds for the gateable evidence.

Empty slots return success with `peak_amplitude: 0.0`, `notes: []`, plus a warning — that's the gate-failing condition (check #7) routed to `sprite-quality`.

## notes.md template

Brief summary, no narrative prose. Replace angle brackets with the
actual values:

```markdown
# Bundle <N>

Generated: <ISO timestamp>
Game: <Title>
Spec: REFERENCE.md @ <git ref>
Plan: PLAN.md @ <git ref>

## Verified

- Win path GIF: <duration>s, ends on WIN at frame <N>.
- Lose path GIF: <duration>s, ends on GAME_OVER at frame <N>.
- Audio: <count> BGM channels rendered, <count> SE rendered.
- Frames: title / play_start / mid_game / win / game_over all show
  recognizable scenes.

## Known issues

- <anything caught but accepted as out-of-scope, with rationale>
```

## Concrete invocations

```python
# Win path: GIF + frames + state proof, all in one run
run(
    script="main.py",
    frames=720,
    inputs=<PLAN.md win-path inputs>,
    snapshots=[
        {"kind": "video", "start_frame": 0, "end_frame": 720, "fps": 30,
         "output": "screenshots/result/1/win-path.gif"},
        {"frames": [30, 90, 180, 360, 719], "kind": "screen_image",
         "output_pattern": "screenshots/result/1/frames/win-{frame}.png", "scale": 2},
        {"frame": 719, "kind": "state", "attrs": ["scene"]},
    ],
)

# Lose path: same shape, shorter frames, lose-path inputs
run(
    script="main.py",
    frames=480,
    inputs=[
        {"frame": 30, "buttons": ["KEY_SPACE"]},
        {"frame": 32, "buttons": []},
    ],
    snapshots=[
        {"kind": "video", "start_frame": 0, "end_frame": 480, "fps": 30,
         "output": "screenshots/result/1/lose-path.gif"},
        {"frame": 479, "kind": "state", "attrs": ["scene"]},
    ],
)

# Audio (script must run cleanly to populate sound slots first).
# Use `target={"sound": N}` for anything that will go through quality-gate check #7:
# the music-target render does not populate `notes` (see "Audio rendering"
# section above for the full explanation).
read_audio(script="main.py", target={"sound": 10},
             output_path="/abs/path/screenshots/result/1/audio/se_jump.wav")
read_audio(script="main.py", target={"sound": 32},   # bgm channel 0 sound id
             output_path="/abs/path/screenshots/result/1/audio/bgm_ch0.wav")
```

## Anti-patterns

- Bundle with `duration < 60`. Too short to demonstrate the loop.
- Skipping audio. A game with no rendered SE/BGM is not a complete
  proof, even if the visuals are perfect.
- Frames captured but no GIF. Static PNGs cannot prove animation
  or input handling.
- Reusing a stale bundle from before a code change. Bump `<N>` and
  produce a fresh bundle after any non-trivial change.
- Bundle whose middle 80% is the same frame (game stalled). `diff_frames(frame_a=mid_frame_path, frame_b=late_frame_path)` returns `identical: True` only if pixels are bit-identical. For middle-of-bundle stall checks, capture two frames in the visually-active range and assert `identical: False`. (`region` is `None` when identical, so the check needs both `identical` and `size_match`.) (Pattern G)
- Re-attempt regression checks (Pattern G). When iterating, compare a representative frame from the previous bundle (`screenshots/result/<N-1>/frames/mid_game.png`) to the same frame in the new bundle (`screenshots/result/<N>/frames/mid_game.png`). Drift confirms a fix moved things; identical pixels mean the fix did not change the visible state. Useful as a sanity check before running the full gate.

## Pre-handoff agent review

After `screenshots/result/<N>/` is produced, before calling the
gate or reporting to the user, agent (you) must inspect the bundle
visually. This is **the gate's primary check** (quality-gate.md #11) — tool-based observations (`run` state snapshots, `read_audio` peak/notes, `diff_frames` dead-time) certify *mechanics*; only the agent's own multimodal eyes certify *recognizability* and *playability*. A bundle that passes #1-#10 with empty / boilerplate / contradictory verbalization fails #11 and the gate.

Procedure:

1. List the frame files: `screenshots/result/<N>/frames/*.png` (typically
   `title.png`, `play_start.png`, `mid_game.png`, `win.png`,
   `game_over.png`).
2. For each PNG, use the `Read` tool to open it. The Pyxel canvas is
   small (e.g., 224×256), so the multimodal LLM can read every pixel.
3. Verbalize observation in 1–2 sentences per frame, covering:
   - **Sprite identity** — does the player sprite look like Mario /
     Princess / declared character per ASSETS.md `represents:`? Or is
     it a single-color rectangle, an unrecognizable blob, or the wrong
     sprite swapped in?
   - **Scene state** — is this TITLE / PLAY / WIN / GAME_OVER as the
     PLAN.md milestone for this frame implies?
   - **HUD content** — score, lives, level, "PRESS SPACE" prompts —
     all visible, legible, no overflow, no overlap with gameplay sprites?
   - **Animation state** — is the player mid-stride / climbing / jumping
     / falling / dead as the milestone implies?
   - **Background and hazards** — is the playfield populated (girders,
     ladders, pickups, hazards) or mostly empty? Are barrels / enemies
     in plausible positions?
4. Compare each verbalization against the corresponding PLAN.md
   milestone description. Note divergences explicitly: "milestone
   says barrel near floor at frame 200, observation: barrel still on
   girder 1".
5. **If any frame shows a defect** — missing sprite, wrong scene,
   static animation, placeholder rectangle, illegible HUD, unexpected
   color blob, recognizability failure, dead-time signature — return
   to `task-execution.md` (or earlier stage if upstream:
   `asset-gen.md` for sprite identity, `scaffold.md` for scene
   routing, `decomposer.md` for milestone alignment). **Do NOT
   proceed to the gate without a fix.**
6. When all frames pass agent visual review, the verbalizations
   become input to the gate's check #11 (Agent visual review),
   which records them in `gate-report.json["agent_review"]`.

The previous validation cycle taught the project that 15/15
mechanics PASS can still produce "100 中 5" gameplay if the agent
never looked at a single frame. This step is the harness's
correction. It is NOT optional.

## When this is done

`screenshots/result/<N>/` exists with all required artifacts:
both GIFs, the five frame snapshots, one WAV per audio manifest
entry, and `notes.md`. **Pre-handoff agent review has been
performed** — agent has Read each frame and verbalized
observations against PLAN.md milestones, with no unresolved
divergence. The counter `<N>` is the next integer above the
previous bundle. Return to `task-execution.md` (which hands off
to `quality-gate.md`).
