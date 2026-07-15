import re
from pyxel_mcp.observe._harnesses.tools.pyxel_info import run as pyxel_info_run


def test_returns_required_fields():
    result = pyxel_info_run({})
    for key in ("pyxel_mcp_version", "pyxel_version", "python_version",
                "stubs_path", "examples", "resources", "errors"):
        assert key in result


def test_versions_look_like_versions():
    result = pyxel_info_run({})
    assert re.match(r"^\d+\.\d+\.\d+", result["pyxel_mcp_version"])
    assert re.match(r"^\d+\.\d+\.\d+", result["pyxel_version"])
    assert re.match(r"^\d+\.\d+\.\d+", result["python_version"])


def test_errors_empty_on_success():
    result = pyxel_info_run({})
    assert result["errors"] == []


def test_resources_has_expected_uris():
    """Verify every advertised resource URI is present and correct.

    The server exposes only local, version-matched resources.
    """
    result = pyxel_info_run({})
    assert result["resources"] == {
        "default_palette": "pyxel://palette/default",
        "examples": "pyxel://examples/{name}",
        "run_snapshots_schema": "pyxel://run-snapshots-schema",
        "validation_patterns": "pyxel://validation-patterns",
    }


def test_examples_have_paths():
    result = pyxel_info_run({})
    assert isinstance(result["examples"], list)
    for ex in result["examples"]:
        assert "name" in ex and "path" in ex
