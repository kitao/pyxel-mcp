"""Tests for _palette module."""

import pytest
from pyxel_mcp._common.palette import (
    PALETTE,
    analyze_hierarchy,
    classify_color,
    color_contrast,
    color_name,
    color_rgb,
    luminance,
    relative_luminance,
    wcag_contrast,
)

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


# --- WCAG relative luminance ---

def test_relative_luminance_black():
    assert relative_luminance(0) == 0.0


def test_relative_luminance_white():
    lum = relative_luminance(7)  # white: (238, 238, 238) — not pure 255,255,255
    assert lum > 0.8  # high luminance, but not exactly 1.0


# --- WCAG contrast ratio ---

def test_wcag_contrast_black_white():
    # True white (255,255,255) vs black = 21.0; palette white is close
    ratio = wcag_contrast(0, 7)
    assert ratio > 15  # very high contrast


def test_wcag_contrast_same():
    ratio = wcag_contrast(5, 5)
    assert abs(ratio - 1.0) < 0.001


def test_wcag_contrast_symmetric():
    assert wcag_contrast(3, 8) == pytest.approx(wcag_contrast(8, 3))


# --- Color classification ---

def test_classify_color():
    assert classify_color(0) == "background"
    assert classify_color(1) == "background"
    assert classify_color(5) == "background"
    assert classify_color(3) == "environment"
    assert classify_color(4) == "environment"
    assert classify_color(13) == "environment"
    assert classify_color(8) == "interactive"
    assert classify_color(10) == "interactive"
    assert classify_color(11) == "interactive"
    assert classify_color(7) == "neutral"
    assert classify_color(2) == "neutral"
    assert classify_color(6) == "neutral"


# --- Hierarchy analysis ---

def test_analyze_hierarchy_full():
    # Good palette: env + interactive colors present
    used = {0, 3, 8, 7}  # black(bg), green(env), red(interactive), white(neutral)
    result = analyze_hierarchy(used, bg_color=0)
    assert result["has_environment"] is True
    assert result["has_interactive"] is True
    assert result["score"] == 2
    assert result["layers"]["environment"] == 1
    assert result["layers"]["interactive"] == 1
    assert result["layers"]["neutral"] == 1


def test_analyze_hierarchy_no_env():
    used = {0, 8, 7}  # bg + interactive + neutral, no environment
    result = analyze_hierarchy(used, bg_color=0)
    assert result["has_environment"] is False
    assert result["has_interactive"] is True
    assert result["score"] == 1


def test_analyze_hierarchy_no_interactive():
    used = {0, 3, 7}  # bg + environment + neutral, no interactive
    result = analyze_hierarchy(used, bg_color=0)
    assert result["has_environment"] is True
    assert result["has_interactive"] is False
    assert result["score"] == 1


def test_analyze_hierarchy_minimal():
    used = {0}  # only background color used
    result = analyze_hierarchy(used, bg_color=0)
    assert result["fg_count"] == 0
    assert result["score"] == 0


def test_analyze_hierarchy_excludes_bg():
    # bg_color itself should not count as foreground
    used = {1, 3}  # navy(bg), green(env)
    result = analyze_hierarchy(used, bg_color=1)
    assert result["fg_count"] == 1
    assert result["layers"]["background"] == 0  # navy excluded as it is bg
    assert result["layers"]["environment"] == 1
