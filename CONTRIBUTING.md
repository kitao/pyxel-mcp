# Contributing

Bug reports and small fixes are welcome. For larger changes, please open an
issue first so the tool contract can be discussed before code is written.

## Scope

pyxel-mcp observes Pyxel programs and reports facts. Game-building guidance,
quality judgments, and workflow advice belong in
[pyxel-skill](https://github.com/kitao/pyxel-skill), not here.

## Development setup

```bash
git clone https://github.com/kitao/pyxel-mcp.git
cd pyxel-mcp
uv sync --extra dev
```

## Checks

```bash
uv run pytest -q
uv run ruff check
uv run ruff format --check
```

CI runs pytest on Python 3.11 and 3.14 and the two ruff checks on Python 3.12.
Tag releases run the same checks before building or publishing.

Notes:

- Tests drive Pyxel (installed as a dependency) headlessly through SDL dummy
  drivers, so no display is needed.
- `tests/conftest.py` generates the PNG fixtures under
  `tests/fixtures/images/` on first run; they are intentionally gitignored.
- Anything that changes how the subprocess harness loads or drives a script
  needs a test in `tests/integration/test_subprocess_roundtrip.py`, because
  in-process tests share one already-imported Pyxel.

## Layout

- `src/pyxel_mcp/server.py` registers the eight tools with the MCP SDK.
- `src/pyxel_mcp/contracts.py` holds the public input and output models.
- `src/pyxel_mcp/dispatch.py` is the subprocess boundary.
- `src/pyxel_mcp/observe/_harnesses/` runs inside the subprocess: one module
  per tool under `tools/`, shared pieces under `_common/`.
- `src/pyxel_mcp/_resources/` serves the `pyxel://` resources.

## Releasing

1. Update the version in `pyproject.toml` and `server.json` (two places), and
   add a `## x.y.z` section to `CHANGELOG.md`.
2. Commit, tag `vX.Y.Z`, and push the tag. The release workflow runs the
   checks above, builds the package, publishes it to PyPI through trusted
   publishing, and then publishes `server.json` to the MCP Registry through
   GitHub OIDC.

The PyPI step runs only while the repository variable
`PYPI_TRUSTED_PUBLISHING` is `true`, which requires a trusted publisher on
PyPI for `release.yml` with the `pypi` environment. Without it, upload the
package by hand before pushing the tag; the registry step still runs because
it only needs the version to exist on PyPI:

```bash
uv build && twine upload dist/*
```
