"""Tests for read_animation tool (spec §7.3)."""
import pytest

from pyxel_mcp.observe._harnesses.tools.read_animation import run as read_animation_run
from tests.conftest import SCRIPTS


def test_missing_region_count_validation():
    """Omitting region_count returns a validation phase error."""
    result = read_animation_run({
        "script": str(SCRIPTS / "palette_default.py"),
        "image": 0,
        "x": 0, "y": 0, "w": 8, "h": 8,
        # region_count omitted
    })
    assert result["errors"][0]["phase"] == "validation"
    assert result["image_index"] == -1


def test_region_count_below_2_validation():
    """region_count=1 fails validation."""
    result = read_animation_run({
        "script": str(SCRIPTS / "palette_default.py"),
        "image": 0,
        "x": 0, "y": 0, "w": 8, "h": 8,
        "region_count": 1,
    })
    assert result["errors"][0]["phase"] == "validation"


def test_overflow_returns_validation_error():
    """Region strip extending beyond bank bounds returns a validation phase error."""
    result = read_animation_run({
        "script": str(SCRIPTS / "palette_default.py"),
        "image": 0,
        "x": 250, "y": 0, "w": 8, "h": 8,
        "region_count": 4,
        "direction": "horizontal",
    })
    assert result["errors"][0]["phase"] == "validation"
    assert result["image_index"] == -1


def test_round_trip_horizontal():
    """Valid horizontal strip returns correct structure with no errors."""
    result = read_animation_run({
        "script": str(SCRIPTS / "palette_default.py"),
        "image": 0,
        "x": 0, "y": 0, "w": 8, "h": 8,
        "region_count": 3,
        "direction": "horizontal",
    })
    assert result["errors"] == []
    assert result["image_index"] == 0
    assert len(result["regions"]) == 3
    assert len(result["region_diffs"]) == 2
    assert 0.0 <= result["palette_consistency"] <= 1.0
    assert 0.0 <= result["silhouette_stability"] <= 1.0
    # Confirm horizontal layout
    assert result["regions"][0]["region"]["x"] == 0
    assert result["regions"][1]["region"]["x"] == 8
    assert result["regions"][2]["region"]["x"] == 16


def test_invalid_bank_index_validation():
    """image=99 is out of range — errors[0].phase == 'validation'."""
    result = read_animation_run({
        "script": str(SCRIPTS / "palette_default.py"),
        "image": 99,
        "x": 0, "y": 0, "w": 8, "h": 8,
        "region_count": 2,
    })
    assert result["errors"][0]["phase"] == "validation"
    assert result["image_index"] == -1
