# Stage 5: Asset Generation

For every entry in `ASSETS.md`, write the `pyxel.images[N].set()` call in `_build_assets()` and verify the rendered sprite reads as its `represents:` description before moving on.

## Inputs

- `ASSETS.md` (from Stage 4) — full sprite manifest with bank coordinates, palette plan, identity contract.
- `STRUCTURE.md` "Modules" — `_build_assets()` lives in `App.__init__`.
- `main.py` — runnable skeleton from Stage 3.
- `knowledge/pixel-art.md` — 16-color palette, 3-color-per-material rule, sprite design process.
- `pyxel://run-snapshots-schema` (MCP resource) — only relevant for `screen_image` outputs from any verify run; `read_image` returns its own self-contained schema.

## Output

`main.py` with `_build_assets()` populated. Every ASSETS.md entry has a working `read_image` showing distinguishable pixels at the declared coordinates.

## Loop per asset — multi-draft, blind read, concrete-feature

Single-draft sprite shipping is the most common failure mode here. The multimodal LLM has a **generous interpretation bias** when reading its own output ("yes that 5-pixel blob is a head, that red shape is a cap, this is Mario"). One draft + permissive verbalization passes the loop ritual without producing a recognizable sprite. Three structural rules counteract this:

### Rule A — Multi-draft mandate (≥3 drafts per character sprite)

For each character sprite (`player_*`, antagonist, NPC — anything an ASSETS.md entry calls a character or names a represented subject), produce at least **3 distinct hex-string drafts** with materially different design choices: e.g., Draft 1 minimal (5 colors, simple shapes), Draft 2 detailed (more colors, finer features), Draft 3 stylized (exaggerated proportions, bold outline). Render each draft to its own PNG via `read_image(... render_path="tmp/<sprite>_v<N>.png")`. Single-draft → single attempt → no real iteration.

The drafts and selection are part of the artifact: ASSETS.md's entry for the sprite must list the 3 hex-strings, the literal verbalization of each draft, and a 1-line **selection reasoning** ("v2 picked: cap clearer at top because 4-pixel-wide vs v1's 2-pixel; eyes more legible because pixel positions don't blend with background"). The chosen draft becomes the `_build_assets()` data; the others stay in ASSETS.md as evidence the loop ran.

Background / decoration / abstract sprites (girder tile, ladder rung, single-tone pickup) can be 1 draft if the represented subject is a geometric primitive. Only character sprites (subject + features expected) need ≥3.

### Rule B — Blind read protocol (separate literal description from recognition)

The verbalization step splits into two strictly-separated sub-steps. Generous bias is reduced when literal description happens **without** the `represents:` string in the immediate context.

**Step B1 — Literal description, pixel-by-pixel.** Read the rendered PNG with the explicit prompt-to-self: *"Describe what I literally see in this grid, position by position. Do not name the figure. Do not infer intent. Do not match against expectations."* Output is mechanical: row indices, color regions, pixel positions, sizes. Example:

> "16×16 grid. Top region (rows 0-3): 4-pixel-wide red shape spanning columns 6-9 at row 1, narrowing to 2 pixels at row 3. Mid region (rows 4-9): brown 8×6 block centered, with 1-pixel black dots at (row 4, col 5) and (row 4, col 10). Bottom region (rows 10-15): blue 6×4 region with 2-pixel-wide separation forming two leg-like columns at cols 5-7 and cols 9-11."

**Step B2 — Recognition check.** Now bring the entry's `represents:` into focus (e.g., `"Mario, red-cap plumber, mid-stride"`). Ask: *given only the Step B1 literal description, would a reader with no prior knowledge identify this as `[represents:]`?* Show reasoning explicitly:

> "Step B1 mentions: red shape on top, brown center, blue lower with two columns. Mapping to represents: red cap → ✓ (top red), face → ~ (brown center plausible), eyes → ✓ (black dots), overalls → ✓ (blue lower), legs in stride → ~ (two columns visible but no clear stride asymmetry). 4 of 5 features present, stride ambiguous. Pass with caveat: redraw legs to show offset stride."

If the recognition check fails (literal description doesn't suggest the subject), redraw. **Do not** rationalize the existing draft into recognizability ("well technically the brown is the face if you squint").

For maximum rigor, dispatch the literal-description step to a fresh subagent that does not have ASSETS.md in its context (PNG only). Optional but recommended for the protagonist and antagonist sprites.

### Rule C — Concrete-feature verbalization required

Both Step B1 and B2 outputs must use **pixel-position-concrete** language. Reject any of these vague-label patterns:

| Anti-pattern (vague) | Replace with (concrete) |
|---|---|
| "Mario-like figure" | "16×16 sprite, top has 4-pixel red region, middle has 8-pixel brown region, bottom has two 4-pixel blue legs" |
| "Looks like a barrel" | "8×8 sprite, brown 8×6 oval, 2 horizontal black bands at rows 3 and 5" |
| "Identifiable as the boss" | "32×32 sprite, brown body 24×24 centered, white eyes 1-pixel at (rows 8, cols 10/14), red bow-tie 4×2 at row 18" |
| "Recognizable" / "good enough" / "decent" | replaced by the concrete description that justifies the claim |

If the agent's verbalization slides into vague labels, the recognizability test isn't honest — quality-gate.md #11 catches this and the gate FAILs.

### Concrete loop for one character asset

```python
# Per ASSETS.md row "player_idle, represents: Mario red-cap plumber idle":
# 1. Three drafts:
draft_v1 = ["00088000", "00111000", ...]   # minimal, 5 colors
draft_v2 = ["08888880", "01111110", ...]   # detailed, 8 colors
draft_v3 = ["00088000", "00811800", ...]   # stylized, exaggerated cap
# Write each into a tmp slot, render PNGs:
for v, hex in [("v1", draft_v1), ("v2", draft_v2), ("v3", draft_v3)]:
    pyxel.images[7].set(0, 0, hex)   # tmp slot 7
    read_image(script="main.py", image=7, x=0, y=0, w=16, h=16,
               render_path=f"tmp/player_idle_{v}.png")
    # 2. Step B1 — literal Read of each PNG, no represents: in context
    # 3. Step B2 — recognition check against "Mario red-cap plumber"

# 4. Pick best (e.g., v2). Reasoning recorded in ASSETS.md:
#    "v2: cap clearer at top (4-px vs v1's 2-px); eyes legible at (4,5)+(4,10);
#     overalls visible as blue 8×4 lower region. v1 too sparse. v3 caricatured."

# 5. Final commit to _build_assets():
pyxel.images[0].set(0, 0, draft_v2)

# 6. validate clean
validate(script="main.py")
```

### Background / abstract assets (1 draft acceptable)

Tilemap girders, ladders, pickup icons (hammer, coin, key), bullets — these are geometric primitives. Single hex-string draft is acceptable if the represented subject has no sub-features. Still render, still Read once, but no multi-draft is required.

The rule of thumb: *if `represents:` names a subject with anatomy (head, body, limbs, face), it's a character sprite and needs ≥3 drafts. If `represents:` names a shape or material (rectangle, line, geometric tile), 1 draft is fine.*

### What `read_image` aggregate fields are still good for

`color_count` (≥ ASSETS.md `min_distinct_colors`) and `fill_ratio` (in [0.15, 0.95]) remain **necessary** sanity checks for "is the sprite empty / oversaturated / single-blob". They do not certify recognizability — that's the agent's job per Rule A/B/C above.

`read_image` returns the `pixels` palette-index grid inline only when the requested region's area ≤ 4096 (per spec §6.4.1 / §7.2). For 16×16 sprites the grid is included; for the full 256×256 bank it is `None`. The `render_path` argument always writes the PNG regardless — it is the agent-readable artifact and is mandatory for the Read steps above.

## Sprite identity heuristics

`read_image` returns aggregate fields that map directly to ASSETS.md identity contracts — do not eyeball:

- **Color region count.** `read_image` returns `color_count` as a dict mapping palette-index integer keys to pixel counts (or string keys after JSON serialization through MCP). Assert `len(color_count) >= min_distinct_colors` from ASSETS.md. Below that → single-blob → FAIL.
- **Bounding-box density.** `read_image` returns `fill_ratio` (non-zero pixels / total). Assert `0.15 <= fill_ratio <= 0.95`. Above 0.95 → no silhouette. Below 0.15 → too few visible pixels.
- **Frame pair diff.** For paired frames (`walk_1` / `walk_2`), call `read_animation`. The argument that controls "how many adjacent regions" is `region_count` (renamed from old `frame_count`); pair the count with `direction`:
  - `direction="horizontal"` if frames are laid out side-by-side (e.g., `walk_1` at (0,0), `walk_2` at (16,0))
  - `direction="vertical"` if frames stack (e.g., `walk_1` at (0,0), `walk_2` at (0,16))
  Read the layout from ASSETS.md before choosing. The result's `region_diffs[0]["diff_ratio"]` is the pair diff; assert `0.05 <= diff_ratio <= 0.50`. Do NOT compute the diff yourself.
- **Edge contrast.** Surfaces in `read_image`'s `warnings` list when an outlined sprite's perimeter palette is too close to the interior. Treat warnings as FAILs for outlined sprites.

## Worked example: `player_walk_1` (16x16, 6+ colors)

```python
# Inside _build_assets():
pyxel.images[0].set(0, 0, [
    "0008888880000000",   #     ████
    "0088888888000000",   #    ██████
    "008f44ff44f00000",   #   skin/face with outline & mouth
    "008f4ff4ff4f0000",   #   eye details
    "0008f4444f000000",   #
    "0008cccccccc0000",   #   overalls (12=cyan)
    "008c87887878c000",   #   buttons (8=red dots)
    "008cccccccccc000",   #
    "0088cc8800cc8800",   #   arms swing forward
    "008c08000080cc00",   #
    "0080000000000000",   #
    "00cccc0000cccc00",   #   legs separated (one fwd, one bk)
    "00cccc0000cccc00",   #
    "0044440000444400",   #   shoes (4=brown)
    "0044440000444400",   #
    "0000000000000000",
])
```

This is illustrative — exact pixels depend on art direction. The point is: 16x16 is enough room for cap, face, eyes, mustache hint, overalls with two buttons, arm in distinguishable position, two separated legs, and shoes. A "Mario-shaped blob" with one or two colors does not satisfy the contract.

After writing this block:

```python
validate(script="main.py")
read_image(script="main.py", image=0, x=0, y=0, w=16, h=16)
```

Expect `color_count` keys ≥ 5 (e.g., `{0, 4, 8, 12, 15}` for transparent / brown / red / cyan / white), and `fill_ratio` around 0.45.

## Hex-string conventions

Every character in a hex string is a single palette index `0`–`f`. Width = number of characters per line; height = number of lines. Pyxel does not tolerate ragged rows: if one line is 15 chars and another is 16, `validate` flags it but the underlying `images.set()` call may silently pad or crash depending on context. Keep all rows the same length.

Conventions worth holding to:

- Use `0` for transparent pixels and pass `colkey=0` everywhere `blt()` is called. Mixing transparent palette indices across sprites breaks reuse.
- Indent hex strings at the same column so columns line up visually — this is how you spot a stray pixel before running `read_image`.
- Trailing comments (`# overalls (12=cyan)`) are encouraged. Stage 6 maintainers read these.
- For 8x8 sprites, prefer 8x8 over a half-filled 16x16 — pixel density scales differently and animation diff thresholds tighten.

## Animation pairs

When ASSETS.md declares paired frames (`walk_1` / `walk_2`, `barrel_1` / `barrel_2`, swing-left / swing-right), implement both before verifying. `read_animation` is the only tool that reports the per-frame diff cleanly:

```python
read_animation(
    script="main.py",
    image=0,
    x=0, y=0, w=16, h=16,
    region_count=2,
    direction="horizontal",   # or "vertical" — match ASSETS.md bank layout
)
```

The two frames must share palette (same `color_count` keys, allowing for one or two pixels of motion-driven swap) and outline silhouette, but differ in 5–50% of pixels. Practical recipe: copy walk_1's hex into walk_2, then move legs / arms / cape down or up by 1–2 pixels. Don't redraw walk_2 from scratch; it will diverge too much.

## Bank organization tip

Use a region dict that mirrors ASSETS.md so coordinates aren't magic numbers:

```python
REGIONS = {
    "player_walk_1": (0,   0),
    "player_walk_2": (16,  0),
    "player_jump":   (32,  0),
    "hammer_idle":   (96,  0),
    "hammer_swing":  (112, 0),
    "boss":          (128, 0),
    "barrel_1":      (0,  32),
    "barrel_2":      (16, 32),
}

def _build_assets(self):
    img = pyxel.images[0]
    img.set(*REGIONS["player_walk_1"], [...])
    img.set(*REGIONS["player_walk_2"], [...])
    # ...
```

When you change a coordinate in ASSETS.md, change it once here. Draw calls `pyxel.blt(x, y, 0, *REGIONS["player_walk_1"], 16, 16, colkey=0)` stay readable.

## End-of-stage verification

Once every ASSETS.md entry is implemented, run a whole-stage scan:

```python
read_image(script="main.py", image=0)
```

Omitting `x/y/w/h` scans the full bank. The result's `pixels` is `None` (256x256 = 65k > 4096), but `color_count` and `fill_ratio` give a useful summary: every declared region should contribute colors, fill_ratio should be non-trivial. Visually verify no sprite spills into a neighbor's region using per-asset `read_image` calls if needed. Then for each animation pair declared in ASSETS.md:

```python
read_animation(
    script="main.py",
    image=0,
    x=0, y=0, w=16, h=16,
    region_count=2,
    direction="horizontal",   # or "vertical" — match ASSETS.md bank layout
)
```

Frames should differ (5–50% per-frame diff) but share palette and silhouette outline. If the diff is below 5%, the animation will look static. Above 50%, it will flicker.

**Tilemap source-bank trap (Pattern F).** If ASSETS.md declares a tilemap (used in scaffold or task-execution), the source bank's `(0, 0)` tile must be empty (all palette index 0) — otherwise every "empty" tilemap cell shows visible content. This is `quality-gate.md` check #9. Verify by inspecting the (0,0) corner of the source bank:

```python
read_image(script="main.py", image=0, x=0, y=0, w=8, h=8)
# Assert: color_count keys == {0} (only background) and fill_ratio == 0.0
```

If non-zero pixels are at (0,0), move the offending sprite to a different bank location and update ASSETS.md.

## Quirks worth knowing before you start

- **`pyxel.sounds[N].mml(...)` does not populate `.notes` and produces a silent WAV via `.save()`.** If this stage produces audio cues that need to clear quality-gate check #7, use `pyxel.sounds[N].set(notes=..., tones=..., volumes=..., effects=..., speed=N)` instead. See `knowledge/audio.md` "Gate compatibility" for the gate-passable BGM template. (Friction surfaced in β2 e2e validation.)
- **`gen_bgm` returns MML strings.** Loading them via `.mml()` runs into the same problem. Hand-author shipping BGM via `.set()`, or transcribe `gen_bgm` output by hand.

## Anti-patterns in this stage

- **Generating sprites in `update()` instead of `_build_assets()`.** Either runs every frame (perf disaster) or runs after `pyxel.run()` starts and is invisible to `read_image` for the first few frames.
- **"Add it later" placeholders:** `pyxel.rect(x, y, 8, 8, 8)` in `draw()` instead of `pyxel.blt(...)`. The asset manifest declares a sprite; the draw call must `blt` from it. Asset-gen was skipped — the agent visual review (quality-gate.md check #11) will catch the placeholder rectangle and route to `sprite-quality`.
- **Bulk-edit then bulk-verify.** Edit one sprite, run `read_image` with `render_path=`, `Read` the PNG, verbalize observation, fix, then move on. Editing 10 sprites before reviewing means 10 broken sprites to triage at once. The Read step is non-negotiable — see SKILL.md rule #9.
- **Trusting `color_count` / `fill_ratio` without Reading the PNG.** Aggregate metrics certify "5 colors used" but not "the sprite reads as Mario". A 5-color sprite of a random pattern passes the aggregate check; the multimodal `Read` is the recognizability gate.
- **Forgetting `colkey=0` in `blt()` calls.** The transparent background of the sprite renders opaque (palette index 0). `validate` warns about missing `colkey` — fix it.
- **Computing diffs yourself.** `read_animation` returns `diff_ratio` via `region_diffs[0]["diff_ratio"]`; always specify `region_count` and `direction` explicitly. Don't read raw `pixels` arrays and XOR them — the harness already did the math.

## When this stage is done

- Every ASSETS.md entry has a corresponding `pyxel.images[N].set(...)` call in `_build_assets()`.
- `read_image` per asset reports `color_count` keys ≥ ASSETS.md minimum, `fill_ratio` in [0.15, 0.95].
- `read_animation` per paired frames reports `diff_ratio` in [0.05, 0.50] (called with `region_count=2, direction="horizontal"` or `direction="vertical"` per ASSETS.md layout).
- `read_image(script="main.py", image=0)` (full-bank scan, no x/y/w/h) shows the declared layout with no overlap and no missing regions.
- `read_image(image=0, x=0, y=0, w=8, h=8)` shows source-bank (0,0) is fully transparent (no tilemap trap).
- Move to Stage 6 (read `task-execution.md`).
