"""Tests for diff_frames tool (spec §9.1)."""
from tests.conftest import IMAGES


def compare_run(payload: dict) -> dict:
    from pyxel_mcp.observe._harnesses.tools.diff_frames import run
    return run(payload)


def test_identical_images():
    result = compare_run({
        "frame_a": str(IMAGES / "reference_a.png"),
        "frame_b": str(IMAGES / "reference_a.png"),
    })
    assert result["identical"] is True
    assert result["changed_pixels"] == 0
    assert result["region"] is None


def test_one_pixel_diff():
    result = compare_run({
        "frame_a": str(IMAGES / "reference_a.png"),
        "frame_b": str(IMAGES / "reference_b.png"),
    })
    assert result["identical"] is False
    assert result["changed_pixels"] == 1
    assert result["region"] == {"x": 10, "y": 10, "w": 1, "h": 1}


def test_size_mismatch_returns_nulls():
    """size_match=false → numeric fields all None."""
    result = compare_run({
        "frame_a": str(IMAGES / "reference_a.png"),
        "frame_b": str(IMAGES / "reference_c_16x16.png"),
    })
    assert result["size_match"] is False
    assert result["changed_pixels"] is None
    assert result["ratio"] is None


def test_missing_file_validation_error():
    result = compare_run({
        "frame_a": "/nonexistent/a.png",
        "frame_b": str(IMAGES / "reference_a.png"),
    })
    assert result["errors"][0]["phase"] == "validation"
