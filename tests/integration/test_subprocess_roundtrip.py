import json
import subprocess
import sys

import pytest

from tests.conftest import SCRIPTS


def _run(subcommand: str, payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pyxel_mcp.observe._harnesses.main", subcommand],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    return json.loads(proc.stdout)


def test_validate_via_subprocess():
    result = _run("validate", {"script": str(SCRIPTS / "minimal.py")})
    assert result["ok"] is True


def test_pyxel_info_via_subprocess():
    result = _run("pyxel_info", {})
    assert "pyxel_version" in result
    assert result["resources"]["run_snapshots_schema"] == "pyxel://run-snapshots-schema"


def test_relative_asset_paths_resolve_from_the_script_directory():
    """`pyxel.load("assets/...")` must work exactly as under `python game.py`."""
    result = _run(
        "run",
        {
            "script": str(SCRIPTS / "relative_asset.py"),
            "frames": 1,
            "snapshots": [{"kind": "state", "frame": 0, "attrs": ["loaded_color"]}],
        },
    )
    assert result["exit_status"] == "ok", result["errors"]
    assert result["snapshots"][0]["values"]["loaded_color"] != 0


def test_read_tools_share_the_script_context():
    result = _run("read_palette", {"script": str(SCRIPTS / "relative_asset.py")})
    assert result["ok"] is True, result["errors"]


def test_bundled_pyxel_example_runs_with_its_assets():
    info = _run("pyxel_info", {})
    hello = next((e for e in info["examples"] if e["name"] == "01_hello_pyxel"), None)
    if hello is None:
        pytest.skip("01_hello_pyxel is not bundled with this Pyxel build")

    result = _run("run", {"script": hello["path"], "frames": 2})
    assert result["exit_status"] == "ok", result["errors"]
