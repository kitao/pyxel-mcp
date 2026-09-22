"""State observations stay valid and lossless across the public MCP boundary."""

import json

from pyxel_mcp.server import mcp
from tests.conftest import structured


async def test_unusual_state_values_survive_the_public_tool_reply(tmp_path):
    script = tmp_path / "unusual_state.py"
    script.write_text(
        """import numpy as np
import pyxel
nan_value = float('nan')
inf_value = np.float64('inf')
negative_inf = float('-inf')
values = [1, float('nan')]
mapping = {'score': float('inf')}
colliding_keys = {1: 'integer', '1': 'string', None: 5}
numeric_array = np.array([[1, float('nan'), float('inf'), float('-inf')]])
complex_array = np.array([1 + 2j])
object_array = np.array([{'score': 1}], dtype=object)
pyxel.init(16, 16)
pyxel.run(lambda: None, lambda: pyxel.cls(0))
"""
    )
    reply = await mcp.call_tool(
        "run",
        {
            "script": str(script),
            "frames": 1,
            "snapshots": [
                {"kind": "state", "frame": "end"},
                {
                    "kind": "state",
                    "frame": "end",
                    "attrs": [
                        "values",
                        "mapping",
                        "colliding_keys",
                        "numeric_array",
                        "complex_array",
                        "object_array",
                    ],
                },
            ],
        },
    )
    result = structured(reply)
    assert result["ok"] is True, result["errors"]
    assert result["frame_count"] == 1
    assert result["snapshots"][0]["values"] == {
        "nan_value": "nan",
        "inf_value": "inf",
        "negative_inf": "-inf",
    }
    values = result["snapshots"][1]["values"]
    assert values["values"] == [1, "nan"]
    assert values["mapping"] == {"score": "inf"}
    assert values["numeric_array"] == [[1, "nan", "inf", "-inf"]]
    assert values["colliding_keys"] == "{1: 'integer', '1': 'string', None: 5}"
    assert values["complex_array"] == "array([1.+2.j])"
    assert "'score': 1" in values["object_array"]
    # Strict JSON encoding rejects NaN/Infinity in both structured and text
    # content, before any transport or client can reinterpret those values.
    json.dumps(result, allow_nan=False)
    assert json.loads(reply.content[0].text) == result
    json.dumps(json.loads(reply.content[0].text), allow_nan=False)
