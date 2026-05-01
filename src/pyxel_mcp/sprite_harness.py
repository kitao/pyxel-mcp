"""Sprite inspection harness - reads pixel data from Pyxel image banks.

Runs a Pyxel script with game loop patched to no-ops, then reads pixel
data from the specified image bank region and outputs analysis as JSON.

Usage:
    python sprite_harness.py <script> <image> <x> <y> <w> <h> [frame_count]

When frame_count > 1, reads frame_count adjacent horizontal regions
starting at (x, y) and includes a "frames" array in the JSON output.
"""

import json
import os
import sys

if len(sys.argv) < 7:
    print(
        "Usage: sprite_harness <script> <image> <x> <y> <w> <h> [frame_count]",
        file=sys.stderr,
    )
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
image_idx = int(sys.argv[2])
sx = int(sys.argv[3])
sy = int(sys.argv[4])
sw = int(sys.argv[5])
sh = int(sys.argv[6])
frame_count = int(sys.argv[7]) if len(sys.argv) > 7 else 1

import pyxel

from pyxel_mcp._common.headless import noop_game_loop, run_script, setup_harness

setup_harness(script_path)
noop_game_loop()

# Execute the script to set up sprites/images
run_script(script_path)

# Read pixel data from the image bank
img = pyxel.images[image_idx]
pixels = []
for y in range(sy, sy + sh):
    row = []
    for x in range(sx, sx + sw):
        row.append(img.pget(x, y))
    pixels.append(row)

# Check horizontal symmetry (each row is a palindrome)
h_symmetric = True
h_issues = []
for row_idx, row in enumerate(pixels):
    n = len(row)
    for i in range(n // 2):
        j = n - 1 - i
        if row[i] != row[j]:
            h_symmetric = False
            h_issues.append({
                "row": row_idx,
                "col_l": i,
                "col_r": j,
                "val_l": row[i],
                "val_r": row[j],
            })

# Check vertical symmetry (top rows mirror bottom rows)
v_symmetric = True
v_issues = []
n_rows = len(pixels)
for i in range(n_rows // 2):
    j = n_rows - 1 - i
    if pixels[i] != pixels[j]:
        v_symmetric = False
        v_issues.append({
            "row_top": i,
            "row_bottom": j,
            "pixels_top": pixels[i],
            "pixels_bottom": pixels[j],
        })

# Color usage count
color_count = {}
for row in pixels:
    for c in row:
        color_count[c] = color_count.get(c, 0) + 1

# Border (outline) analysis: count non-zero pixels on the sprite boundary
border_nonzero = 0
border_total = 0
if sh > 0 and sw > 0:
    for x_idx in range(sw):
        border_total += 2
        if pixels[0][x_idx] != 0:
            border_nonzero += 1
        if pixels[sh - 1][x_idx] != 0:
            border_nonzero += 1
    for y_idx in range(1, sh - 1):
        border_total += 2
        if pixels[y_idx][0] != 0:
            border_nonzero += 1
        if pixels[y_idx][sw - 1] != 0:
            border_nonzero += 1

# Fill ratio: non-zero pixels / total pixels
total_pixels = sw * sh
nonzero = sum(1 for row in pixels for c in row if c != 0)
fill_ratio = round(nonzero / total_pixels, 3) if total_pixels > 0 else 0.0

# Edge vs center color distribution (for pillow shading detection)
# Classify each non-zero pixel by Manhattan distance from center
cx, cy = sw / 2.0, sh / 2.0
max_dist = cx + cy
edge_colors = []
center_colors = []
for y_idx in range(sh):
    for x_idx in range(sw):
        c = pixels[y_idx][x_idx]
        if c == 0:
            continue
        dist = abs(x_idx - cx) + abs(y_idx - cy)
        if max_dist > 0 and dist > max_dist * 0.6:
            edge_colors.append(c)
        else:
            center_colors.append(c)

result = {
    "image": image_idx,
    "region": {"x": sx, "y": sy, "w": sw, "h": sh},
    "pixels": pixels,
    "symmetric_h": h_symmetric,
    "h_issues": h_issues[:20],
    "symmetric_v": v_symmetric,
    "v_issues": v_issues[:10],
    "color_count": color_count,
    "border_nonzero": border_nonzero,
    "border_total": border_total,
    "fill_ratio": fill_ratio,
    "nonzero_pixels": nonzero,
    "edge_colors": edge_colors[:50],
    "center_colors": center_colors[:50],
}

# Multi-frame support: read adjacent horizontal regions
if frame_count > 1:
    img = pyxel.images[image_idx]
    all_frames = []
    for fi in range(frame_count):
        fx = sx + fi * sw
        frame_pixels = []
        for fy in range(sy, sy + sh):
            row = []
            for fxp in range(fx, fx + sw):
                row.append(img.pget(fxp, fy))
            frame_pixels.append(row)

        fc_colors = {}
        for row in frame_pixels:
            for c in row:
                fc_colors[c] = fc_colors.get(c, 0) + 1

        all_frames.append({
            "offset_x": fx,
            "pixels": frame_pixels,
            "color_count": fc_colors,
        })

    result["frames"] = all_frames

print("__PYXEL_MCP_JSON__:" + json.dumps(result))
sys.stdout.flush()
