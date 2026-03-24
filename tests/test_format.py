"""Tests for _format module."""

from pyxel_mcp._format import (
    format_sprite_report,
    format_layout_report,
    format_state_report,
    format_state_timeline,
)


# --- format_sprite_report ---

_SPRITE_DATA = {
    "image": 0,
    "region": {"x": 0, "y": 0, "w": 4, "h": 2},
    "pixels": [[0, 1, 2, 3], [4, 5, 6, 7]],
    "symmetric_h": True,
    "symmetric_v": False,
    "color_count": {"0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "7": 1},
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
