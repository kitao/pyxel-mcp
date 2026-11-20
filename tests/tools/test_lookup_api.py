from pyxel_mcp.api import lookup


def test_signatures_docs_and_overloads_come_from_stubs():
    result = lookup("Image.clip")
    assert result["name"] == "pyxel.Image.clip"
    assert len(result["declarations"]) == 2
    assert all("def clip(self," in d for d in result["declarations"])
    assert "drawing area" in result["declarations"][0]
    assert "pyxel.colors[:]" in lookup("colors")["declarations"][0]


def test_cube_class_members_and_partial_discovery():
    cls = lookup("cube.Vec3")
    assert "lerp" in cls["members"]
    assert any("def __init__(" in d for d in cls["declarations"])
    assert lookup("Vec3.lerp")["name"] == "pyxel.cube.Vec3.lerp"
    partial = lookup("KEY_")
    assert partial["match_count"] > len(partial["matches"]) == 30
    assert lookup("no_such_symbol")["match_count"] == 0
    assert not lookup("Node()")["ok"]
