import json
import subprocess
import sys


def _run_subprocess(subcommand: str, payload: dict) -> tuple[int, dict, str]:
    """Run pyxel_mcp._harnesses.main as subprocess. Returns (exit_code, stdout_json, stderr)."""
    proc = subprocess.run(
        [sys.executable, "-m", "pyxel_mcp._harnesses.main", subcommand],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    out = json.loads(proc.stdout) if proc.stdout.strip() else {}
    return proc.returncode, out, proc.stderr


def test_unknown_subcommand_returns_validation_error():
    code, out, err = _run_subprocess("nonexistent", {})
    assert code == 0  # subprocess exits 0; failure is in errors
    assert out["errors"][0]["phase"] == "validation"
    assert "unknown subcommand" in out["errors"][0]["message"].lower()


def test_invalid_json_stdin_returns_validation_error():
    proc = subprocess.run(
        [sys.executable, "-m", "pyxel_mcp._harnesses.main", "validate"],
        input="not json {{{",
        capture_output=True,
        text=True,
    )
    out = json.loads(proc.stdout)
    assert out["errors"][0]["phase"] == "validation"
    assert "json" in out["errors"][0]["message"].lower()
