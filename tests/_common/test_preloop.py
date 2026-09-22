"""Tests for synchronous observations at the pyxel.run checkpoint."""

import pytest

from pyxel_mcp.observe._harnesses._common.preloop import PreloopFailed, run_to_preloop
from tests.conftest import SCRIPTS


def _empty(error: dict) -> dict:
    return {"ok": False, "errors": [error]}


def _observe(_state):
    return {"ok": True, "errors": []}


@pytest.mark.parametrize("payload", [{}, {"script": "/no/such/file.py"}])
def test_invalid_script_raises_preloop_failed(payload):
    with pytest.raises(PreloopFailed) as failure:
        run_to_preloop(payload, empty_factory=_empty, observe=_observe)
    assert failure.value.result["ok"] is False
    assert failure.value.result["errors"][0]["phase"] == "validation"
    if "script" in payload:
        assert failure.value.result["errors"][0]["path"] == payload["script"]


def test_no_pyxel_run_raises_preloop_failed():
    with pytest.raises(PreloopFailed) as failure:
        run_to_preloop(
            {"script": str(SCRIPTS / "no_pyxel_run.py")},
            empty_factory=_empty,
            observe=_observe,
        )
    assert failure.value.result["errors"][0]["phase"] == "script_import"


def test_observer_uses_resource_before_context_manager_closes_it(tmp_path):
    resource = tmp_path / "input.txt"
    resource.write_text("resource still open")
    script = tmp_path / "app.py"
    script.write_text(
        "import pyxel\n"
        "class App:\n"
        "    def __init__(self):\n"
        "        pyxel.init(8, 8)\n"
        f"        with open({str(resource)!r}) as self.resource:\n"
        "            pyxel.run(self.update, self.draw)\n"
        "            raise RuntimeError('must not run after checkpoint')\n"
        "    def update(self): pass\n"
        "    def draw(self): pass\n"
        "App()\n"
    )
    seen = {}

    def observe(state):
        seen["app"] = state.app_instance
        return {"text": state.app_instance.resource.read()}

    result = run_to_preloop(
        {"script": str(script)}, empty_factory=_empty, observe=observe
    )
    assert result == {"text": "resource still open"}
    assert seen["app"].resource.closed


def test_observer_failure_is_an_artifact_error_and_still_stops_script(tmp_path):
    marker = tmp_path / "returned.txt"
    script = tmp_path / "app.py"
    script.write_text(
        "import pyxel\nfrom pathlib import Path\npyxel.init(8, 8)\n"
        "try:\n"
        "    pyxel.run(lambda: None, lambda: None)\n"
        "except Exception:\n"
        f"    Path({str(marker)!r}).write_text('caught observer failure')\n"
        f"Path({str(marker)!r}).write_text('continued after run')\n"
    )

    def observe(_state):
        raise OSError("cannot save observation")

    result = run_to_preloop(
        {"script": str(script)}, empty_factory=_empty, observe=observe
    )
    assert result["ok"] is False
    assert result["errors"][0]["phase"] == "artifact"
    assert "cannot save observation" in result["errors"][0]["message"]
    assert not marker.exists()
