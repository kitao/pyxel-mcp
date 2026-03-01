"""Sprite inspection harness - reads pixel data from Pyxel image banks.

Runs a Pyxel script with game loop patched to no-ops, then reads pixel
data from the specified image bank region and outputs analysis as JSON.

Usage:
    python sprite_harness.py <script> <image> <x> <y> <w> <h>
"""

import json
import os
import runpy
import sys

if len(sys.argv) < 7:
    print(
        "Usage: sprite_harness <script> <image> <x> <y> <w> <h>",
        file=sys.stderr,
    )
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
image_idx = int(sys.argv[2])
sx = int(sys.argv[3])
sy = int(sys.argv[4])
sw = int(sys.argv[5])
sh = int(sys.argv[6])

sys.argv = [script_path]

import pyxel

# Patch game loop functions to no-ops (we only need resource setup)
pyxel.run = lambda update, draw: None
pyxel.show = lambda: None
pyxel.flip = lambda: None

# Execute the script to set up sprites/images
sys.path.insert(0, os.path.dirname(script_path))
try:
    runpy.run_path(script_path, run_name="__main__")
except SystemExit:
    pass

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

result = {
    "image": image_idx,
    "region": {"x": sx, "y": sy, "w": sw, "h": sh},
    "pixels": pixels,
    "symmetric_h": h_symmetric,
    "h_issues": h_issues[:20],
    "symmetric_v": v_symmetric,
    "v_issues": v_issues[:10],
    "color_count": color_count,
}
print(json.dumps(result))
