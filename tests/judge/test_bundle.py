"""Tests for judge_bundle (Pattern G).

Verify the deliverable bundle dir contains required GIFs, enough PNG
frames, audio files per manifest, and that mid-bundle frames are not
identical (a dead-time check).
"""
from __future__ import annotations
import wave
from pathlib import Path

from PIL import Image

from pyxel_mcp.judge._impl.bundle import DEFAULT_CONTRACT, judge_bundle


def _make_gif(path: Path, color: tuple[int, int, int] = (255, 0, 0)) -> None:
    Image.new("RGB", (16, 16), color).save(path, format="GIF")


def _make_png(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (16, 16), color).save(path, format="PNG")


def _make_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b"\x00\x10" * 1000)  # tiny non-empty WAV


def _build_bundle(root: Path, *, frames: int = 5, frame_color_step: bool = True,
                  with_videos: bool = True, with_audio: list[str] | None = None) -> Path:
    bundle = root / "bundle"
    bundle.mkdir()

    if with_videos:
        _make_gif(bundle / "win-path.gif", (0, 255, 0))
        _make_gif(bundle / "lose-path.gif", (255, 0, 0))

    frames_dir = bundle / "frames"
    frames_dir.mkdir()
    for i in range(frames):
        # Step the color so consecutive frames differ — passes dead-time check.
        c = (i * 30 % 255, i * 50 % 255, i * 70 % 255) if frame_color_step else (10, 20, 30)
        _make_png(frames_dir / f"frame_{i:03d}.png", c)

    if with_audio:
        audio_dir = bundle / "audio"
        audio_dir.mkdir()
        for name in with_audio:
            _make_wav(audio_dir / name)

    return bundle


def test_pass_complete_bundle(tmp_path):
    bundle = _build_bundle(tmp_path, with_audio=["bgm.wav", "jump.wav"])
    contract = {
        "required_videos": ["win-path.gif", "lose-path.gif"],
        "min_frames": 5,
        "min_dead_time_diff": 0.05,
        "audio_manifest": [
            {"name": "bgm.wav", "type": "music"},
            {"name": "jump.wav", "type": "sound"},
        ],
    }
    result = judge_bundle({"bundle_dir": str(bundle)}, contract)
    assert result["verdict"] == "pass", result
    assert result["ok"] is True


def test_fail_missing_video(tmp_path):
    bundle = _build_bundle(tmp_path, with_audio=["bgm.wav"])
    (bundle / "win-path.gif").unlink()
    result = judge_bundle({"bundle_dir": str(bundle)}, {
        "required_videos": ["win-path.gif", "lose-path.gif"],
        "min_frames": 5, "min_dead_time_diff": 0.05,
        "audio_manifest": [{"name": "bgm.wav", "type": "music"}],
    })
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "bundle"
    assert "win-path.gif" in result["evidence"]


def test_fail_too_few_frames(tmp_path):
    bundle = _build_bundle(tmp_path, frames=2, with_audio=["bgm.wav"])
    result = judge_bundle({"bundle_dir": str(bundle)}, {
        "required_videos": ["win-path.gif", "lose-path.gif"],
        "min_frames": 5, "min_dead_time_diff": 0.05,
        "audio_manifest": [{"name": "bgm.wav", "type": "music"}],
    })
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "bundle"


def test_fail_missing_audio(tmp_path):
    bundle = _build_bundle(tmp_path, with_audio=["bgm.wav"])
    result = judge_bundle({"bundle_dir": str(bundle)}, {
        "required_videos": ["win-path.gif", "lose-path.gif"],
        "min_frames": 5, "min_dead_time_diff": 0.05,
        "audio_manifest": [
            {"name": "bgm.wav", "type": "music"},
            {"name": "missing.wav", "type": "sound"},
        ],
    })
    assert result["verdict"] == "fail"
    assert "missing.wav" in result["evidence"]


def test_fail_dead_time(tmp_path):
    """All frames identical -> dead-time diff is zero -> fail."""
    bundle = _build_bundle(tmp_path, frames=5, frame_color_step=False,
                           with_audio=["bgm.wav"])
    result = judge_bundle({"bundle_dir": str(bundle)}, {
        "required_videos": ["win-path.gif", "lose-path.gif"],
        "min_frames": 5, "min_dead_time_diff": 0.05,
        "audio_manifest": [{"name": "bgm.wav", "type": "music"}],
    })
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "bundle"
    assert "dead" in result["evidence"].lower() or "diff" in result["evidence"].lower()


def test_fail_bundle_dir_missing(tmp_path):
    result = judge_bundle({"bundle_dir": str(tmp_path / "nonexistent")},
                          {"required_videos": [], "min_frames": 0,
                           "min_dead_time_diff": 0.0, "audio_manifest": []})
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "bundle"


def test_default_contract_constants():
    assert DEFAULT_CONTRACT["required_videos"] == ["win-path.gif", "lose-path.gif"]
    assert DEFAULT_CONTRACT["min_frames"] == 5
    assert DEFAULT_CONTRACT["min_dead_time_diff"] == 0.05


def test_pass_when_only_one_pair_among_many_shows_motion(tmp_path):
    """Sparse-content game whose canonical frames mostly look alike (same
    bg + wall) but at least one pair (e.g. mid_game vs title) differs
    meaningfully. Pre-P0-2 this failed because only the alphabetical
    first-vs-mid pair was checked."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    _make_gif(bundle / "win-path.gif", (0, 255, 0))
    _make_gif(bundle / "lose-path.gif", (255, 0, 0))
    frames_dir = bundle / "frames"
    frames_dir.mkdir()
    # Canonical names landing in alphabetical order:
    # game_over.png, mid_game.png, play_start.png, title.png, win.png
    base = (10, 20, 30)
    _make_png(frames_dir / "game_over.png", base)
    _make_png(frames_dir / "mid_game.png", base)
    _make_png(frames_dir / "play_start.png", base)   # all identical so far
    _make_png(frames_dir / "title.png", (200, 50, 30))  # only this differs
    _make_png(frames_dir / "win.png", base)

    audio_dir = bundle / "audio"
    audio_dir.mkdir()
    _make_wav(audio_dir / "bgm.wav")

    result = judge_bundle({"bundle_dir": str(bundle)}, {
        "required_videos": ["win-path.gif", "lose-path.gif"],
        "min_frames": 5, "min_dead_time_diff": 0.05,
        "audio_manifest": [{"name": "bgm.wav", "type": "music"}],
    })
    assert result["verdict"] == "pass", result["evidence"]
    # The max pair should be (something, title.png) or (title.png, something)
    max_pair = result["details"]["dead_time_debug"]["max_pair"]
    assert any("title" in p for p in max_pair)


def test_fail_when_every_pair_is_below_threshold(tmp_path):
    """Five identical frames — no pair shows movement. Bundle fails."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    _make_gif(bundle / "win-path.gif", (0, 255, 0))
    _make_gif(bundle / "lose-path.gif", (255, 0, 0))
    frames_dir = bundle / "frames"
    frames_dir.mkdir()
    base = (10, 20, 30)
    for name in ("game_over", "mid_game", "play_start", "title", "win"):
        _make_png(frames_dir / f"{name}.png", base)

    audio_dir = bundle / "audio"
    audio_dir.mkdir()
    _make_wav(audio_dir / "bgm.wav")

    result = judge_bundle({"bundle_dir": str(bundle)}, {
        "required_videos": ["win-path.gif", "lose-path.gif"],
        "min_frames": 5, "min_dead_time_diff": 0.05,
        "audio_manifest": [{"name": "bgm.wav", "type": "music"}],
    })
    assert result["verdict"] == "fail"
    assert result["details"]["dead_time_debug"]["max_ratio"] == 0.0


def test_dead_time_records_size_mismatches_in_debug(tmp_path):
    """Frames captured at inconsistent scales surface as size_mismatches
    in debug — capture.md requires uniform scale, this is the diagnostic."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    _make_gif(bundle / "win-path.gif", (0, 255, 0))
    _make_gif(bundle / "lose-path.gif", (255, 0, 0))
    frames_dir = bundle / "frames"
    frames_dir.mkdir()
    # Mismatched sizes
    Image.new("RGB", (16, 16), (10, 20, 30)).save(frames_dir / "title.png")
    Image.new("RGB", (32, 32), (10, 20, 30)).save(frames_dir / "play_start.png")
    Image.new("RGB", (32, 32), (200, 200, 200)).save(frames_dir / "mid_game.png")
    Image.new("RGB", (32, 32), (10, 20, 30)).save(frames_dir / "win.png")
    Image.new("RGB", (32, 32), (10, 20, 30)).save(frames_dir / "game_over.png")

    audio_dir = bundle / "audio"
    audio_dir.mkdir()
    _make_wav(audio_dir / "bgm.wav")

    result = judge_bundle({"bundle_dir": str(bundle)}, {
        "required_videos": ["win-path.gif", "lose-path.gif"],
        "min_frames": 5, "min_dead_time_diff": 0.05,
        "audio_manifest": [{"name": "bgm.wav", "type": "music"}],
    })
    mismatches = result["details"]["dead_time_debug"]["size_mismatches"]
    assert mismatches, "expected size_mismatches list to record the mixed-scale pairs"
    # title.png is the odd one out (16x16 vs the rest 32x32) — should
    # appear in every recorded mismatch.
    assert all("title" in pair[0] or "title" in pair[1] for pair in mismatches)
