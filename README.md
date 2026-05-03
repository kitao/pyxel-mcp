# pyxel-mcp

MCP server for [Pyxel](https://github.com/kitao/pyxel), a retro game engine for Python. Gives AI agents the verbs to **run, observe, judge, and ship** Pyxel programs end-to-end without a window — headless, deterministic, gate-able. Includes a bundled production workflow skill (Layer 3) so the agent has a phased pipeline, not just isolated verbs.

## Why this exists

LLM agents writing Pyxel code without verification produce shortcut games: placeholder rectangles, stalled play loops, missing assets, scripts that compile but render black. pyxel-mcp is the verb library that lets the agent **see** what its code actually does — and the workflow skill is the recipe that keeps it honest from concept to playable bundle.

- **Headless + fast-forward.** 600-frame run < 1 second. Pyxel's internal fps is overridden so `flip()` doesn't pace real-time.
- **Subprocess isolation.** Each Layer 1 tool call is a fresh Python subprocess. No leaked Pyxel state; deterministic with `random_seed=`.
- **Structured output.** Every tool returns JSON with a uniform `ok` / error shape — agents chain calls predicating on observed values, not stdout strings.
- **Pyxel footguns caught structurally.** (0,0) tilemap trap, draw-without-cls ghost trails, palette animation in `update`, run-outside-init — flagged by `validate` and `read_*`, not by squinting at screenshots.
- **Quality is a contract, not vibes.** Layer 2 (`judge_*`) maps observations against PLAN.md / ASSETS.md contracts and returns `pass`/`warn`/`fail` + a `fail_route`. The workflow skill turns those routes into a 17-check quality gate that refuses to declare "done" until every milestone, asset, audio slot, and proof bundle clears.

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
[pyxel-mcp] starting — 17 tools (Layer 1: 9, Layer 2: 8), workflow=/path/to/skill
```

Pyxel ≥ 2.9.4 is fetched as a transitive dependency.

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

## Tools — Layer 1 (observe, 9 tools)

Run the script, read raw Pyxel state, diff frames. Each call is a fresh subprocess.

| Tool | What it returns |
|---|---|
| `run` | Drives N frames headless. Snapshots: `screen_image`, `screen_grid`, `state`, `layout`, `video`. Inputs schedule (`set_btn`/`set_btnv`/`set_mouse_pos`). `ASSERT` parsing. `random_seed` for determinism. |
| `validate` | Static analysis: syntax + 10 anti-pattern detectors (`cls_missing`, `palette_animation`, `tilemap_zero_zero`, `update_in_draw`, `iter_modify`, …). |
| `pyxel_info` | Versions, example paths, resource URIs. |
| `read_palette` | `pyxel.colors` analysis: 3-layer hierarchy (bg/env/interactive), WCAG contrast warnings filtered to **co-located** pairs only. |
| `read_image` | Image-bank region pixels + `color_count`, `fill_ratio`, `symmetry`, `edge_density`. Optional PNG render. |
| `read_animation` | Cross-region Jaccard / per-pair diff for paired sprite frames. |
| `read_tilemap` | Tilemap usage map + (0,0)-tile trap detection. |
| `read_audio` | Render `pyxel.sounds[N]` / `pyxel.musics[N]` to WAV; return `notes`, `peak_amplitude`, `warnings`. |
| `diff_frames` | Pixel-wise diff of two PNGs: `identical`, `ratio`, bounding box. |

## Tools — Layer 2 (judge, 8 tools)

Pure functions: `(observation, contract=None) → {ok, verdict, evidence, fail_route, details}`. Pass a Layer 1 result as `observation`; pass a contract dict (extracted from PLAN.md / ASSETS.md, or omit for module defaults). `fail_route` names the workflow stage to revisit.

| Tool | Pairs with | Routes failures to |
|---|---|---|
| `judge_palette` | `read_palette` | asset-planning / sprite-quality |
| `judge_sprite` | `read_image` | sprite-quality |
| `judge_animation` | `read_animation` | sprite-quality |
| `judge_milestone` | `run` (state snapshots) | playthrough / spec |
| `judge_genre` | `run` (assertions + log) | spec / playthrough |
| `judge_bundle` | bundle dir | bundle |
| `judge_audio` | `read_audio` | sprite-quality / scaffolding |
| `judge_layout` | `run` (layout snapshot) | scaffolding |

`judge_milestone` is Pattern D: snapshots are indexed by `(kind, frame)` and per-frame predicates are evaluated in a sandboxed namespace (no `Call` nodes, no imports — comparisons / boolean ops / attribute / subscript only). Dotted state keys (`player.x`) auto-promote to nested attribute access.

## Workflow skill (Layer 3) and resources

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

**Tools don't appear in the client.** Confirm the server started: look for `[pyxel-mcp] starting — 17 tools` in your client's MCP server logs. If absent, the snippet wasn't picked up — re-check the path you pasted into. If present but tools are missing, restart the client (some clients cache the tool list across config edits).

**Skill doesn't activate on prompts.** The skill must be in the host's skill directory and the host must be restarted. Verify with `ls ~/.claude/skills/pyxel/SKILL.md`. If absent, run `uvx pyxel-mcp publish-skill ~/.claude/skills/pyxel`.

**Pyxel script crashes on `pyxel.init()`.** The harness already wraps `init()` in headless mode; user scripts should call it once, in `App.__init__`. Calling it twice in the same process raises — but each tool call is its own subprocess, so this only bites when a custom test fixture re-imports the user module.

**`validate` reports `tilemap_zero_zero` / `cls_missing` / etc. — what does it mean?** Read `@pyxel:anti-patterns` for the catalog (severity, rationale, canonical fix per category).

**Diagnostic line says `workflow=<unavailable: …>`.** The wheel was installed without the workflow build artifact (rare — usually means a pip-from-sdist install with the build hook disabled). Server still works for Layer 1+2 tools; only `pyxel://workflow/*` resources and `publish-skill` require the workflow content. Reinstall via `uvx pyxel-mcp` to pick up the wheel.

## MCP Registry

`mcp-name: io.github.kitao/pyxel-mcp`

## License

MIT
