"""Layout analysis harness - analyzes screen composition and text alignment.

Runs a Pyxel script, captures at a specified frame, then reads all screen
pixels and analyzes layout balance, content centering, and text positioning.

Usage:
    python layout_harness.py <script> <frames>
"""

import json
import os
import sys

if len(sys.argv) < 3:
    print("Usage: layout_harness <script> <frames>", file=sys.stderr)
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
target_frames = int(sys.argv[2])

import pyxel

from pyxel_mcp._headless import patch_game_loop, run_script, setup_harness

setup_harness(script_path)

# --- Pure analysis functions (testable without pyxel running) ---


def read_pixels(w, h):
    """Read all screen pixels as a 2D list of color indices."""
    pixels = []
    for y in range(h):
        row = [pyxel.pget(x, y) for x in range(w)]
        pixels.append(row)
    return pixels


def find_bg_color(pixels):
    """Return the most frequent color in the pixel grid."""
    color_count = {}
    for row in pixels:
        for c in row:
            color_count[c] = color_count.get(c, 0) + 1
    return max(color_count, key=color_count.get)


def content_bbox(pixels, bg):
    """Return bounding box of non-bg pixels, or None if all background."""
    h = len(pixels)
    w = len(pixels[0]) if h > 0 else 0
    min_x, min_y = w, h
    max_x, max_y = -1, -1
    for y in range(h):
        for x in range(w):
            if pixels[y][x] != bg:
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y
    if max_x < 0:
        return None
    return {"x": min_x, "y": min_y, "w": max_x - min_x + 1, "h": max_y - min_y + 1}


def calc_balance(pixels, bg):
    """Compute horizontal/vertical balance, quadrant counts, and center of mass."""
    h = len(pixels)
    w = len(pixels[0]) if h > 0 else 0
    mid_x = w // 2
    mid_y = h // 2
    left = right = top = bottom = 0
    quadrants = {"tl": 0, "tr": 0, "bl": 0, "br": 0}
    sum_x = sum_y = 0
    for y in range(h):
        for x in range(w):
            if pixels[y][x] != bg:
                sum_x += x
                sum_y += y
                if x < mid_x:
                    left += 1
                else:
                    right += 1
                if y < mid_y:
                    top += 1
                else:
                    bottom += 1
                if x < mid_x and y < mid_y:
                    quadrants["tl"] += 1
                elif x >= mid_x and y < mid_y:
                    quadrants["tr"] += 1
                elif x < mid_x and y >= mid_y:
                    quadrants["bl"] += 1
                else:
                    quadrants["br"] += 1

    total = left + right
    h_balance = 0.0
    v_balance = 0.0
    center_of_mass = None
    if total > 0:
        h_balance = min(left, right) / max(left, right)
        v_balance = min(top, bottom) / max(top, bottom)
        center_of_mass = {"x": round(sum_x / total, 1), "y": round(sum_y / total, 1)}

    return {
        "h_balance": round(h_balance, 3),
        "v_balance": round(v_balance, 3),
        "fg_pixels": {
            "left": left, "right": right,
            "top": top, "bottom": bottom,
            "total": total,
        },
        "quadrants": quadrants,
        "center_of_mass": center_of_mass,
    }


def calc_margins(bbox, w, h):
    """Return margins from content bbox to screen edges."""
    return {
        "top": bbox["y"],
        "bottom": h - (bbox["y"] + bbox["h"]),
        "left": bbox["x"],
        "right": w - (bbox["x"] + bbox["w"]),
    }


def estimate_font_height(pixels, bg):
    """Estimate font height from vertical pixel continuity.

    Scans for rows where non-bg pixels form consistent vertical spans.
    Returns estimated font height (default 6 if undetermined).
    """
    h = len(pixels)
    if h == 0:
        return 6
    w = len(pixels[0])

    # Find rows with sparse non-bg content (likely text rows)
    span_heights = []
    y = 0
    while y < h:
        bg_in_row = sum(1 for x in range(w) if pixels[y][x] == bg)
        if bg_in_row < w * 0.5:
            y += 1
            continue
        # Check if this row starts a text span
        has_content = any(pixels[y][x] != bg for x in range(w))
        if not has_content:
            y += 1
            continue
        # Measure vertical extent of content at this row
        span_h = 1
        while y + span_h < h:
            next_has = any(pixels[y + span_h][x] != bg for x in range(w))
            next_bg = sum(1 for x in range(w) if pixels[y + span_h][x] == bg)
            if not next_has or next_bg < w * 0.5:
                break
            span_h += 1
        if 4 <= span_h <= 16:  # reasonable font height range
            span_heights.append(span_h)
        y += span_h + 1

    if not span_heights:
        return 6
    # Most common height
    from collections import Counter
    return Counter(span_heights).most_common(1)[0][0]


def check_grid_alignment(bbox, text_lines):
    """Check if content aligns to 8px or 16px grid.

    Returns alignment info dict, or None if no bbox.
    """
    if not bbox:
        return None

    checks = {}
    for grid in [8, 16]:
        x_aligned = bbox["x"] % grid == 0
        y_aligned = bbox["y"] % grid == 0
        w_aligned = bbox["w"] % grid == 0
        h_aligned = bbox["h"] % grid == 0
        checks[grid] = {
            "x": x_aligned, "y": y_aligned,
            "w": w_aligned, "h": h_aligned,
            "score": sum([x_aligned, y_aligned, w_aligned, h_aligned]),
        }
    return checks


def detect_text(pixels, bg):
    """Detect text-like horizontal spans in the pixel grid.

    Returns a list of span dicts with x, y, w, h, color, center_x.
    Uses Pyxel default font heuristics: 4px wide per char, 6px tall.
    """
    h = len(pixels)
    w = len(pixels[0]) if h > 0 else 0
    FONT_H = estimate_font_height(pixels, bg)
    MIN_TEXT_W = 10  # minimum ~3 characters
    text_spans = []

    y = 0
    while y < h - FONT_H + 1:
        # Only scan rows where most of the row is background
        bg_in_row = sum(1 for x in range(w) if pixels[y][x] == bg)
        if bg_in_row < w * 0.5:
            y += 1
            continue

        x = 0
        row_spans = []
        while x < w:
            c = pixels[y][x]
            if c == bg:
                x += 1
                continue

            # Scan right: same-color pixels with small bg gaps (char spacing)
            span_start = x
            span_color = c
            gap = 0
            while x < w:
                if pixels[y][x] == span_color:
                    gap = 0
                elif pixels[y][x] == bg:
                    gap += 1
                    if gap > 5:  # allow space char (4px) + 1
                        break
                else:
                    break
                x += 1
            span_end = x - gap
            span_w = span_end - span_start

            if span_w < MIN_TEXT_W:
                continue

            # Fill density: text ~25-65%, solid rects >80%
            total_area = span_w * FONT_H
            filled = 0
            for dy in range(FONT_H):
                if y + dy >= h:
                    break
                for sx in range(span_start, span_end):
                    if pixels[y + dy][sx] == span_color:
                        filled += 1
            fill_ratio = filled / total_area if total_area > 0 else 0

            if fill_ratio > 0.7 or fill_ratio < 0.08:
                continue

            # Verify text is isolated: rows above and below should be bg
            bg_above = span_w  # default if y==0
            if y > 0:
                bg_above = sum(
                    1 for sx in range(span_start, span_end)
                    if pixels[y - 1][sx] == bg
                )
            check_below = y + FONT_H
            bg_below = span_w  # default if at bottom
            if check_below < h:
                bg_below = sum(
                    1 for sx in range(span_start, span_end)
                    if pixels[check_below][sx] == bg
                )
            isolation = (bg_above + bg_below) / (2 * span_w)
            if isolation < 0.6:
                continue

            row_spans.append({
                "x": span_start,
                "y": y,
                "w": span_w,
                "h": FONT_H,
                "color": span_color,
                "center_x": span_start + span_w / 2,
            })

        text_spans.extend(row_spans)
        y += FONT_H if row_spans else 1

    return text_spans


def merge_text_spans(spans):
    """Merge overlapping text spans on the same Y into wider spans."""
    merged = []
    for span in spans:
        done = False
        for m in merged:
            if (abs(span["y"] - m["y"]) <= 1
                    and span["color"] == m["color"]
                    and span["x"] <= m["x"] + m["w"] + 2):
                new_x = min(m["x"], span["x"])
                new_end = max(m["x"] + m["w"], span["x"] + span["w"])
                m["x"] = new_x
                m["w"] = new_end - new_x
                m["center_x"] = new_x + (new_end - new_x) / 2
                done = True
                break
        if not done:
            merged.append(dict(span))
    return merged


def dedup_text_by_y(spans):
    """Keep only the widest span per Y position."""
    by_y = {}
    for span in spans:
        y_key = span["y"]
        if y_key not in by_y or span["w"] > by_y[y_key]["w"]:
            by_y[y_key] = span
    return sorted(by_y.values(), key=lambda s: s["y"])


def analyze_text_alignment(text_lines, screen_w):
    """Compute centering offset for each text line relative to screen center."""
    screen_center = screen_w / 2
    result = []
    for tl in text_lines:
        cx = tl["center_x"]
        offset = cx - screen_center
        result.append({
            "y": tl["y"],
            "x": tl["x"],
            "w": tl["w"],
            "color": tl["color"],
            "center_x": round(cx, 1),
            "offset_from_center": round(offset, 1),
        })
    return result


# --- Main analysis entry point ---

_captured = False


def _analyze_and_quit():
    """Analyze the screen layout and output JSON."""
    global _captured
    if _captured:
        return True
    _captured = True

    w = pyxel.width
    h = pyxel.height

    pixels = read_pixels(w, h)
    bg_color = find_bg_color(pixels)
    bbox = content_bbox(pixels, bg_color)
    balance = calc_balance(pixels, bg_color)
    margins = calc_margins(bbox, w, h) if bbox else None

    font_h = estimate_font_height(pixels, bg_color)
    spans = detect_text(pixels, bg_color)
    merged = merge_text_spans(spans)
    text_lines = dedup_text_by_y(merged)
    text_alignment = analyze_text_alignment(text_lines, w)

    result = {
        "screen": {"w": w, "h": h},
        "bg_color": bg_color,
        "content_bbox": bbox,
        "margins": margins,
        "h_balance": balance["h_balance"],
        "v_balance": balance["v_balance"],
        "fg_pixels": balance["fg_pixels"],
        "quadrants": balance["quadrants"],
        "center_of_mass": balance["center_of_mass"],
        "text_lines": text_alignment,
        "font_height": font_h,
        "grid_alignment": check_grid_alignment(bbox, text_alignment),
    }
    print(json.dumps(result))
    sys.stdout.flush()
    return True


def _on_frame(fc, draw):
    if fc < target_frames:
        return False
    draw()
    return _analyze_and_quit()


patch_game_loop(_on_frame, on_show=lambda: _analyze_and_quit())
run_script(script_path)
