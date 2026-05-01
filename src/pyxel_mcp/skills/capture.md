# Capture — proof bundle production

**Phase 8.** Produce a `screenshots/result/{N}/` directory containing
runnable evidence that the game functions end-to-end.

## Bundle contract

For attempt `N` (start at 1, increment for each new final attempt):

```
screenshots/result/<N>/
├── win-path.gif         — record_gameplay output of full clear
├── lose-path.gif        — record_gameplay output of full death
├── frames/              — capture_frames at scene transitions
│   ├── title.png
│   ├── play_start.png
│   ├── mid_game.png
│   ├── win.png
│   └── game_over.png
├── audio/
│   ├── bgm_ch0.wav      — render_audio for each declared sound
│   ├── bgm_ch1.wav
│   ├── bgm_ch2.wav
│   ├── se_jump.wav
│   ├── se_climb.wav
│   ├── se_death.wav
│   └── se_win.wav
└── notes.md             — summary, known issues, observations
```

`record_gameplay` writes GIF; the `.wav` artifacts come from
`render_audio`'s `output_wav_path`. `capture_frames` writes PNGs.

## Win-path GIF requirements

- Duration: at least the full win-path scenario (typically
  20–30 seconds at 30 fps = 600–900 frames).
- Must show the player traversing from start to goal.
- Must end on the WIN scene.
- A bundle that shows "first 5 seconds look right then static for
  20 seconds" is FAIL, not partial pass.

```bash
record_gameplay main.py \
    --inputs '<win-path scripted inputs from PLAN.md>' \
    --duration 720 \
    --scale 2 \
    --timeout 30 \
    > screenshots/result/1/win-path.gif
```

## Lose-path GIF requirements

- Duration: at least until GAME_OVER triggers (typically ≥ 12s).
- Must show hazard appearing, hitting player, lives decrementing.
- Must end on GAME_OVER scene.

```bash
record_gameplay main.py \
    --inputs '[{"frame":30,"keys":["KEY_SPACE"]},{"frame":32,"keys":[]}]' \
    --duration 480 \
    --scale 2
```

## Frame snapshots

Capture key transitions:

```bash
capture_frames main.py --frames="30,90,180,360,720" --scale=2
```

Or, for a scenario with input, use `play_and_capture` with the same
input schedule the GIF used.

## Audio rendering

For every entry in REFERENCE.md §6 (audio cues), render to WAV:

```bash
render_audio main.py --sound_index=10 \
    --output_wav_path=screenshots/result/1/audio/se_jump.wav
render_audio main.py --music_index=0 \
    --output_wav_path=screenshots/result/1/audio/bgm.wav
```

Verify each WAV is non-empty and has notes (peak > minimum threshold).
The note sequence in the response confirms the BGM/SE plays the
intended pitches.

## notes.md content

Brief summary:

```markdown
# Bundle 1

Generated: <timestamp>
Game: <Title>
Spec: REFERENCE.md @ <git ref>
Plan: PLAN.md @ <git ref>

## Verified

- Win path GIF: <duration>s, ends on WIN scene at frame <N>.
- Lose path GIF: <duration>s, ends on GAME_OVER at frame <N>.
- Audio: 4 BGM channels, 7 SE.
- Frames: title/play/mid/win/gameover all show recognizable scenes.

## Known issues

- <anything caught but accepted as out-of-scope, with rationale>
```

## Anti-patterns in this phase

- Producing a bundle with `duration < 60`. Too short to demonstrate
  full game flow.
- Producing a bundle but skipping audio. Game without sound is
  not a complete proof.
- Producing a bundle with frames captured but no GIF. Static frames
  don't prove animation works.
- Re-using a bundle from before a code change. Bundle is per
  final-attempt; bump `{N}` after any non-trivial change.
- A bundle whose middle 80% is the same frame (game stalled).
  Use `compare_frames` to spot-check that frame X and frame X+200
  meaningfully differ.

## When this phase is done

`screenshots/result/<N>/` exists with all required artifacts. Move to
`quality-gate` (read `pyxel://skills/quality-gate`) for final
acceptance.
