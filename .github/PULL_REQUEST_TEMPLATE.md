## Summary

<!-- What changes and why. Link the issue when there is one. -->

## Contract impact

- [ ] No public tool, resource, or result-field change
- [ ] Additive change (new optional field or parameter), documented in `CHANGELOG.md`
- [ ] Breaking change, marked `BREAKING:` in `CHANGELOG.md` and reflected in `instructions.md` and `README.md`

## Verification

- [ ] `uv run pytest -q` passes locally
- [ ] `uv run ruff check` and `uv run ruff format --check` pass
- [ ] New behavior has a test; harness changes have a subprocess-level test
