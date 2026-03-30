# Version Check in pyxel_info

## Summary

Add update notifications to the `pyxel_info` MCP tool. When a newer version
of `pyxel-mcp` or `pyxel` is available on PyPI, append an informational line
to the tool output so the AI can relay it to the user.

## Motivation

Users who install pyxel-mcp or pyxel may never learn about newer versions
unless they actively check. A passive, non-intrusive notification in
`pyxel_info` — the first tool called each session — solves this without
forcing updates.

## Design

### Where

The existing `pyxel_info` tool in `server.py`. No new tools or files.

### How it works

1. After building the current `pyxel_info` output, check PyPI for the latest
   versions of both `pyxel-mcp` and `pyxel`.
2. For each package, compare the installed version (via `importlib.metadata`)
   with the latest on PyPI (via `https://pypi.org/pypi/{pkg}/json`).
3. If a newer version exists, append a line:
   `Update available: {pkg} {installed} → {latest} (pip install --upgrade {pkg})`
4. If versions are current, add nothing.
5. If the check fails (network error, timeout, parse error), skip silently.

### Technical details

- **HTTP client**: `urllib.request` (stdlib, no new dependencies)
- **Timeout**: ~3 seconds per request
- **Version comparison**: Simple tuple comparison on split version segments;
  no `packaging` dependency needed
- **Installed version**: `importlib.metadata.version()`

### Output example

```
Pyxel package: /path/to/pyxel
API type stubs: /path/to/pyxel/__init__.pyi (found)
Examples dir: /path/to/pyxel/examples (found)
Examples: 01_hello_pyxel.py, 02_jump_game.py, ...
Update available: pyxel-mcp 0.9.1 → 1.0.0 (pip install --upgrade pyxel-mcp)
Update available: pyxel 2.8.9 → 2.9.0 (pip install --upgrade pyxel)
```

### Behavior on failure

Silent skip — the user sees normal `pyxel_info` output with no mention of
version checking. No error messages, no warnings.

### What this does NOT do

- Does not auto-update anything
- Does not block or slow down noticeably under normal network conditions
- Does not add new dependencies
- Does not add new MCP tools
