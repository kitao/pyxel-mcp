import json
import subprocess
import sys
from tests.conftest import SCRIPTS


def _run(subcommand: str, payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pyxel_mcp._harnesses.main", subcommand],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=10,
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
