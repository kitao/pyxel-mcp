# pyxel-skill Hooks

This directory contains the Claude Code Stop hook used by `pyxel-skill`. The hook is a non-blocking tripwire that warns when the quality gate appears to have been skipped.

## Files

| File | Purpose |
|------|---------|
| `stop_check_bundle.py` | The Stop hook itself. Reads `cwd` from the Stop event, checks for `.pyxel-skill/` project marker, walks `screenshots/result/<latest>/` for proof bundle shape, and warns to stderr if required artifacts or `gate-report.json` are missing. Always exits 0 with `{}` on stdout (non-blocking). |
| `test_stop_check_bundle.py` | pytest suite for the hook (6 cases). Run: `python -m pytest hooks/`. |
| `install.sh` | Idempotent installer. Adds an entry to `~/.claude/settings.json` under `hooks.Stop`. Requires `jq`. |
| `README.md` | This file. |

## Install

```bash
hooks/install.sh
```

The installer reads `$HOME/.claude/settings.json` (or `$CLAUDE_SETTINGS` if set, useful for testing) and appends an entry. Running it twice is safe.

## Uninstall

Edit `~/.claude/settings.json` and remove the entry under `hooks.Stop` whose `command` matches the absolute path of `stop_check_bundle.py`.

## Why a Stop hook

`pyxel-skill`'s quality gate (Stage 7) is the contract for "done". The agent is expected to run the gate and address all FAILs before declaring completion. Empirically, agents skip steps when allowed to. The Stop hook is a session-boundary tripwire that surfaces a missed gate to the user as a warning — it does **not** block the session and does **not** replace the agent running the gate.

## Behavior

| Project state | Hook output |
|---------------|-------------|
| cwd has no `.pyxel-skill/` directory | silent no-op |
| `.pyxel-skill/` exists, no `screenshots/result/` | warns "no proof bundle found" |
| `screenshots/result/<N>/` exists but win/lose media, frame PNGs, audio WAVs, or `notes.md` are missing | warns "bundle is incomplete" |
| Complete proof bundle shape plus `gate-report.json` exists | silent; the hook does not parse gate contents |
| All clean | silent |

In every case the hook prints `{}` on stdout and exits 0. It cannot block Claude Code from terminating.

## Testing

```bash
cd /Users/takashi/repos/pyxel-skill
python -m pytest hooks/test_stop_check_bundle.py -v
```

Six tests cover: no-marker no-op, missing-bundle warning, incomplete-bundle warning, missing-gate-report warning, complete-bundle silence, malformed-input non-blocking.
