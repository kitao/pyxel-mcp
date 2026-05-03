"""Tests for hooks/stop_check_bundle.py — pyxel-skill Stop hook."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

HOOK = Path(__file__).parent / "stop_check_bundle.py"


def run_hook(event: dict, cwd: Path) -> tuple[str, str, int]:
    """Run the hook as a subprocess with given event on stdin and cwd."""
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    return proc.stdout, proc.stderr, proc.returncode


def test_no_op_when_not_a_pyxel_skill_project(tmp_path: Path) -> None:
    """Hook silently returns {} when .pyxel-skill/ marker is absent."""
    out, err, rc = run_hook({"cwd": str(tmp_path)}, tmp_path)
    assert rc == 0
    assert json.loads(out) == {}
    assert err == ""


def test_warns_when_marker_present_but_no_bundle(tmp_path: Path) -> None:
    """Hook prints a warning when .pyxel-skill/ exists but no screenshots/result/."""
    (tmp_path / ".pyxel-skill").mkdir()
    out, err, rc = run_hook({"cwd": str(tmp_path)}, tmp_path)
    assert rc == 0
    assert json.loads(out) == {}
    assert "no proof bundle" in err.lower()


def test_warns_when_bundle_lacks_video(tmp_path: Path) -> None:
    """Hook warns if latest screenshots/result/<N>/ has no win-path.gif."""
    (tmp_path / ".pyxel-skill").mkdir()
    bundle = tmp_path / "screenshots" / "result" / "1"
    bundle.mkdir(parents=True)
    out, err, rc = run_hook({"cwd": str(tmp_path)}, tmp_path)
    assert rc == 0
    assert json.loads(out) == {}
    assert "win-path" in err.lower() or "incomplete" in err.lower()


def test_warns_when_bundle_lacks_gate_report(tmp_path: Path) -> None:
    """Hook warns when bundle has artifacts but gate-report.json is missing
    (= quality gate did not run). The hook does NOT inspect gate-report content."""
    (tmp_path / ".pyxel-skill").mkdir()
    bundle = tmp_path / "screenshots" / "result" / "1"
    bundle.mkdir(parents=True)
    (bundle / "win-path.gif").write_bytes(b"GIF89a")
    out, err, rc = run_hook({"cwd": str(tmp_path)}, tmp_path)
    assert rc == 0
    assert json.loads(out) == {}
    assert "gate-report.json" in err.lower() or "quality gate did not run" in err.lower()


def test_silent_pass_on_complete_bundle(tmp_path: Path) -> None:
    """Hook silently returns {} when bundle has win-path video AND gate-report.json
    exists. The hook does NOT parse gate-report content — that is the agent's
    responsibility (the agent ran the gate and wrote the JSON)."""
    (tmp_path / ".pyxel-skill").mkdir()
    bundle = tmp_path / "screenshots" / "result" / "1"
    bundle.mkdir(parents=True)
    (bundle / "win-path.gif").write_bytes(b"GIF89a")
    (bundle / "lose-path.gif").write_bytes(b"GIF89a")
    # Even a FAIL gate-report.json: the hook is content-agnostic.
    (bundle / "gate-report.json").write_text(json.dumps({
        "attempt": 1,
        "fps": 30,
        "checks": [{"id": 5, "label": "Win path", "result": "FAIL", "evidence": "x"}],
        "summary": {"pass": 10, "fail": 1, "total": 11},
    }))
    out, err, rc = run_hook({"cwd": str(tmp_path)}, tmp_path)
    assert rc == 0
    assert json.loads(out) == {}
    assert "warn" not in err.lower()
    assert "fail" not in err.lower()


def test_never_blocks_on_unexpected_input(tmp_path: Path) -> None:
    """Hook returns {} (non-blocking) even on malformed input."""
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input="not valid json",
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0
    # Either {} or some error JSON, but rc must be 0 to avoid blocking stop.
