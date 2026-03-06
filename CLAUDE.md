# Pyxel MCP

MCP server for Pyxel — enables AI agents to run, verify, and iterate on retro game programs.

## Structure

```
src/pyxel_mcp/
  server.py              MCP server (FastMCP, tool registration)
  harness.py             Screenshot capture
  frames_harness.py      Multi-frame capture
  audio_harness.py       Sound rendering to WAV
  sprite_harness.py      Sprite pixel inspection
  layout_harness.py      Screen layout analysis
```

## Build

```
source .venv/bin/activate
uv run python -m pyxel_mcp.server   # run locally
```

Pure Python — no build step. Uses UV for dependency management.

## Coding Conventions

- Follow Python idioms — natural, concise code
- Comments in concise English
- Use blank lines between logical sections, not after every line
- Leading underscore for private module-level names
- Each harness is a standalone subprocess script: parse args, patch Pyxel, execute, output JSON
- Never import Pyxel in the main server process — only in subprocess harnesses

## Release

Always confirm the version number before releasing.
Update version in `pyproject.toml`, `server.json` (2 places), and `CHANGELOG.md`.

```
rm -rf dist/ && .venv/bin/python -m build
.venv/bin/python -m twine upload dist/*
git push origin main
```

Publish to MCP Registry (token may need re-login):

```
/tmp/mcp-publisher login github
/tmp/mcp-publisher publish server.json
```

## CHANGELOG

Maintained in `CHANGELOG.md` at the repo root.

- `## x.y.z` header with `- ` bullet points
- Concise English, one item per line, start with a verb (Added, Fixed, Removed, etc.)
- Flat list only — no nested sub-items
- Under 60 characters; 80 max for complex entries
- Newest entries first within each section
