import re
from pyxel_mcp._harnesses.tools.pyxel_info import run as pyxel_info_run


def test_returns_required_fields():
    result = pyxel_info_run({})
    for key in ("pyxel_mcp_version", "pyxel_version", "python_version",
                "stubs_path", "examples", "resources", "errors"):
        assert key in result


def test_versions_look_like_versions():
    result = pyxel_info_run({})
    assert re.match(r"^\d+\.\d+\.\d+", result["pyxel_mcp_version"])
    assert re.match(r"^\d+\.\d+\.\d+", result["pyxel_version"])


def test_resources_includes_run_snapshots_schema():
    result = pyxel_info_run({})
    assert result["resources"]["run_snapshots_schema"] == "pyxel://run-snapshots-schema"


def test_examples_have_paths():
    result = pyxel_info_run({})
    assert isinstance(result["examples"], list)
    for ex in result["examples"]:
        assert "name" in ex and "path" in ex
