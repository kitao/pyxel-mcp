import shutil
import pytest
from pathlib import Path
from PIL import Image
from pyxel_mcp._harnesses._common.snapshot_kinds.video import (
    VideoAccumulator, ExtensionError
)


def _dummy_frames(n: int, size: tuple[int, int] = (16, 16)) -> list[Image.Image]:
    return [Image.new("RGB", size, (i * 8 % 256, 0, 0)) for i in range(n)]


def test_gif_output(tmp_path):
    out = tmp_path / "anim.gif"
    accum = VideoAccumulator({
        "kind": "video", "start_frame": 0, "end_frame": 5,
        "fps": 30, "output": str(out), "scale": 1,
    })
    for i, img in enumerate(_dummy_frames(5)):
        accum.add_frame(i, img)
    result = accum.encode()
    assert out.exists()
    assert result["format"] == "gif"
    assert result["frames_encoded"] == 5
    assert result["duration_seconds"] == pytest.approx(5 / 30)


def test_invalid_extension_raises(tmp_path):
    with pytest.raises(ExtensionError):
        VideoAccumulator({
            "kind": "video", "start_frame": 0, "end_frame": 5,
            "fps": 30, "output": str(tmp_path / "anim.webm"), "scale": 1,
        })


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")
def test_mp4_output(tmp_path):
    out = tmp_path / "anim.mp4"
    accum = VideoAccumulator({
        "kind": "video", "start_frame": 0, "end_frame": 5,
        "fps": 30, "output": str(out), "scale": 1,
    })
    for i, img in enumerate(_dummy_frames(5)):
        accum.add_frame(i, img)
    result = accum.encode()
    assert out.exists()
    assert result["format"] == "mp4"


def test_mp4_falls_back_to_gif_when_ffmpeg_missing(tmp_path, monkeypatch):
    """If ffmpeg isn't available, output is rewritten to .gif and warned."""
    import pyxel_mcp._harnesses._common.snapshot_kinds.video as vid_mod
    monkeypatch.setattr(vid_mod, "_ffmpeg_available", lambda: False)
    out = tmp_path / "anim.mp4"
    accum = VideoAccumulator({
        "kind": "video", "start_frame": 0, "end_frame": 5,
        "fps": 30, "output": str(out), "scale": 1,
    })
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
    accum = VideoAccumulator({
        "kind": "video", "start_frame": 0, "end_frame": 5,
        "fps": 30, "output": str(out), "scale": 1,
    })
    for i, img in enumerate(_dummy_frames(3)):
        accum.add_frame(i, img)
    result = accum.encode()
    assert result["frames_encoded"] == 3
