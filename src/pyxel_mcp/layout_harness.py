"""Layout analysis harness - analyzes screen composition and text alignment.

Runs a Pyxel script, captures at a specified frame, then reads all screen
pixels and analyzes layout balance, content centering, and text positioning.

Usage:
    python layout_harness.py <script> <frames>
"""

import json
import os
import runpy
import sys

if len(sys.argv) < 3:
    print("Usage: layout_harness <script> <frames>", file=sys.stderr)
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
target_frames = int(sys.argv[2])

sys.argv = [script_path]

import pyxel

# Turbo mode: override FPS to run as fast as possible
_original_init = pyxel.init


def _turbo_init(*args, **kwargs):
    kwargs["fps"] = 10000
    _original_init(*args, **kwargs)


pyxel.init = _turbo_init

_captured = False


def _analyze_and_quit():
    """Analyze the screen layout and output JSON."""
    global _captured
    if _captured:
        return
    _captured = True

    w = pyxel.width
    h = pyxel.height

    # Read all screen pixels
    pixels = []
    for y in range(h):
        row = []
        for x in range(w):
            row.append(pyxel.screen.pget(x, y))
        pixels.append(row)

    # Determine background color (most frequent)
    color_count = {}
    for row in pixels:
        for c in row:
            color_count[c] = color_count.get(c, 0) + 1
    bg_color = max(color_count, key=color_count.get)

    # Find content bounding box (non-background area)
    min_x, min_y = w, h
    max_x, max_y = 0, 0
    for y in range(h):
        for x in range(w):
            if pixels[y][x] != bg_color:
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)

    content_bbox = None
    if max_x >= min_x:
        content_bbox = {
            "x": min_x, "y": min_y,
            "w": max_x - min_x + 1, "h": max_y - min_y + 1,
        }

    # Horizontal balance: count non-bg pixels in left vs right halves
    left_count = 0
    right_count = 0
    mid_x = w // 2
    for y in range(h):
        for x in range(w):
            if pixels[y][x] != bg_color:
                if x < mid_x:
                    left_count += 1
                else:
                    right_count += 1

    total_fg = left_count + right_count
    h_balance = 0.0
    if total_fg > 0:
        h_balance = min(left_count, right_count) / max(left_count, right_count)

    # Detect text-like horizontal spans
    # Pyxel default font: 4px wide per char, 6px tall
    FONT_H = 6
    MIN_TEXT_W = 10  # minimum ~3 characters
    text_spans = []

    y = 0
    while y < h - FONT_H + 1:
        # Only scan rows where most of the row is background (HUD area).
        # Game content rows have lots of non-bg pixels and are skipped.
        bg_in_row = sum(1 for x in range(w) if pixels[y][x] == bg_color)
        if bg_in_row < w * 0.5:
            y += 1
            continue

        # Scan for text spans in this clear row
        x = 0
        row_spans = []
        while x < w:
            c = pixels[y][x]
            if c == bg_color:
                x += 1
                continue

            # Scan right: same-color pixels with small bg gaps (char spacing)
            span_start = x
            span_color = c
            gap = 0
            while x < w:
                if pixels[y][x] == span_color:
                    gap = 0
                elif pixels[y][x] == bg_color:
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
                    if pixels[y - 1][sx] == bg_color
                )
            check_below = y + FONT_H
            bg_below = span_w  # default if at bottom
            if check_below < h:
                bg_below = sum(
                    1 for sx in range(span_start, span_end)
                    if pixels[check_below][sx] == bg_color
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

    # Merge overlapping text spans on the same Y
    merged_texts = []
    for span in text_spans:
        merged = False
        for m in merged_texts:
            if (abs(span["y"] - m["y"]) <= 1
                    and span["color"] == m["color"]
                    and span["x"] <= m["x"] + m["w"] + 2):
                new_x = min(m["x"], span["x"])
                new_end = max(m["x"] + m["w"], span["x"] + span["w"])
                m["x"] = new_x
                m["w"] = new_end - new_x
                m["center_x"] = new_x + (new_end - new_x) / 2
                merged = True
                break
        if not merged:
            merged_texts.append(dict(span))

    # Deduplicate by Y position (keep widest span per Y)
    by_y = {}
    for span in merged_texts:
        y_key = span["y"]
        if y_key not in by_y or span["w"] > by_y[y_key]["w"]:
            by_y[y_key] = span
    text_lines = sorted(by_y.values(), key=lambda s: s["y"])

    # Analyze text centering
    screen_center = w / 2
    text_alignment = []
    for tl in text_lines:
        cx = tl["center_x"]
        offset = cx - screen_center
        text_alignment.append({
            "y": tl["y"],
            "x": tl["x"],
            "w": tl["w"],
            "color": tl["color"],
            "center_x": round(cx, 1),
            "offset_from_center": round(offset, 1),
        })

    result = {
        "screen": {"w": w, "h": h},
        "bg_color": bg_color,
        "content_bbox": content_bbox,
        "h_balance": round(h_balance, 3),
        "fg_pixels": {"left": left_count, "right": right_count, "total": total_fg},
        "text_lines": text_alignment,
    }
    print(json.dumps(result))
    sys.stdout.flush()
    pyxel.quit()


# Patch pyxel.run: wrap draw to analyze after rendering the target frame
_original_run = pyxel.run


def _patched_run(update, draw):
    def wrapped_draw():
        if pyxel.frame_count >= target_frames:
            draw()
            _analyze_and_quit()

    _original_run(update, wrapped_draw)


pyxel.run = _patched_run

# Patch pyxel.show
pyxel.show = lambda: _analyze_and_quit()

# Patch pyxel.flip
_flip_counter = 0
_original_flip = pyxel.flip


def _patched_flip():
    global _flip_counter
    _original_flip()
    _flip_counter += 1
    if _flip_counter >= target_frames:
        _analyze_and_quit()


pyxel.flip = _patched_flip

sys.path.insert(0, os.path.dirname(script_path))
try:
    runpy.run_path(script_path, run_name="__main__")
except SystemExit:
    pass
