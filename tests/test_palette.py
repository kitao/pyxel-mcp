"""Tests for _palette module."""

from pyxel_mcp._palette import color_name, color_rgb, color_contrast, luminance, PALETTE

def test_palette_has_16_entries():
    assert len(PALETTE) == 16

def test_color_name_known():
    assert color_name(0) == "black"
    assert color_name(7) == "white"
    assert color_name(8) == "red"

def test_color_name_unknown():
    assert color_name(99) == "?"

def test_color_rgb_known():
    assert color_rgb(0) == (0, 0, 0)
    assert color_rgb(7) == (238, 238, 238)

def test_color_rgb_unknown():
    assert color_rgb(99) == (0, 0, 0)

def test_luminance_black():
    assert luminance(0) == 0.0

def test_luminance_white_high():
    assert luminance(7) > 200

def test_contrast_same_color():
    ratio = color_contrast(5, 5)
    assert ratio < 1.1

def test_contrast_black_white():
    ratio = color_contrast(0, 7)
    assert ratio > 10

def test_contrast_symmetric():
    assert color_contrast(3, 8) == color_contrast(8, 3)
