"""Observe callback lifetimes and early exits through real subprocesses."""

from textwrap import dedent

import pytest
from PIL import Image

from pyxel_mcp.server import run
from tests.conftest import structured


def _script(tmp_path, source):
    path = tmp_path / "game.py"
    path.write_text(dedent(source), encoding="utf-8")
    return str(path)


@pytest.mark.parametrize("until, completed", [(None, 3), ("counter >= 2", 2)])
def test_observation_keeps_resources_open_until_snapshots_are_complete(
    tmp_path, until, completed
):
    script = _script(
        tmp_path,
        """
        from pathlib import Path
        import pyxel

        pyxel.init(8, 8)
        counter = 0
        active = True
        resource = open("resource.txt", "w")

        def update():
            global counter
            assert active and not resource.closed
            counter += 1
            resource.write(f"{counter}\\n")
            resource.flush()

        def draw():
            assert active and not resource.closed
            pyxel.cls(counter)

        try:
            with resource:
                try:
                    pyxel.run(update, draw)
                    Path("after-run.txt").write_text("unexpected")
                finally:
                    active = False
                    counter = 999
                    pyxel.cls(9)
        finally:
            Path("released.txt").write_text(str(resource.closed))
        """,
    )
    result = structured(
        run(
            script=script,
            frames=3,
            until=until,
            snapshots=[
                {
                    "kind": "state",
                    "frame": "end",
                    "attrs": ["counter", "active", "resource.closed"],
                },
                {"kind": "screen_grid", "frame": "end", "bbox": [0, 0, 2, 2]},
            ],
        )
    )

    assert result["ok"] is True, result["errors"]
    assert result["exit_status"] == "ok"
    assert result["frame_count"] == completed
    assert result["until_met"] is (True if until else None)
    state, screen = result["snapshots"]
    assert state["frame"] == screen["frame"] == completed - 1
    assert state["values"] == {
        "counter": completed,
        "active": True,
        "resource.closed": False,
    }
    assert screen["grid"] == [[completed] * 2] * 2
    assert (tmp_path / "resource.txt").read_text().splitlines() == [
        str(i) for i in range(1, completed + 1)
    ]
    assert (tmp_path / "released.txt").read_text() == "True"
    assert not (tmp_path / "after-run.txt").exists()


@pytest.mark.parametrize("phase", ["update", "draw"])
@pytest.mark.parametrize("completed", [0, 2])
def test_quit_preserves_only_completed_frames_and_their_end_snapshots(
    tmp_path, phase, completed
):
    script = _script(
        tmp_path,
        f"""
        from pathlib import Path
        import pyxel

        pyxel.init(8, 8)
        counter = 0
        value = 0
        history = []

        def stop():
            global value
            value = 999
            history.append(999)
            pyxel.cls(9)
            pyxel.quit()
            Path("after-quit.txt").write_text("unexpected")

        def update():
            global counter, value
            counter += 1
            value = counter
            history.append(counter)
            if {phase!r} == "update" and counter == {completed + 1}:
                stop()

        def draw():
            global value
            value = counter * 10
            pyxel.cls(counter)
            if {phase!r} == "draw" and counter == {completed + 1}:
                stop()

        try:
            pyxel.run(update, draw)
            Path("after-run.txt").write_text("unexpected")
        finally:
            Path("cleanup.txt").write_text("complete")
        """,
    )
    end_image = tmp_path / "end.png"
    video_path = tmp_path / "partial.gif"
    result = structured(
        run(
            script=script,
            frames=6,
            until="counter >= 3",
            snapshots=[
                {"kind": "state", "frames": "all", "attrs": ["counter"]},
                {
                    "kind": "state",
                    "frame": "end",
                    "attrs": ["counter", "value", "history"],
                },
                {"kind": "screen_grid", "frame": "end", "bbox": [0, 0, 2, 2]},
                {
                    "kind": "screen_image",
                    "frames": "all",
                    "output_pattern": str(tmp_path / "frame-{frame}.png"),
                },
                {"kind": "screen_image", "frame": "end", "output": str(end_image)},
                {
                    "kind": "video",
                    "start_frame": 0,
                    "end_frame": 6,
                    "output": str(video_path),
                },
            ],
        )
    )

    assert result["ok"] is True, result["errors"]
    assert result["exit_status"] == "ok"
    assert result["frame_count"] == completed
    assert result["until_met"] is (False if completed else None)
    assert "quit" in result["log"].lower()
    assert (tmp_path / "cleanup.txt").read_text() == "complete"
    assert not (tmp_path / "after-quit.txt").exists()
    assert not (tmp_path / "after-run.txt").exists()

    if not completed:
        assert result["snapshots"] == []
        assert not end_image.exists()
        assert not video_path.exists()
        assert not list(tmp_path.glob("frame-*.png"))
        return

    states = [s for s in result["snapshots"] if s["kind"] == "state"]
    regular = [s for s in states if set(s["values"]) == {"counter"}]
    assert [s["frame"] for s in regular] == list(range(completed))
    assert [s["values"]["counter"] for s in regular] == list(range(1, completed + 1))
    end_state = next(s for s in states if "history" in s["values"])
    assert end_state["frame"] == completed - 1
    assert end_state["values"] == {
        "counter": completed,
        "value": completed * 10,
        "history": list(range(1, completed + 1)),
    }
    grid = next(s for s in result["snapshots"] if s["kind"] == "screen_grid")
    assert grid["frame"] == completed - 1
    assert grid["grid"] == [[completed] * 2] * 2
    images = [s for s in result["snapshots"] if s["kind"] == "screen_image"]
    assert len(images) == completed + 1
    assert all(s["frame"] < completed for s in images)
    with (
        Image.open(end_image) as end,
        Image.open(tmp_path / f"frame-{completed - 1:05d}.png") as previous,
    ):
        assert end.convert("RGB").tobytes() == previous.convert("RGB").tobytes()
    video = next(s for s in result["snapshots"] if s["kind"] == "video")
    assert video["frames_encoded"] == completed
    with Image.open(video_path) as image:
        assert image.n_frames == completed


@pytest.mark.parametrize("initialize", [False, True])
def test_quit_during_import_before_run_is_a_normal_empty_observation(
    tmp_path, initialize
):
    setup = "pyxel.init(8, 8)" if initialize else ""
    script = _script(
        tmp_path,
        f"""
        from pathlib import Path
        import pyxel
        {setup}
        pyxel.quit()
        Path("after-quit.txt").write_text("unexpected")
        """,
    )
    end_image = tmp_path / "end.png"
    result = structured(
        run(
            script=script,
            frames=3,
            until="counter > 0",
            snapshots=[
                {"kind": "state", "frame": "end"},
                {"kind": "screen_image", "frame": "end", "output": str(end_image)},
            ],
        )
    )

    assert result["ok"] is True, result["errors"]
    assert result["exit_status"] == "ok"
    assert result["frame_count"] == 0
    assert result["snapshots"] == []
    assert result["until_met"] is None
    assert "quit" in result["log"].lower()
    assert not end_image.exists()
    assert not (tmp_path / "after-quit.txt").exists()


@pytest.mark.parametrize("stop_with_quit", [False, True])
def test_cleanup_failure_preserves_observations_and_reports_script_exit(
    tmp_path, stop_with_quit
):
    script = _script(
        tmp_path,
        f"""
        import pyxel
        pyxel.init(8, 8)
        counter = 0

        def update():
            global counter
            counter += 1
            if {stop_with_quit!r} and counter == 3:
                pyxel.quit()

        try:
            pyxel.run(update, lambda: pyxel.cls(counter))
        finally:
            counter = 999
            pyxel.cls(9)
            raise RuntimeError("cleanup exploded")
        """,
    )
    result = structured(
        run(
            script=script,
            frames=6 if stop_with_quit else 2,
            until="counter >= 100",
            snapshots=[
                {"kind": "state", "frame": "end", "attrs": ["counter"]},
                {"kind": "screen_grid", "frame": "end", "bbox": [0, 0, 1, 1]},
            ],
        )
    )

    assert result["ok"] is False
    assert result["exit_status"] == "crashed"
    assert result["frame_count"] == 2
    assert result["until_met"] is False
    assert any(
        error["phase"] == "script_exit" and "cleanup exploded" in error["message"]
        for error in result["errors"]
    )
    state, screen = result["snapshots"]
    assert state["frame"] == screen["frame"] == 1
    assert state["values"] == {"counter": 2}
    assert screen["grid"] == [[2]]


def test_quit_before_run_cannot_start_a_loop_from_finally(tmp_path):
    script = _script(
        tmp_path,
        """
        from pathlib import Path
        import pyxel

        pyxel.init(8, 8)
        counter = 0

        def update():
            global counter
            counter += 1
            Path("unexpected-update.txt").write_text(str(counter))

        try:
            pyxel.quit()
        finally:
            pyxel.run(update, lambda: pyxel.cls(1))
        """,
    )
    end_image = tmp_path / "end.png"
    result = structured(
        run(
            script=script,
            frames=3,
            until="counter >= 1",
            snapshots=[
                {"kind": "state", "frame": "end", "attrs": ["counter"]},
                {"kind": "screen_image", "frame": "end", "output": str(end_image)},
            ],
        )
    )

    assert result["ok"] is True, result["errors"]
    assert result["exit_status"] == "ok"
    assert result["frame_count"] == 0
    assert result["until_met"] is None
    assert result["snapshots"] == []
    assert "quit" in result["log"].lower()
    assert not (tmp_path / "unexpected-update.txt").exists()
    assert not end_image.exists()


def test_sequential_run_calls_stop_after_the_first_observation(tmp_path):
    script = _script(
        tmp_path,
        """
        from pathlib import Path
        import pyxel
        pyxel.init(8, 8)
        counter = 0

        def update():
            global counter
            counter += 1

        pyxel.run(update, lambda: pyxel.cls(1))
        Path("second-run.txt").write_text("unexpected")
        pyxel.run(lambda: None, lambda: pyxel.cls(9))
        """,
    )
    result = structured(
        run(
            script=script,
            frames=2,
            snapshots=[{"kind": "state", "frame": "end", "attrs": ["counter"]}],
        )
    )

    assert result["ok"] is True, result["errors"]
    assert result["frame_count"] == 2
    assert result["snapshots"][0]["values"] == {"counter": 2}
    assert not (tmp_path / "second-run.txt").exists()


def test_quit_request_still_stops_when_a_callback_suppresses_the_signal(tmp_path):
    script = _script(
        tmp_path,
        """
        from contextlib import suppress
        from pathlib import Path
        import pyxel

        pyxel.init(8, 8)

        def update():
            with suppress(BaseException):
                pyxel.quit()

        def draw():
            Path("unexpected-draw.txt").write_text("unexpected")

        pyxel.run(update, draw)
        """,
    )

    result = structured(run(script=script, frames=3))

    assert result["ok"] is True, result["errors"]
    assert result["frame_count"] == 0
    assert "quit" in result["log"].lower()
    assert not (tmp_path / "unexpected-draw.txt").exists()


@pytest.mark.parametrize("phase", ["update", "draw"])
def test_recursive_run_reports_an_error_without_losing_completed_frames(
    tmp_path, phase
):
    script = _script(
        tmp_path,
        f"""
        import pyxel
        pyxel.init(8, 8)
        counter = 0

        def update():
            global counter
            counter += 1
            if {phase!r} == "update" and counter == 2:
                pyxel.run(lambda: None, lambda: None)

        def draw():
            pyxel.cls(counter)
            if {phase!r} == "draw" and counter == 2:
                pyxel.run(lambda: None, lambda: None)

        pyxel.run(update, draw)
        """,
    )
    result = structured(
        run(
            script=script,
            frames=3,
            snapshots=[
                {"kind": "state", "frames": "all", "attrs": ["counter"]},
                {"kind": "state", "frame": "end", "attrs": ["counter"]},
            ],
        )
    )

    assert result["ok"] is False
    assert result["exit_status"] == "crashed"
    assert result["frame_count"] == 1
    messages = " ".join(error["message"].lower() for error in result["errors"])
    assert "pyxel.run" in messages
    assert "recursive" in messages or "nested" in messages
    # A crashed run retains explicit captures and omits deferred end captures.
    assert len(result["snapshots"]) == 1
    assert result["snapshots"][0]["frame"] == 0
    assert result["snapshots"][0]["values"] == {"counter": 1}
