"""Tests for _format module."""

from pyxel_mcp._common.format import (
    format_sprite_report,
    format_layout_report,
    format_state_report,
    format_state_timeline,
    format_animation_report,
    format_palette_report,
)


# --- format_sprite_report ---

_SPRITE_DATA = {
    "image": 0,
    "region": {"x": 0, "y": 0, "w": 4, "h": 2},
    "pixels": [[0, 1, 2, 3], [4, 5, 6, 7]],
    "symmetric_h": True,
    "symmetric_v": False,
    "color_count": {"0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "7": 1},
    "border_nonzero": 0,
    "border_total": 8,
    "fill_ratio": 0.875,
    "nonzero_pixels": 7,
    "edge_colors": [1, 3, 4, 7],
    "center_colors": [2, 5, 6],
}


def test_sprite_report_header():
    out = format_sprite_report(_SPRITE_DATA)
    assert "Sprite at image[0]" in out
    assert "4x2" in out


def test_sprite_report_pixel_grid():
    out = format_sprite_report(_SPRITE_DATA)
    assert "0123" in out
    assert "4567" in out


def test_sprite_report_symmetry():
    out = format_sprite_report(_SPRITE_DATA)
    assert "H-symmetry: yes" in out
    assert "V-symmetry: no" in out


def test_sprite_report_color_usage():
    out = format_sprite_report(_SPRITE_DATA)
    assert "Colors:" in out
    # color 0 = black
    assert "0(black)" in out
    # color 7 = white
    assert "7(white)" in out


def test_sprite_report_extended_colors():
    data = {
        "image": 1,
        "region": {"x": 0, "y": 0, "w": 2, "h": 1},
        "pixels": [[16, 255]],
        "symmetric_h": False,
        "symmetric_v": False,
        "color_count": {"16": 1, "255": 1},
    }
    out = format_sprite_report(data)
    # Extended colors use 2-digit hex with spaces
    assert "10 ff" in out


def test_sprite_report_no_suggestions_when_clean():
    """A sprite with no issues should have no suggestions section."""
    # 4x2 sprite with border all zero — clean outline, few colors
    data = {
        "image": 0,
        "region": {"x": 0, "y": 0, "w": 4, "h": 2},
        "pixels": [[0, 0, 0, 0], [0, 7, 7, 0]],
        "symmetric_h": True,
        "symmetric_v": False,
        "color_count": {"0": 6, "7": 2},
        "border_nonzero": 0,
        "border_total": 8,
        "fill_ratio": 0.25,
        "nonzero_pixels": 2,
        "edge_colors": [],
        "center_colors": [7, 7],
    }
    out = format_sprite_report(data)
    assert "Suggestions" not in out


def test_sprite_report_outline_suggestion():
    """Sprites with non-zero border pixels should get outline suggestion."""
    data = {
        "image": 0,
        "region": {"x": 0, "y": 0, "w": 4, "h": 2},
        "pixels": [[1, 2, 3, 4], [5, 6, 7, 8]],
        "symmetric_h": False,
        "symmetric_v": False,
        "color_count": {"1": 1, "2": 1, "3": 1, "4": 1,
                        "5": 1, "6": 1, "7": 1, "8": 1},
        "border_nonzero": 8,
        "border_total": 8,
        "fill_ratio": 1.0,
        "nonzero_pixels": 8,
        "edge_colors": [1, 4, 5, 8],
        "center_colors": [2, 3, 6, 7],
    }
    out = format_sprite_report(data)
    assert "Suggestions" in out
    assert "black outline" in out
    assert "border" in out


def test_sprite_report_too_many_colors_8x8():
    """8x8 sprite with > 4 non-zero colors should warn."""
    # 8x8 all filled with 5 different non-zero colors
    row = [1, 2, 3, 4, 5, 1, 2, 3]
    pixels = [row[:] for _ in range(8)]
    data = {
        "image": 0,
        "region": {"x": 0, "y": 0, "w": 8, "h": 8},
        "pixels": pixels,
        "symmetric_h": False,
        "symmetric_v": False,
        "color_count": {"1": 16, "2": 16, "3": 16, "4": 8, "5": 8},
        "border_nonzero": 28,
        "border_total": 28,
        "fill_ratio": 1.0,
        "nonzero_pixels": 64,
        "edge_colors": [1, 2, 3],
        "center_colors": [1, 2, 5],
    }
    out = format_sprite_report(data)
    assert "Suggestions" in out
    assert "Too many colors" in out
    assert "8x8" in out


def test_sprite_report_pillow_shading_warning():
    """Center much brighter than edges triggers pillow shading warning."""
    # color 7 (white, very bright) in center, color 1 (navy, dark) at edges
    data = {
        "image": 0,
        "region": {"x": 0, "y": 0, "w": 8, "h": 8},
        "pixels": [[1] * 8 for _ in range(8)],
        "symmetric_h": True,
        "symmetric_v": True,
        "color_count": {"1": 40, "7": 24},
        "border_nonzero": 28,
        "border_total": 28,
        "fill_ratio": 1.0,
        "nonzero_pixels": 64,
        "edge_colors": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # navy (dark)
        "center_colors": [7, 7, 7, 7, 7, 7, 7, 7, 7, 7],  # white (bright)
    }
    out = format_sprite_report(data)
    assert "Suggestions" in out
    assert "pillow shading" in out


def test_sprite_report_no_pillow_shading_when_correct():
    """Edges brighter than center should not trigger pillow shading warning."""
    data = {
        "image": 0,
        "region": {"x": 0, "y": 0, "w": 8, "h": 8},
        "pixels": [[1] * 8 for _ in range(8)],
        "symmetric_h": True,
        "symmetric_v": True,
        "color_count": {"1": 40, "7": 24},
        "border_nonzero": 0,
        "border_total": 28,
        "fill_ratio": 1.0,
        "nonzero_pixels": 64,
        "edge_colors": [7, 7, 7, 7, 7, 7, 7, 7, 7, 7],  # white (bright)
        "center_colors": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # navy (dark)
    }
    out = format_sprite_report(data)
    assert "pillow shading" not in out


def test_sprite_report_material_hint_skin():
    """Skin material colors (brown/peach/white) should be detected."""
    data = {
        "image": 0,
        "region": {"x": 0, "y": 0, "w": 8, "h": 8},
        "pixels": [[4, 15, 7, 0, 0, 7, 15, 4]] * 8,
        "symmetric_h": True,
        "symmetric_v": True,
        "color_count": {"0": 16, "4": 16, "7": 16, "15": 16},
        "border_nonzero": 0,
        "border_total": 28,
        "fill_ratio": 0.75,
        "nonzero_pixels": 48,
        "edge_colors": [4, 4, 4],
        "center_colors": [7, 15, 7],
    }
    out = format_sprite_report(data)
    assert "Suggestions" in out
    assert "skin" in out


def test_sprite_report_material_hint_metal():
    """Metal material colors (dark_blue/gray/white) should be detected."""
    data = {
        "image": 0,
        "region": {"x": 0, "y": 0, "w": 8, "h": 8},
        "pixels": [[5, 13, 7, 5, 5, 7, 13, 5]] * 8,
        "symmetric_h": True,
        "symmetric_v": True,
        "color_count": {"5": 24, "13": 16, "7": 24},
        "border_nonzero": 28,
        "border_total": 28,
        "fill_ratio": 1.0,
        "nonzero_pixels": 64,
        "edge_colors": [5, 5, 5],
        "center_colors": [13, 7, 13],
    }
    out = format_sprite_report(data)
    assert "metal" in out


def test_sprite_report_mostly_empty():
    """Sprites with fill_ratio < 0.2 should warn about empty space."""
    data = {
        "image": 0,
        "region": {"x": 0, "y": 0, "w": 16, "h": 16},
        "pixels": [[0] * 16 for _ in range(15)] + [[0, 7, 0] + [0] * 13],
        "symmetric_h": False,
        "symmetric_v": False,
        "color_count": {"0": 254, "7": 2},
        "border_nonzero": 0,
        "border_total": 60,
        "fill_ratio": 0.008,
        "nonzero_pixels": 2,
        "edge_colors": [],
        "center_colors": [],
    }
    out = format_sprite_report(data)
    assert "Suggestions" in out
    assert "mostly empty" in out


# --- format_layout_report ---

_LAYOUT_DATA = {
    "screen": {"w": 160, "h": 120},
    "bg_color": 0,
    "content_bbox": {"x": 20, "y": 10, "w": 120, "h": 100},
    "margins": {"top": 10, "bottom": 10, "left": 20, "right": 20},
    "fg_pixels": {"left": 500, "right": 500, "top": 400, "bottom": 400, "total": 1000},
    "h_balance": 1.0,
    "v_balance": 1.0,
    "center_of_mass": {"x": 80, "y": 60},
    "quadrants": {"tl": 250, "tr": 250, "bl": 250, "br": 250},
    "text_lines": [
        {"y": 10, "x": 60, "w": 40, "color": 7, "offset_from_center": 0},
    ],
    "font_height": 6,
    "grid_alignment": {
        8: {"x": True, "y": False, "w": True, "h": False, "score": 2},
        16: {"x": False, "y": False, "w": False, "h": False, "score": 0},
    },
}


def test_layout_report_screen_size():
    out = format_layout_report(_LAYOUT_DATA)
    assert "160x120" in out


def test_layout_report_bg_color_name():
    out = format_layout_report(_LAYOUT_DATA)
    assert "black" in out


def test_layout_report_margins():
    out = format_layout_report(_LAYOUT_DATA)
    assert "Margins:" in out
    assert "top=10" in out
    assert "left=20" in out


def test_layout_report_balance():
    out = format_layout_report(_LAYOUT_DATA)
    assert "H-balance:" in out
    assert "V-balance:" in out


def test_layout_report_text_lines():
    out = format_layout_report(_LAYOUT_DATA)
    assert "Text lines detected: 1" in out
    assert "white" in out
    assert "centered" in out


def test_layout_report_no_warnings_when_balanced():
    out = format_layout_report(_LAYOUT_DATA)
    assert "⚠" not in out


def test_layout_report_warning_on_imbalance():
    data = dict(_LAYOUT_DATA)
    data["h_balance"] = 0.3
    data["fg_pixels"] = {"left": 700, "right": 100, "top": 400, "bottom": 400, "total": 800}
    out = format_layout_report(data)
    assert "⚠" in out
    assert "imbalance" in out


def test_layout_report_margin_warning_vertical():
    data = dict(_LAYOUT_DATA)
    data["margins"] = {"top": 2, "bottom": 50, "left": 20, "right": 20}
    out = format_layout_report(data)
    assert "⚠" in out
    assert "Vertical margin imbalance" in out


def test_layout_report_margin_warning_horizontal():
    data = dict(_LAYOUT_DATA)
    data["margins"] = {"top": 10, "bottom": 10, "left": 2, "right": 60}
    out = format_layout_report(data)
    assert "⚠" in out
    assert "Horizontal margin imbalance" in out


def test_layout_report_text_alignment_warning():
    data = dict(_LAYOUT_DATA)
    data["text_lines"] = [
        {"y": 10, "x": 10, "w": 40, "color": 7, "offset_from_center": -30},
        {"y": 20, "x": 110, "w": 40, "color": 7, "offset_from_center": 30},
    ]
    out = format_layout_report(data)
    assert "Text alignment varies" in out


def test_layout_report_font_height():
    """Font height should appear in report when present."""
    out = format_layout_report(_LAYOUT_DATA)
    assert "Detected font height: 6px" in out


def test_layout_report_font_height_absent():
    """Report should not error when font_height key is missing."""
    data = dict(_LAYOUT_DATA)
    data.pop("font_height", None)
    out = format_layout_report(data)
    assert "font height" not in out


def test_layout_report_grid_alignment_shown():
    """Grid alignment scores should appear in report."""
    out = format_layout_report(_LAYOUT_DATA)
    assert "Grid alignment:" in out
    assert "8px:" in out
    assert "16px:" in out


def test_layout_report_grid_alignment_suggestion():
    """Low grid alignment score should generate a suggestion."""
    out = format_layout_report(_LAYOUT_DATA)
    # 16px score is 0 — should suggest alignment
    assert "=== Suggestions ===" in out
    assert "16px grid" in out


def test_layout_report_no_grid_alignment_absent():
    """Report should not error when grid_alignment key is missing."""
    data = dict(_LAYOUT_DATA)
    data.pop("grid_alignment", None)
    out = format_layout_report(data)
    assert "Grid alignment" not in out


# --- format_state_report ---

_STATE_DATA = {
    "frame": 60,
    "app_type": "MyGame",
    "attributes": {"score": 100, "lives": 3, "player_x": 80.0},
    "pyxel": {"frame_count": 60, "fps": 30},
}


def test_state_report_frame_number():
    out = format_state_report(_STATE_DATA)
    assert "State at frame 60" in out


def test_state_report_app_class():
    out = format_state_report(_STATE_DATA)
    assert "App class: MyGame" in out


def test_state_report_attributes():
    out = format_state_report(_STATE_DATA)
    assert "score" in out
    assert "100" in out
    assert "lives" in out
    assert "3" in out


def test_state_report_pyxel_system():
    out = format_state_report(_STATE_DATA)
    assert "Pyxel system:" in out
    assert "frame_count" in out


def test_state_report_no_app():
    data = {"frame": 30, "app_type": None, "note": "No class found", "attributes": {}}
    out = format_state_report(data)
    assert "No App instance found" in out
    assert "No class found" in out


def test_state_report_skips_type_key():
    data = {
        "frame": 1,
        "app_type": "App",
        "attributes": {"__type__": "App", "x": 5},
    }
    out = format_state_report(data)
    assert "__type__" not in out
    assert "x: 5" in out


# --- format_state_timeline ---

_SNAP_A = {
    "frame": 10,
    "app_type": "Game",
    "attributes": {"score": 0, "lives": 3},
    "pyxel": {},
}
_SNAP_B = {
    "frame": 30,
    "app_type": "Game",
    "attributes": {"score": 50, "lives": 3},
    "pyxel": {},
}
_SNAP_C = {
    "frame": 60,
    "app_type": "Game",
    "attributes": {"score": 50, "lives": 2},
    "pyxel": {},
}


def test_timeline_empty():
    assert format_state_timeline([]) == "No state captured"


def test_timeline_single_frame():
    out = format_state_timeline([_SNAP_A])
    assert "State at frame 10" in out
    # Should not show "timeline" header for single frame
    assert "timeline" not in out


def test_timeline_multi_frame_header():
    out = format_state_timeline([_SNAP_A, _SNAP_B, _SNAP_C])
    assert "State timeline (3 frames)" in out


def test_timeline_shows_first_frame():
    out = format_state_timeline([_SNAP_A, _SNAP_B])
    assert "State at frame 10" in out


def test_timeline_shows_diff():
    out = format_state_timeline([_SNAP_A, _SNAP_B])
    assert "Changes at frame 30" in out
    assert "score" in out
    assert "0" in out
    assert "50" in out


def test_timeline_no_changes():
    snap_same = dict(_SNAP_B, frame=45)
    out = format_state_timeline([_SNAP_B, snap_same])
    assert "(no changes)" in out


def test_timeline_skips_type_key():
    a = {"frame": 1, "app_type": "App", "attributes": {"__type__": "App", "x": 0}, "pyxel": {}}
    b = {"frame": 2, "app_type": "App", "attributes": {"__type__": "App", "x": 1}, "pyxel": {}}
    out = format_state_timeline([a, b])
    assert "__type__" not in out


# --- format_animation_report ---

def _make_frame(pixels):
    """Build a frame dict from a 2D pixel list."""
    color_count = {}
    for row in pixels:
        for c in row:
            color_count[c] = color_count.get(c, 0) + 1
    return {"offset_x": 0, "pixels": pixels, "color_count": color_count}


_ANIM_FRAME_A = _make_frame([[0, 1, 1, 0], [0, 2, 2, 0], [0, 1, 1, 0], [0, 0, 0, 0]])
_ANIM_FRAME_B = _make_frame([[0, 1, 1, 0], [0, 2, 2, 0], [0, 0, 0, 0], [0, 1, 1, 0]])
_ANIM_FRAME_C = _make_frame([[0, 3, 3, 0], [0, 3, 3, 0], [0, 1, 1, 0], [0, 0, 0, 0]])

_ANIM_DATA = {
    "image": 0,
    "region": {"x": 0, "y": 0, "w": 4, "h": 4},
    "frames": [_ANIM_FRAME_A, _ANIM_FRAME_B],
}


def test_animation_report_header():
    out = format_animation_report(_ANIM_DATA)
    assert "Animation: image[0]" in out
    assert "4x4" in out
    assert "x2 frames" in out


def test_animation_report_color_summary():
    out = format_animation_report(_ANIM_DATA)
    assert "Colors:" in out
    assert "shared across all frames" in out


def test_animation_report_per_frame_info():
    out = format_animation_report(_ANIM_DATA)
    assert "Frame 0:" in out
    assert "Frame 1:" in out
    assert "filled pixels" in out


def test_animation_report_frame_differences():
    out = format_animation_report(_ANIM_DATA)
    assert "Frame differences:" in out
    assert "Frame 0→1:" in out


def test_animation_report_no_frames():
    data = {"image": 0, "region": {"x": 0, "y": 0, "w": 8, "h": 8}, "frames": []}
    out = format_animation_report(data)
    assert "No animation frames found." in out


def test_animation_report_palette_drift_suggestion():
    """Frames with unique colors should trigger palette drift suggestion."""
    data = {
        "image": 0,
        "region": {"x": 0, "y": 0, "w": 4, "h": 4},
        "frames": [_ANIM_FRAME_A, _ANIM_FRAME_C],
    }
    out = format_animation_report(data)
    assert "Suggestions" in out
    assert "unique colors" in out


def test_animation_report_no_suggestions_when_consistent():
    """Identical frames should produce no suggestions."""
    data = {
        "image": 0,
        "region": {"x": 0, "y": 0, "w": 4, "h": 4},
        "frames": [_ANIM_FRAME_A, _ANIM_FRAME_A],
    }
    out = format_animation_report(data)
    assert "Suggestions" not in out


def test_animation_report_silhouette_size_suggestion():
    """Frames with very different fill counts should warn about silhouette size."""
    big = _make_frame([[1, 1, 1, 1]] * 4)   # 16 non-zero pixels
    tiny = _make_frame([[0, 0, 0, 0]] * 3 + [[0, 1, 0, 0]])  # 1 non-zero pixel
    data = {
        "image": 0,
        "region": {"x": 0, "y": 0, "w": 4, "h": 4},
        "frames": [big, tiny],
    }
    out = format_animation_report(data)
    assert "Suggestions" in out
    assert "size differs significantly" in out


def test_animation_report_three_frames():
    """Three-frame animation should show two difference lines."""
    data = {
        "image": 0,
        "region": {"x": 0, "y": 0, "w": 4, "h": 4},
        "frames": [_ANIM_FRAME_A, _ANIM_FRAME_B, _ANIM_FRAME_A],
    }
    out = format_animation_report(data)
    assert "Frame 0→1:" in out
    assert "Frame 1→2:" in out


# --- format_palette_report ---

def _make_snap(grid, frame=1):
    """Build a minimal snap dict from a 2D color grid."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    return {"frame": frame, "width": w, "height": h, "grid": grid}


# A simple 4x2 snap: color 0 dominates, color 7 appears twice
# color 0 (black) = background, color 7 (white) = foreground
_PALETTE_SNAP = _make_snap([[0, 0, 7, 0], [0, 0, 7, 0]])


def test_palette_report_header():
    """Header line should include frame number and screen dimensions."""
    out = format_palette_report(_PALETTE_SNAP)
    assert "Palette analysis at frame 1" in out
    assert "4x2" in out


def test_palette_report_background_detection():
    """Most common color should be identified as background."""
    out = format_palette_report(_PALETTE_SNAP)
    assert "Background:" in out
    assert "black" in out


def test_palette_report_color_count():
    """Color count line should reflect distinct colors present."""
    out = format_palette_report(_PALETTE_SNAP)
    assert "Colors used: 2" in out


def test_palette_report_color_distribution():
    """Color distribution block should list colors with pixel counts."""
    out = format_palette_report(_PALETTE_SNAP)
    assert "Color distribution:" in out
    # 0 (black) has 6 pixels, 7 (white) has 2 pixels
    assert "0 (black" in out
    assert "7 (white" in out


def test_palette_report_unused_colors():
    """Colors absent from the grid should appear in 'Unused colors'."""
    out = format_palette_report(_PALETTE_SNAP)
    assert "Unused colors:" in out
    # Color 1 (navy) is not in the 4x2 snap
    assert "1" in out


def test_palette_report_color_hierarchy_section():
    """Color hierarchy section should always be present."""
    out = format_palette_report(_PALETTE_SNAP)
    assert "Color hierarchy:" in out
    assert "background=" in out
    assert "environment=" in out
    assert "interactive=" in out
    assert "Hierarchy score:" in out


def test_palette_report_hierarchy_score_labels():
    """Score labels: 0→poor, 1→partial, 2→good."""
    # _PALETTE_SNAP has only black+white — no env or interactive colors
    out = format_palette_report(_PALETTE_SNAP)
    assert "0/2 (poor)" in out

    # Snap with env color (3=green) and interactive color (8=red) alongside bg
    good_snap = _make_snap([[0, 3, 8, 0], [0, 3, 8, 0]])
    out_good = format_palette_report(good_snap)
    assert "2/2 (good)" in out_good


def test_palette_report_foreground_color_roles():
    """Foreground colors should be listed with their role classification."""
    out = format_palette_report(_PALETTE_SNAP)
    assert "Foreground color roles:" in out
    # color 7 (white) is 'neutral'
    assert "neutral" in out


def test_palette_report_wcag_warning_on_low_contrast():
    """Colors with WCAG ratio < 3.0 against background should produce a warning."""
    # color 1 (navy) on color 0 (black) has very low contrast
    snap = _make_snap([[0, 0, 1, 0], [0, 0, 1, 0]])
    out = format_palette_report(snap)
    assert "Contrast warnings (WCAG AA):" in out
    assert "Low contrast:" in out
    assert "3.0+" in out


def test_palette_report_no_wcag_warning_on_high_contrast():
    """High-contrast color pair should not produce a WCAG warning."""
    # color 7 (white) on color 0 (black) has excellent contrast
    out = format_palette_report(_PALETTE_SNAP)
    assert "Contrast warnings" not in out


def test_palette_report_suggestion_low_contrast():
    """Low-contrast foreground should appear in suggestions."""
    snap = _make_snap([[0, 0, 1, 0], [0, 0, 1, 0]])
    out = format_palette_report(snap)
    assert "=== Suggestions ===" in out
    assert "Replace" in out
    assert "contrast" in out


def test_palette_report_suggestion_no_environment_colors():
    """Missing environment colors (3, 4, 13) should trigger a suggestion."""
    # Only black + white — no env colors
    out = format_palette_report(_PALETTE_SNAP)
    assert "=== Suggestions ===" in out
    assert "environment colors" in out


def test_palette_report_suggestion_no_interactive_colors():
    """Missing interactive colors (8, 10, 11) should trigger a suggestion."""
    out = format_palette_report(_PALETTE_SNAP)
    assert "interactive colors" in out


def test_palette_report_no_missing_suggestions_when_full_hierarchy():
    """Snap with env + interactive colors should not warn about missing layers."""
    # 0=bg, 3=env, 8=interactive, 7=neutral; enough colors to avoid <10 warning
    row = [0, 3, 8, 7, 10, 11, 4, 13, 6, 9, 2]
    snap = _make_snap([row, row])
    out = format_palette_report(snap)
    assert "No environment colors" not in out
    assert "No interactive colors" not in out


def test_palette_report_suggestion_few_colors():
    """Fewer than 10 distinct colors should suggest adding more."""
    out = format_palette_report(_PALETTE_SNAP)
    # Only 2 colors used → suggestion to use more
    assert "of 16 colors used" in out
    assert "10-14" in out


def test_palette_report_no_few_colors_suggestion_at_10():
    """Exactly 10 colors should not trigger the 'add more colors' suggestion."""
    # Build a snap with exactly 10 distinct colors (0-9)
    row = list(range(10))
    snap = _make_snap([row, row])
    out = format_palette_report(snap)
    assert "of 16 colors used" not in out


def test_palette_report_user_output_prepended():
    """user_output string should appear before the analysis."""
    out = format_palette_report(_PALETTE_SNAP, user_output="hello world")
    assert out.startswith("Script output:\nhello world")
    assert "Palette analysis" in out


def test_palette_report_stderr_appended():
    """stderr_text should be appended after the analysis."""
    out = format_palette_report(_PALETTE_SNAP, stderr_text="some warning")
    assert out.endswith("stderr: some warning")


def test_palette_report_no_user_output_by_default():
    """Without user_output, the report starts with 'Palette analysis'."""
    out = format_palette_report(_PALETTE_SNAP)
    assert out.startswith("Palette analysis")
