"""Smoke tests for pyxel_env helpers."""

from pyxel_mcp._common.pyxel_env import (
    pyxel_dir,
    check_script,
    installed_version,
    parse_version,
    check_updates,
)


def test_parse_version_ok():
    assert parse_version("1.2.3") == (1, 2, 3)


def test_parse_version_bad():
    assert parse_version("not-a-version") == ()


def test_installed_version_returns_str_or_none():
    v = installed_version("pyxel-mcp")
    assert v is None or isinstance(v, str)
