# Knowledge: Audio

Used by Stage 3 (scaffold — channel allocation) and Stage 6 (task-execution — SE definitions per event).

## Gate compatibility — `.set()` not `.mml()` for any sound feeding the gate

**Pyxel's `pyxel.sounds[N].mml("...")` does not populate the underlying `.notes` / `.tones` / `.volumes` / `.effects` lists, and `.save()` produces a silent WAV from an MML-populated slot.** That means:

- `read_audio(target={"sound": N})` returns `notes: []` and `peak_amplitude: 0.0` for any slot populated via `.mml()`
- quality-gate.md check #7 (`peak >= 0.02 AND len(notes) >= 1`) cannot pass for MML-populated sounds

For **any** sound that needs to clear the gate — every SE on ch3, every BGM constituent sound on ch0–ch2 — use `.set()` and let `.mml()` stay as a prototyping / reference tool only. Conversion is mechanical (note string ↔ MML letter sequence; volume `V0`-`V100` → `0`-`7`; tone `@N` → `s/p/t/n`).

**Gate-passable BGM template (use this, not MML):**

```python
# Ch0: Melody (set form — populates .notes, gate sees it)
pyxel.sounds[10].set(
    notes="C2C2D2D2E2E2F2F2 G2G2A2A2B2B2C3C3",
    tones="s",
    volumes="5",
    effects="n",
    speed=10,
)
# Ch1: Bass
pyxel.sounds[11].set(
    notes="C1RG1R A1RF1R",
    tones="t", volumes="6", effects="n", speed=20,
)
# Ch2: Harmony
pyxel.sounds[12].set(
    notes="EGCG ECEG",
    tones="p", volumes="3", effects="s", speed=10,
)
pyxel.musics[0].set([10], [11], [12])
```

The MML composition guide below is still useful for **designing** a tune (MML is more expressive for prototyping in a Pyxel editor session) — but commit the final BGM as `set()` calls so the gate's audio check (#7) can verify it.

## Channel allocation

Pyxel exposes 4 audio channels (ch0–ch3). Allocate them as follows:

- **ch0–ch2**: BGM (3-channel music — melody / bass / harmony or arpeggio)
- **ch3**: SE (sound effects — reserved exclusively)

Never play SE on ch0–ch2 — it cuts the BGM mid-note. Never put BGM on ch3 — it conflicts with SE.

**Volume rules:**

- BGM volume: 3–5 (background, doesn't dominate)
- SE volume: 5–7 (must cut through BGM, especially for player-feedback events)

**Tone rules for SE:**

- Use square (`"s"`) or pulse (`"p"`) for melodic SE (jump, coin, menu, power-up)
- Use noise (`"n"`) only for impacts (explosion, hit, crash)
- Noise tone is hard to hear over BGM — never use it as a primary SE tone for events the player must notice

Every player-visible event needs an SE: move, rotate, land, clear, chain, game over, game start. Short SE (4–8 notes, speed 3–10) naturally prevent channel conflicts even on ch3.

### MML Composition Guide (prototyping reference only — convert to `set()` for shipping)

> **Reminder.** MML-populated slots fail quality-gate check #7 (`.notes` not populated, `.save()` silent). The 3-channel templates below are useful for designing the tune in a Pyxel editor session; **convert to `set()` calls before shipping** (see "Gate compatibility" section above for the `set()` template).

Structure BGM as 3 channels: melody (ch0), bass (ch1), harmony/arpeggio (ch2). Reserve ch3 for SE. Use `read_audio` to verify each channel separately.

**3-channel MML template (for prototyping):**

```python
# Ch0: Melody — carries the theme
pyxel.sounds[10].mml("T120 @1 V80 L8 O4 [CEGC>C<BAGFEDC R4]2")
# Ch1: Bass — root notes, steady rhythm
pyxel.sounds[11].mml("T120 @0 V60 L4 O2 [CC8C8 GG8G8 AA8A8 FF8F8]2")
# Ch2: Arpeggio — fills space, adds texture
pyxel.sounds[12].mml("T120 @1 V40 L16 O4 [CEGCEGCEGCEG <B>DG<B>DG<B>DG<B>DG]2")
pyxel.musics[0].set([10], [11], [12])
```

**Volume scales:** MML uses `V0`-`V100` (e.g., `V80` = 80%). The `set()` API uses a `volumes` string with single-digit values `0`-`7` (e.g., `"7776"`). These are independent scales — `V7` in MML is very quiet, not the same as `7` in `set()`.

**Genre moods by key and tempo:**

| Genre | Key | Tempo | Tones | Tips |
|-------|-----|-------|-------|------|
| Action/Gothic | A- minor, C minor | T100-120 | @1 melody, @0 bass | Use E-/A-/B- for dark feel, 8th note arpeggios |
| Adventure | C major, G major | T120-140 | @1 melody, @0 bass | Ascending phrases for heroic mood |
| Puzzle/Calm | F major | T80-100 | @0 melody, @1 harmony | Dotted notes, gentle tempo |
| Horror | B- minor | T60-80 | @2 melody, @3 accents | Half notes, chromatic movement, sparse |
| Boss battle | E minor | T140-160 | @1 melody, @0 bass | Driving 16th bass, syncopated melody |

### Quick BGM

`gen_bgm` generates procedural music — great for rapid iteration, but all outputs share a similar flavor. Combine with hand-written MML for variety.

> **Gate compatibility note.** `gen_bgm` returns MML strings, which load via `.mml()`. As covered in the "Gate compatibility" section above, MML-populated slots fail quality-gate check #7 (silent WAV, empty `.notes`). For shipping BGM that the gate verifies, do **not** use `gen_bgm` directly — either: (a) hand-author the BGM via `.set()` per the gate-passable template, or (b) use `gen_bgm` only as a melodic-design starting point and transcribe the result into `.set()` calls. There is no automatic MML→set converter.

```python
# gen_bgm(preset, transp, instr, seed, play=False) — first 4 args required
# Returns 4 MML strings — drop ch3 if you need it for SE

# Example: 3-channel BGM (reserve ch3 for SE)
mml = pyxel.gen_bgm(preset=7, transp=0, instr=1, seed=42)
for i in range(3):
    pyxel.sounds[10 + i].mml(mml[i])
pyxel.musics[0].set([10], [11], [12])

# Quick play (uses all 4 channels — good for title screens)
pyxel.gen_bgm(preset=7, transp=0, instr=3, seed=42, play=True)

# Scene-specific BGM — vary preset/seed per scene for distinct moods
def play_bgm(self, scene):
    BGM = {
        # (preset, transp, instr, seed)
        "title":    (0, 0, 1, 100),  # title/departure, melody+bass+drums
        "game":     (4, 0, 2, 200),  # field/adventure, melody+sub+bass
        "boss":     (7, 0, 1, 300),  # battle/crisis, melody+bass+drums
        "gameover": (2, 0, 0, 400),  # town/peaceful, melody+reverb+bass
    }
    preset, transp, instr, seed = BGM[scene]
    mml = pyxel.gen_bgm(preset, transp, instr, seed)
    for i in range(3):
        pyxel.sounds[60 + i].mml(mml[i])
    pyxel.musics[0].set([60], [61], [62])
    pyxel.playm(0, loop=True)
```

## Sound Effects Cookbook

Copy-paste sound definitions for common game events. All SE on ch3 via `pyxel.play(3, N)`. BGM on ch0-2.

Design rules:
- Use square (`"s"`) or pulse (`"p"`) for melodic SE — noise (`"n"`) only for impacts
- SE speed 3-10 (fast, snappy), BGM speed 16-25 (slower, musical)
- SE volume 5-7 to cut through BGM (volume 3-5)
- Ascending notes = positive (collect, power-up, level clear)
- Descending notes = negative (damage, death, game over)

### Jump

```python
pyxel.sounds[0].set(
    notes="c2e2g2c3", tones="s", volumes="7776", effects="nnnn", speed=8,
)
```

### Coin / Collect

```python
pyxel.sounds[1].set(
    notes="c3e3g3c4c4", tones="s", volumes="44444",
    effects="nnnnf", speed=7,
)
```

### Hit / Damage

```python
pyxel.sounds[2].set(
    notes="g3c3", tones="s", volumes="74", effects="nn", speed=5,
)
```

### Game Over

```python
pyxel.sounds[4].set(
    notes="f3b2f2b1f1f1f1f1", tones="p",
    volumes="44444321", effects="nnnnnnnf", speed=9,
)
```

Design other SE (explosion, menu, power-up, landing, shoot) using the rules above.
