"""End-state observation must not eagerly execute game code."""

import json
from textwrap import dedent

import pytest

from pyxel_mcp.server import run
from tests.conftest import structured


@pytest.mark.parametrize("stop", ["cap", "until", "stall"])
def test_normal_end_evaluates_getters_repr_and_indexing_only_once(tmp_path, stop):
    script = tmp_path / "game.py"
    script.write_text(
        dedent(
            """
            from functools import cached_property
            import pyxel

            class Value:
                def __init__(self, app): self.app = app
                def __repr__(self):
                    self.app.repr_reads += 1
                    return f"value={self.app.counter}"
                def __getitem__(self, index):
                    self.app.index_reads += 1
                    return self.app.counter

            class App:
                def __init__(self):
                    self.counter = self.frozen = 0
                    self.getter_reads = self.repr_reads = self.index_reads = 0
                    self.value = Value(self)
                    pyxel.init(8, 8)
                    pyxel.run(self.update, lambda: pyxel.cls(1))
                def update(self): self.counter += 1
                @cached_property
                def final_score(self): return self.counter
                @property
                def current_score(self):
                    self.getter_reads += 1
                    return self.counter
            App()
            """
        )
    )
    snapshots = [
        {
            "kind": "state",
            "frame": "end",
            "attrs": [
                "counter",
                "final_score",
                "current_score",
                "value",
                "value[0]",
                "getter_reads",
                "repr_reads",
                "index_reads",
            ],
        }
    ]
    options = {}
    if stop == "until":
        options["until"] = "counter >= 3"
    elif stop == "stall":
        options["stall_window_frames"] = 3
        snapshots.append({"kind": "state", "frames": "all", "attrs": ["frozen"]})
    result = structured(
        run(script=str(script), frames=4, snapshots=snapshots, **options)
    )
    completed = 4 if stop == "cap" else 3
    assert result["frame_count"] == completed
    assert result["exit_status"] == ("stalled" if stop == "stall" else "ok")
    assert result["errors"] == []
    assert result["snapshots"][-1]["values"] == {
        "counter": completed,
        "final_score": completed,
        "current_score": completed,
        "value": f"value={completed}",
        "value[0]": completed,
        "getter_reads": 1,
        "repr_reads": 1,
        "index_reads": 1,
    }


def test_quit_preserves_plain_state_without_evaluating_dynamic_values(tmp_path):
    script = tmp_path / "game.py"
    script.write_text(
        dedent(
            """
            import json
            from functools import cached_property
            from pathlib import Path
            import numpy as np
            import pyxel

            class Value:
                def __init__(self, app): self.app = app
                def __repr__(self):
                    self.app.reads += 1
                    return "dynamic value"
                def __getitem__(self, index):
                    self.app.reads += 1
                    return self.app.counter

            class App:
                def __init__(self):
                    self.counter = self.reads = 0
                    self.history = []
                    self.mapping = {"counter": 0}
                    self.array = np.array([0])
                    self.value = Value(self)
                    pyxel.init(8, 8)
                    try:
                        with open("resource.txt", "w") as self.resource:
                            pyxel.run(self.update, lambda: pyxel.cls(1))
                    finally:
                        Path("reads.json").write_text(json.dumps({
                            "reads": self.reads,
                            "cached": "final_score" in self.__dict__,
                        }))
                def update(self):
                    self.counter += 1
                    self.history.append(self.counter)
                    self.mapping["counter"] = self.counter
                    self.array[0] = self.counter
                    if self.counter == 3:
                        self.counter = 999
                        self.history.append(999)
                        self.mapping["counter"] = self.array[0] = 999
                        pyxel.quit()
                @cached_property
                def final_score(self): return self.counter
                @property
                def current_score(self):
                    self.reads += 1
                    return self.counter
            App()
            """
        )
    )
    result = structured(
        run(
            script=str(script),
            frames=5,
            snapshots=[
                {
                    "kind": "state",
                    "frame": "end",
                    "attrs": [
                        "counter",
                        "history",
                        "mapping",
                        "array",
                        "final_score",
                        "current_score",
                        "value",
                        "value[0]",
                        "resource.closed",
                    ],
                }
            ],
        )
    )
    assert result["ok"] is True, result["errors"]
    assert result["frame_count"] == 2
    snapshot = result["snapshots"][0]
    assert snapshot["frame"] == 1
    assert snapshot["values"] == {
        "counter": 2,
        "history": [1, 2],
        "mapping": {"counter": 2},
        "array": [2],
    }
    for path in (
        "final_score",
        "current_score",
        "value",
        "value[0]",
        "resource.closed",
    ):
        assert any(
            f"attr '{path}' omitted after quit" in w for w in snapshot["warnings"]
        )
    assert json.loads((tmp_path / "reads.json").read_text()) == {
        "reads": 0,
        "cached": False,
    }


@pytest.mark.parametrize("frame", [2, "end"])
def test_quit_from_a_snapshot_getter_is_an_artifact_failure(tmp_path, frame):
    script = tmp_path / "game.py"
    script.write_text(
        dedent(
            """
            import pyxel
            class App:
                def __init__(self):
                    self.counter = 0
                    pyxel.init(8, 8)
                    pyxel.run(self.update, lambda: pyxel.cls(self.counter))
                def update(self): self.counter += 1
                @property
                def value(self): pyxel.quit()
            App()
            """
        )
    )
    result = structured(
        run(
            script=str(script),
            frames=3,
            snapshots=[
                {"kind": "screen_grid", "frame": 2, "bbox": [0, 0, 1, 1]},
                {"kind": "state", "frame": frame, "attrs": ["value"]},
            ],
        )
    )
    assert result["ok"] is False
    assert result["exit_status"] == "crashed"
    assert result["frame_count"] == 3
    assert result["errors"][0]["phase"] == "artifact"
    assert result["errors"][0]["frame"] == 2
    assert "pyxel.quit()" in result["errors"][0]["message"]
    assert len(result["snapshots"]) == 1
    assert result["snapshots"][0]["frame"] == 2
    assert result["snapshots"][0]["grid"] == [[3]]


def test_quit_from_until_evaluation_is_an_until_failure(tmp_path):
    script = tmp_path / "game.py"
    script.write_text(
        "import pyxel\npyxel.init(8, 8)\n"
        "def stop(): pyxel.quit()\n"
        "pyxel.run(lambda: None, lambda: pyxel.cls(1))\n"
    )
    result = structured(
        run(
            script=str(script),
            frames=3,
            until="stop()",
            snapshots=[{"kind": "screen_grid", "frame": 0, "bbox": [0, 0, 1, 1]}],
        )
    )
    assert result["ok"] is False
    assert result["frame_count"] == 1
    assert result["until_met"] is None
    assert result["errors"][0]["phase"] == "until"
    assert result["errors"][0]["frame"] == 0
    assert "pyxel.quit()" in result["errors"][0]["message"]
    assert result["snapshots"][0]["grid"] == [[1]]
