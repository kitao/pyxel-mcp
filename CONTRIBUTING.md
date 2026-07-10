# Contributing

Bug reports and small fixes are welcome. For larger changes, please open an
issue first.

## Development setup

```bash
git clone https://github.com/kitao/pyxel-mcp.git
cd pyxel-mcp
uv sync --extra test
```

## Running tests

```bash
uv run pytest
```

Notes:

- Tests marked `integration` require Pyxel (installed as a dependency). The
  harness runs it headlessly via SDL dummy drivers, so no display is needed.
- `tests/conftest.py` generates the PNG fixtures under
  `tests/fixtures/images/` on first run; they are intentionally gitignored.
