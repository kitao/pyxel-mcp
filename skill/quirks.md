# Pyxel Quirks

Keep this file small and high-signal. Each item below has bitten real implementations and shows up as ambiguous bugs.

**Inclusion rule.** Add only repeated, non-obvious issues that would have prevented real confusion in `scaffold`, `asset-gen`, `task-execution`, `capture`, or any `knowledge/` file. If an item is already in `pyxel-mcp`'s `instructions.md` Error Recovery section or in the `pyxel://anti-patterns` resource, it does not belong here. If it is answerable by `pyxel://api-reference`, it does not belong here.

## Anti-pattern detector reference

See pyxel-mcp resource `pyxel://anti-patterns` for the full list of categories surfaced by `validate`, with rationale and canonical fixes for each. The categories duplicated here previously (`tilemap_zero_zero`, `assets_in_update` and the asset-bank lifecycle, the `btn` vs `btnp` distinction) all live there now and stay current with the actual detector logic.

## Coordinates and drawing

- **Origin (0, 0) is top-left, Y increases downward.** Math conventions
  with origin bottom-left will produce upside-down sprites. Always
  reason about Y as "distance from top".
- **Draw order is paint order.** Background first, sprites next, UI
  on top. There is no z-buffer; whatever you draw last wins.

## Image bank size

- The image bank is **256x256 pixels per slot**. Plan u/v coordinates
  in `ASSETS.md` so sprites do not overlap. Default Pyxel exposes
  3 banks (0, 1, 2); more can be added but most games stay within
  the defaults.

## Audio: SE volume and tone choice

- The 4 audio channels are split BGM (ch0–ch2) and SE (ch3). SE
  volume must be **5–7** (out of 7) to cut through 3-channel BGM.
  Volumes 1–4 are typically inaudible during gameplay.
- Square (`"s"`) and pulse (`"p"`) tones carry over BGM. Noise
  (`"n"`) is too quiet for melodic SE — reserve it for percussive
  hits where the texture is the point, not the pitch.

## `state` snapshots do not auto-expand deep nesting

The `state` snapshot kind inside `run` reads attributes off the
`App` instance (the class that calls `pyxel.run()`). With `attrs:
None` (or omitted), only top-level scalar primitives are returned —
lists, dicts, and custom objects are skipped. Dotted/indexed paths
like `"player.x"` or `"barrels[0].y"` are followed when explicitly
named, but **arbitrary nested chains are not auto-expanded**:
`app.world.player.physics.velocity.y` will not be reachable as a
single attr — name each leaf individually, or flatten to top-level
App attributes (`self.player_x`, `self.player_vy`, `self.scene`).

## `pyxel.quit()` does not force-exit since 2.8

`pyxel.quit()` *requests* the loop to end after the current frame.
Since Pyxel 2.8, it does **not** force-terminate the process. A
`while True:` loop or busy-wait inside `update()` after calling
`quit()` will hang the script — and hang the harness, which will
hit its timeout instead of exiting cleanly. Return from `update()`
promptly; let the loop end naturally.

## Feedback Loop

Quirks are curated manually in this skill. Add only repeated, non-obvious issues that would have prevented real confusion in a stage file (`scaffold`, `asset-gen`, `task-execution`, `capture`) or in a knowledge file. Remove items that have stopped biting after engine or skill changes.
