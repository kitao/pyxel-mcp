import shutil
from pathlib import Path

import pytest
from PIL import Image

from pyxel_mcp.observe._harnesses._common.snapshot_kinds.video import (
    ExtensionError,
    VideoAccumulator,
)


def _dummy_frames(n: int, size: tuple[int, int] = (16, 16)) -> list[Image.Image]:
    return [Image.new("RGB", size, (i * 8 % 256, 0, 0)) for i in range(n)]


def test_gif_output(tmp_path):
    out = tmp_path / "anim.gif"
    accum = VideoAccumulator(
        {
            "kind": "video",
            "start_frame": 0,
            "end_frame": 5,
            "fps": 30,
            "output": str(out),
            "scale": 1,
        }
    )
    for i, img in enumerate(_dummy_frames(5)):
        accum.add_frame(i, img)
    result = accum.encode()
    assert out.exists()
    assert result["format"] == "gif"
    assert result["frames_encoded"] == 5
    assert result["duration_seconds"] == pytest.approx(5 / 30, abs=0.005)


@pytest.mark.parametrize("fps", [30, 60, 120])
def test_gif_duration_matches_the_encoded_frames(tmp_path, fps):
    out = tmp_path / "timing.gif"
    accum = VideoAccumulator(
        {"start_frame": 0, "end_frame": 60, "fps": fps, "output": str(out)}
    )
    for i, frame in enumerate(_dummy_frames(60)):
        accum.add_frame(i, frame)
    result = accum.encode()
    with Image.open(out) as image:
        durations = []
        for i in range(image.n_frames):
            image.seek(i)
            durations.append(image.info["duration"])
    assert all(duration >= 10 for duration in durations)
    assert result["duration_seconds"] == sum(durations) / 1000
    assert result["duration_seconds"] == pytest.approx(60 / min(fps, 100), abs=0.005)
    if fps > 100:
        assert any("100 fps" in warning for warning in result["warnings"])


def test_invalid_extension_raises(tmp_path):
    with pytest.raises(ExtensionError):
        VideoAccumulator(
            {
                "kind": "video",
                "start_frame": 0,
                "end_frame": 5,
                "fps": 30,
                "output": str(tmp_path / "anim.webm"),
                "scale": 1,
            }
        )


def test_encode_failure_cleans_temporary_directory(tmp_path, monkeypatch):
    out = tmp_path / "anim.gif"
    accum = VideoAccumulator(
        {
            "kind": "video",
            "start_frame": 0,
            "end_frame": 1,
            "fps": 30,
            "output": str(out),
            "scale": 1,
        }
    )
    accum.add_frame(0, _dummy_frames(1)[0])
    tempdir = Path(accum._tempdir)

    def fail_save(*_args, **_kwargs):
        raise OSError("save failed")

    monkeypatch.setattr(Image.Image, "save", fail_save)

    with pytest.raises(OSError, match="save failed"):
        accum.encode()

    assert not tempdir.exists()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")
def test_mp4_output(tmp_path):
    out = tmp_path / "anim.mp4"
    accum = VideoAccumulator(
        {
            "kind": "video",
            "start_frame": 0,
            "end_frame": 5,
            "fps": 30,
            "output": str(out),
            "scale": 1,
        }
    )
    for i, img in enumerate(_dummy_frames(5)):
        accum.add_frame(i, img)
    result = accum.encode()
    assert out.exists()
    assert result["format"] == "mp4"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")
def test_mp4_accepts_odd_screen_dimensions(tmp_path):
    out = tmp_path / "odd.mp4"
    accum = VideoAccumulator(
        {"start_frame": 0, "end_frame": 3, "fps": 30, "output": str(out)}
    )
    for i, frame in enumerate(_dummy_frames(3, size=(9, 13))):
        accum.add_frame(i, frame)
    result = accum.encode()
    assert out.stat().st_size > 0
    assert result["frames_encoded"] == 3
    assert any("padded" in warning for warning in result["warnings"])


def test_mp4_falls_back_to_gif_when_ffmpeg_missing(tmp_path, monkeypatch):
    """If ffmpeg isn't available, output is rewritten to .gif and warned."""
    import pyxel_mcp.observe._harnesses._common.snapshot_kinds.video as vid_mod

    monkeypatch.setattr(vid_mod, "_ffmpeg_available", lambda: False)
    out = tmp_path / "anim.mp4"
    accum = VideoAccumulator(
        {
            "kind": "video",
            "start_frame": 0,
            "end_frame": 5,
            "fps": 30,
            "output": str(out),
            "scale": 1,
        }
    )
    for i, img in enumerate(_dummy_frames(5)):
        accum.add_frame(i, img)
    result = accum.encode()
    assert result["format"] == "gif"
    assert result["path"].endswith(".gif")
    assert any("ffmpeg" in w.lower() for w in result["warnings"])


def test_truncation_when_fewer_frames_added(tmp_path):
    """If only 3 of 5 expected frames were added (run crashed mid-range),
    frames_encoded should reflect 3."""
    out = tmp_path / "anim.gif"
    accum = VideoAccumulator(
        {
            "kind": "video",
            "start_frame": 0,
            "end_frame": 5,
            "fps": 30,
            "output": str(out),
            "scale": 1,
        }
    )
    for i, img in enumerate(_dummy_frames(3)):
        accum.add_frame(i, img)
    result = accum.encode()
    assert result["frames_encoded"] == 3


@pytest.mark.parametrize("extension", ["gif", "mp4"])
def test_run_until_before_video_range_skips_artifact(tmp_path, extension):
    from pyxel_mcp import server
    from tests.conftest import SCRIPTS

    out = tmp_path / f"unreached.{extension}"
    result = server.run(
        script=str(SCRIPTS / "stateful_app.py"),
        frames=20,
        until="counter >= 2",
        snapshots=[
            {
                "kind": "video",
                "start_frame": 10,
                "end_frame": 20,
                "output": str(out),
            }
        ],
    ).structured_content
    assert result["ok"] is True
    assert result["exit_status"] == "ok"
    assert result["until_met"] is True
    assert result["snapshots"] == []
    assert "before any frames in its capture range" in result["log"]
    assert not out.exists()
