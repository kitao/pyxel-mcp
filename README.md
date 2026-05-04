# pyxel-mcp

MCP server for [Pyxel](https://github.com/kitao/pyxel), a retro game engine for Python. Gives AI agents the verbs to **run, observe, and ship** Pyxel programs end-to-end without a window — headless, deterministic, gate-able. Includes a bundled production workflow skill so the agent has a phased pipeline, not just isolated verbs.

## Why this exists

LLM agents writing Pyxel code without verification produce shortcut games: placeholder rectangles, stalled play loops, missing assets, scripts that compile but render black. pyxel-mcp is the verb library that lets the agent **see** what its code actually does — and the workflow skill is the recipe that keeps it honest from concept to playable bundle.

- **Headless + fast-forward.** 600-frame run < 1 second. Pyxel's internal fps is overridden so `flip()` doesn't pace real-time.
- **Subprocess isolation.** Each tool call is a fresh Python subprocess. No leaked Pyxel state; deterministic with `random_seed=`.
- **Structured output.** Every tool returns JSON with a uniform `ok` / error shape — agents chain calls predicating on observed values, not stdout strings.
- **Pyxel footguns caught structurally.** (0,0) tilemap trap, draw-without-cls ghost trails, palette animation in `update`, run-outside-init — flagged by `validate` and `read_*`, not by squinting at screenshots.
- **Quality is the agent's responsibility, not a tool's.** No `judge_*` tools, no hardcoded numerical defaults — the agent runs the 9 observation tools, asserts predicates directly in Python against state snapshots, and uses `Read` on captured PNGs to verbalize against PLAN.md / ASSETS.md anchors. The workflow skill's 11-step quality gate enforces this end-to-end so "done" requires every milestone, asset, audio slot, proof bundle, and visual review to clear.

## Install

Register as an MCP server in your client. The CLI prints the exact snippet:

```bash
uvx pyxel-mcp install
```

Paste the printed JSON into your client's MCP config:

- **Claude Code**: `~/.claude/.mcp.json` (or per-project `.mcp.json`)
- **Cursor**: `~/.cursor/mcp.json`
- **Codex CLI**: `~/.codex/mcp.json`

The snippet itself:

```json
{
  "mcpServers": {
    "pyxel": {
      "command": "uvx",
      "args": ["pyxel-mcp"]
    }
  }
}
```

Restart your client. On startup the server logs one line to stderr (visible in your client's logs) so you can confirm it's loaded:

```
[pyxel-mcp] starting — 9 tools, workflow=/path/to/skill
```

Pyxel ≥ 2.9.5 is fetched as a transitive dependency.

### Optional: publish the workflow skill (Layer 3)

The MCP server already exposes the workflow content as `pyxel://workflow/*` resources. To **also** install it as a host-native skill (Claude Code skills, etc.) so it activates automatically on Pyxel-related prompts:

```bash
uvx pyxel-mcp publish-skill ~/.claude/skills/pyxel
```

Restart your client; the skill activates on phrases like "make a Pyxel game", "build a retro shooter", "remake Donkey Kong in Pyxel".

## First use

Three prompts that exercise the full pipeline (try them in order; each later one builds on the last):

1. **Discovery / smoke test** — "What tools does pyxel-mcp expose? Run a tiny Pyxel script and screenshot frame 30."
2. **Asset workflow** — "Design a 16x16 player sprite for a platformer; render it; show me the bank pixels and contrast warnings."
3. **End-to-end (skill activates)** — "Make a Donkey-Kong-style platformer in Pyxel. Walk the full visual-target → quality-gate pipeline."

Without the skill installed, prompt 3 still works but the agent has no enforced playthrough / asset / bundle gate — outputs degrade to "compiles cleanly" rather than "playable + clearable". `publish-skill` is the difference between verbs and a workflow.

## Tools (9 observation tools)

Run the script, read raw Pyxel state, diff frames. Each call is a fresh subprocess.

| Tool | What it returns |
|---|---|
| `run` | Drives N frames headless. Snapshots: `screen_image`, `screen_grid`, `state`, `layout`, `video`. Inputs schedule (`set_btn`/`set_btnv`/`set_mouse_pos`). `ASSERT` parsing. `random_seed` for determinism. |
| `validate` | Static analysis: syntax + 10 anti-pattern detectors (`cls_missing`, `palette_animation`, `tilemap_zero_zero`, `update_in_draw`, `iter_modify`, `ragged_image_set`, …). |
| `pyxel_info` | Versions, example paths, resource URIs. |
| `read_palette` | `pyxel.colors` analysis: 3-layer hierarchy (bg/env/interactive), WCAG contrast warnings filtered to **co-located** pairs only. |
| `read_image` | Image-bank region pixels + `color_count`, `fill_ratio`, `symmetry`, `edge_density`. Optional PNG render. |
| `read_animation` | Cross-region Jaccard / per-pair diff for paired sprite frames. |
| `read_tilemap` | Tilemap usage map + (0,0)-tile trap detection. |
| `read_audio` | Render `pyxel.sounds[N]` / `pyxel.musics[N]` to WAV; return `notes`, `peak_amplitude`, `warnings`. |
| `diff_frames` | Pixel-wise diff of two PNGs: `identical`, `ratio`, bounding box. |

## Quality verification belongs to the agent

No `judge_*` tools, no hardcoded numerical thresholds. The 9 tools above capture observations; the agent decides whether the observation is acceptable for the current task by writing Python predicates directly against snapshot values and by reading captured PNGs with the host's `Read` tool. The workflow skill (`pyxel://workflow`) lays out the 11 stop conditions an agent runs before declaring done — see its `quality-gate.md`.

This is a deliberate design choice. An earlier prototype had 8 `judge_*` tools with hardcoded `DEFAULT_CONTRACT` numerical thresholds (`min_distinct_colors`, `max_contrast_warnings`, `min_palette_consistency`, etc.). Every game type surfaced a default that fought a legitimate idiom (3-material palette ↔ contrast budget; flame-pulse ↔ palette-consistency floor; 4×4 sprite ↔ distinct-color minimum), and the tuning was unbounded. Removing the judges put the predicate where the multimodal context is — the agent — and ended the recurring tuning cycle.

## Workflow skill and resources

The workflow skill ships inside this package. Its 7-stage pipeline (visual-target → decomposer → scaffold → asset-planner → asset-gen → task-execution → quality-gate) plus reference and knowledge files are exposed two ways:

- **MCP resource channel** — `pyxel://workflow` (entry: SKILL.md), `pyxel://workflow/<stage>`, `pyxel://workflow/knowledge/<topic>`. Read directly with `@pyxel:workflow` style references in clients that surface MCP resources.
- **Host skill channel** — `uvx pyxel-mcp publish-skill <dir>` deploys the same content into the host's skill system so it activates from natural-language triggers.

Other resources (also under `pyxel://`):

- `pyxel://run-snapshots-schema` — Full grammar for `run`'s `snapshots` parameter (5 kinds × multi-frame syntax).
- `pyxel://api-reference`, `pyxel://user-guide`, `pyxel://mml-commands`, `pyxel://pyxres-format` — official Pyxel docs (24h cache).
- `pyxel://anti-patterns` — Categorised reference for `validate` issue codes.
- `pyxel://palette/default` — 16-color default palette table with hex/RGB/use hints.
- `pyxel://examples/<name>` — Pyxel's bundled example scripts (`02_jump_game`, `09_shooter`, …).

In Claude Code, reference any of them with `@pyxel:run-snapshots-schema`, `@pyxel:workflow`, `@pyxel:workflow/quality-gate`, etc.

## Update

`uvx` caches the package; force a refresh by passing the cache flag:

```bash
uvx --refresh-package pyxel-mcp pyxel-mcp install
```

After upgrading, re-run `publish-skill` if you have the host-skill channel installed — the workflow content version is pinned to the server version it shipped with.

## Troubleshooting

**Tools don't appear in the client.** Confirm the server started: look for `[pyxel-mcp] starting — 9 tools` in your client's MCP server logs. If absent, the snippet wasn't picked up — re-check the path you pasted into. If present but tools are missing, restart the client (some clients cache the tool list across config edits).

**Skill doesn't activate on prompts.** The skill must be in the host's skill directory and the host must be restarted. Verify with `ls ~/.claude/skills/pyxel/SKILL.md`. If absent, run `uvx pyxel-mcp publish-skill ~/.claude/skills/pyxel`.

**Pyxel script crashes on `pyxel.init()`.** The harness already wraps `init()` in headless mode; user scripts should call it once, in `App.__init__`. Calling it twice in the same process raises — but each tool call is its own subprocess, so this only bites when a custom test fixture re-imports the user module.

**`validate` reports `tilemap_zero_zero` / `cls_missing` / etc. — what does it mean?** Read `@pyxel:anti-patterns` for the catalog (severity, rationale, canonical fix per category).

**Diagnostic line says `workflow=<unavailable: …>`.** The wheel was installed without the workflow build artifact (rare — usually means a pip-from-sdist install with the build hook disabled). Server still works for the 9 tools; only `pyxel://workflow/*` resources and `publish-skill` require the workflow content. Reinstall via `uvx pyxel-mcp` to pick up the wheel.

## MCP Registry

`mcp-name: io.github.kitao/pyxel-mcp`

## License

MIT
