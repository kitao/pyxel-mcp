"""Report formatters: convert harness JSON output into readable text."""

import json

from pyxel_mcp._palette import (
    analyze_hierarchy,
    classify_color,
    color_name,
    luminance,
    wcag_contrast,
)

# Material detection: sets of palette indices that indicate a material
_MATERIAL_SETS = [
    (frozenset([4, 15, 7]), "skin"),
    (frozenset([3, 11, 10]), "green"),
    (frozenset([1, 6, 12]), "blue"),
    (frozenset([2, 8, 9]), "red"),
    (frozenset([5, 13, 7]), "metal"),
    (frozenset([4, 9, 15]), "wood"),
]


def _detect_materials(nonzero_color_indices):
    """Return list of material names whose colors are all present."""
    present = set(nonzero_color_indices)
    return [mat for keys, mat in _MATERIAL_SETS if keys.issubset(present)]


def format_sprite_report(data):
    """Format sprite inspection JSON into a readable report."""
    pixels = data["pixels"]
    region = data["region"]
    w, h = region["w"], region["h"]

    lines = [
        f"Sprite at image[{data['image']}] ({region['x']},{region['y']}) {w}x{h}",
        "",
        "Pixels (hex):",
    ]
    has_extended = any(c > 15 for row in pixels for c in row)
    for row in pixels:
        if has_extended:
            hex_row = " ".join(f"{c:02x}" for c in row)
        else:
            hex_row = "".join(f"{c:x}" for c in row)
        lines.append(f"  {hex_row}")

    lines.append("")

    # Symmetry info
    lines.append(f"H-symmetry: {'yes' if data['symmetric_h'] else 'no'}")
    lines.append(f"V-symmetry: {'yes' if data['symmetric_v'] else 'no'}")

    # Color usage
    lines.append("")
    lines.append("Colors:")
    color_count = data["color_count"]
    for c_str, count in sorted(color_count.items(), key=lambda x: -x[1]):
        c = int(c_str) if isinstance(c_str, str) else c_str
        name = color_name(c)
        lines.append(f"  {c:x}({name}): {count}px")

    # --- Suggestions ---
    suggestions = []

    # Outline check: non-zero pixels on sprite boundary
    border_nonzero = data.get("border_nonzero")
    border_total = data.get("border_total")
    if border_nonzero is not None and border_total and border_nonzero > 0:
        suggestions.append(
            f"Add black outline: {border_nonzero}/{border_total} border"
            f" pixels are non-zero (color 0 not used as outline)"
        )

    # Color count validation
    nonzero_colors = set()
    for c_str in color_count:
        c = int(c_str) if isinstance(c_str, str) else c_str
        if c != 0:
            nonzero_colors.add(c)
    n_colors = len(nonzero_colors)
    if w <= 8 and h <= 8 and n_colors > 4:
        suggestions.append(
            f"Too many colors for {w}x{h}: {n_colors} non-zero colors"
            f" (max 4 recommended for 8x8)"
        )
    elif (w <= 16 and h <= 16) and n_colors > 6:
        suggestions.append(
            f"Too many colors for {w}x{h}: {n_colors} non-zero colors"
            f" (max 6 recommended for 16x16)"
        )

    # Pillow shading detection: center brighter than edges on average
    edge_colors = data.get("edge_colors", [])
    center_colors = data.get("center_colors", [])
    if edge_colors and center_colors:
        avg_edge_lum = sum(luminance(c) for c in edge_colors) / len(edge_colors)
        avg_center_lum = sum(luminance(c) for c in center_colors) / len(center_colors)
        if avg_center_lum > avg_edge_lum + 20:
            suggestions.append(
                "Possible pillow shading: center is brighter than edges"
                " — shadows should be on bottom/right, highlights on top/left"
            )

    # Material hints
    materials = _detect_materials(nonzero_colors)
    if materials:
        mat_str = ", ".join(materials)
        suggestions.append(f"Material hint: {mat_str}")

    # Empty space check
    fill_ratio = data.get("fill_ratio")
    if fill_ratio is not None and fill_ratio < 0.2:
        suggestions.append(
            f"Sprite is mostly empty (fill ratio {fill_ratio:.1%})"
            f" — consider a smaller region or denser pixel art"
        )

    if suggestions:
        lines.append("")
        lines.append("=== Suggestions ===")
        for s in suggestions:
            lines.append(f"  - {s}")

    return "\n".join(lines)


def format_layout_report(data):
    """Format layout analysis JSON into a readable report."""
    screen = data["screen"]
    sw, sh = screen["w"], screen["h"]
    bg = data["bg_color"]
    warnings = []
    suggestions = []
    lines = [
        f"Screen: {sw}x{sh}  bg_color: {bg}"
        f" ({color_name(bg)})",
    ]

    bbox = data.get("content_bbox")
    if bbox:
        cx = bbox["x"] + bbox["w"] / 2
        cy = bbox["y"] + bbox["h"] / 2
        off_x = cx - sw / 2
        off_y = cy - sh / 2
        lines.append(
            f"Content bbox: ({bbox['x']},{bbox['y']})"
            f" {bbox['w']}x{bbox['h']}"
            f"  center=({cx:.0f},{cy:.0f})"
            f" offset=({off_x:+.0f},{off_y:+.0f})px"
        )

    # Font height
    font_height = data.get("font_height")
    if font_height is not None:
        lines.append(f"Detected font height: {font_height}px")

    # Margins
    margins = data.get("margins")
    if margins:
        t, b = margins["top"], margins["bottom"]
        l, r = margins["left"], margins["right"]
        lines.append(
            f"Margins: top={t} bottom={b} left={l} right={r}"
        )
        # Flag asymmetric margins
        if max(t, b) > 0 and min(t, b) >= 0:
            v_ratio = max(t, b) / max(min(t, b), 1)
            if v_ratio > 2.0 and abs(t - b) > 4:
                warnings.append(
                    f"Vertical margin imbalance: top={t} vs bottom={b}"
                    f" — content not vertically centered"
                )
                suggestions.append(
                    f"Center content vertically: top={t} vs bottom={b}"
                    f" — adjust y position or screen height"
                )
        if max(l, r) > 0 and min(l, r) >= 0:
            h_ratio = max(l, r) / max(min(l, r), 1)
            if h_ratio > 2.0 and abs(l - r) > 4:
                warnings.append(
                    f"Horizontal margin imbalance: left={l} vs right={r}"
                    f" — content not horizontally centered"
                )
                suggestions.append(
                    f"Center content horizontally: left={l} vs right={r}"
                    f" — adjust x position or screen width"
                )

    # Balance
    fg = data["fg_pixels"]
    h_bal = data["h_balance"]
    v_bal = data.get("v_balance", 0)
    lines.append(
        f"H-balance: {h_bal:.1%}  (left:{fg['left']}px right:{fg['right']}px)"
    )
    lines.append(
        f"V-balance: {v_bal:.1%}  (top:{fg.get('top', 0)}px"
        f" bottom:{fg.get('bottom', 0)}px)"
    )
    if h_bal < 0.7:
        warnings.append("Significant left/right imbalance")
        suggestions.append(
            "Redistribute content horizontally — left/right pixel"
            " ratio is below 70%"
        )
    if v_bal < 0.7:
        warnings.append("Significant top/bottom imbalance")
        suggestions.append(
            "Redistribute content vertically — top/bottom pixel"
            " ratio is below 70%"
        )

    # Center of mass
    com = data.get("center_of_mass")
    if com:
        com_off_x = com["x"] - sw / 2
        com_off_y = com["y"] - sh / 2
        lines.append(
            f"Center of mass: ({com['x']},{com['y']})"
            f"  offset=({com_off_x:+.1f},{com_off_y:+.1f})px from screen center"
        )

    # Quadrants
    quads = data.get("quadrants")
    if quads and fg["total"] > 0:
        total = fg["total"]
        q_pct = {k: v / total * 100 for k, v in quads.items()}
        lines.append(
            f"Quadrants: TL={q_pct['tl']:.0f}% TR={q_pct['tr']:.0f}%"
            f" BL={q_pct['bl']:.0f}% BR={q_pct['br']:.0f}%"
        )
        # Detect empty or sparse quadrants
        max_q = max(q_pct.values())
        for name, pct in q_pct.items():
            if pct < 5 and max_q > 30:
                label = {"tl": "top-left", "tr": "top-right",
                         "bl": "bottom-left", "br": "bottom-right"}[name]
                warnings.append(f"Near-empty quadrant: {label} ({pct:.0f}%)")

    # Grid alignment
    grid_align = data.get("grid_alignment")
    if grid_align:
        parts = []
        for grid in [8, 16]:
            info = grid_align.get(grid) or grid_align.get(str(grid))
            if info:
                score = info["score"]
                parts.append(f"{grid}px:{score}/4")
        if parts:
            lines.append(f"Grid alignment: {', '.join(parts)}")
        # Suggest grid alignment if both scores are low
        for grid in [8, 16]:
            info = grid_align.get(grid) or grid_align.get(str(grid))
            if info and info["score"] < 2:
                misaligned = []
                for axis in ["x", "y", "w", "h"]:
                    if not info[axis]:
                        misaligned.append(axis)
                suggestions.append(
                    f"Align content to {grid}px grid:"
                    f" {', '.join(misaligned)} not on {grid}px boundary"
                )

    # Text lines
    text_lines = data.get("text_lines", [])
    if text_lines:
        lines.append("")
        lines.append(f"Text lines detected: {len(text_lines)}")
        for tl in text_lines:
            cname = color_name(tl["color"])
            off = tl["offset_from_center"]
            align = "centered" if abs(off) <= 2 else f"offset {off:+.0f}px"
            lines.append(
                f"  y={tl['y']:3d}  x={tl['x']:3d}  w={tl['w']:3d}px"
                f"  color={tl['color']:x}({cname})"
                f"  {align}"
            )
        offsets = [tl["offset_from_center"] for tl in text_lines]
        if offsets:
            spread = max(offsets) - min(offsets)
            if spread > 20:
                warnings.append(
                    f"Text alignment varies by {spread:.0f}px across lines"
                )

    # Warnings
    if warnings:
        lines.append("")
        for w in warnings:
            lines.append(f"  ⚠ {w}")

    # Suggestions
    if suggestions:
        lines.append("")
        lines.append("=== Suggestions ===")
        for s in suggestions:
            lines.append(f"  - {s}")

    return "\n".join(lines)


def format_state_report(data):
    """Format state inspection JSON into a readable report."""
    lines = [f"State at frame {data['frame']}"]

    app_type = data.get("app_type")
    if app_type:
        lines.append(f"App class: {app_type}")
    else:
        lines.append("No App instance found")
        if data.get("note"):
            lines.append(f"Note: {data['note']}")

    attrs = data.get("attributes", {})
    if isinstance(attrs, dict):
        for key, val in attrs.items():
            if key == "__type__":
                continue
            val_str = json.dumps(val, default=str) if not isinstance(val, str) else val
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            lines.append(f"  {key}: {val_str}")

    pyxel_state = data.get("pyxel", {})
    if pyxel_state:
        lines.append("")
        lines.append("Pyxel system:")
        for key, val in pyxel_state.items():
            lines.append(f"  {key}: {val}")

    return "\n".join(lines)


def format_palette_report(snap, user_output=None, stderr_text=None):
    """Format palette analysis JSON into a readable report with WCAG contrast and hierarchy."""
    w, h = snap["width"], snap["height"]
    grid = snap["grid"]
    total = w * h

    # Count colors
    counts = {}
    for row in grid:
        for c in row:
            counts[c] = counts.get(c, 0) + 1

    # Detect background (most common color)
    bg_color = max(counts, key=counts.get)
    bg_name = color_name(bg_color)
    fg_colors = {c for c in counts if c != bg_color}

    lines = [
        f"Palette analysis at frame {snap['frame']} ({w}x{h})",
        f"Background: {bg_color:x} ({bg_name}) — {counts[bg_color]}/{total} pixels"
        f" ({counts[bg_color] / total * 100:.0f}%)",
        f"Colors used: {len(counts)}",
        "",
        "Color distribution:",
    ]

    for c in sorted(counts, key=counts.get, reverse=True):
        name = color_name(c)
        pct = counts[c] / total * 100
        bar = "#" * max(1, int(pct / 2))
        lines.append(f"  {c:x} ({name:10s}): {counts[c]:6d}px ({pct:5.1f}%) {bar}")

    # Unused colors
    unused = [c for c in range(16) if c not in counts]
    if unused:
        lines.append(f"\nUnused colors: {', '.join(f'{c:x}' for c in unused)}")

    # Color hierarchy analysis
    hierarchy = analyze_hierarchy(set(counts.keys()), bg_color)
    layers = hierarchy["layers"]
    lines.append("")
    lines.append("Color hierarchy:")
    lines.append(
        f"  background={layers['background']}"
        f"  environment={layers['environment']}"
        f"  interactive={layers['interactive']}"
        f"  neutral={layers['neutral']}"
    )
    score_label = ["poor", "partial", "good"][hierarchy["score"]]
    lines.append(f"  Hierarchy score: {hierarchy['score']}/2 ({score_label})")

    # Classify each foreground color
    if fg_colors:
        lines.append("")
        lines.append("Foreground color roles:")
        for c in sorted(fg_colors):
            role = classify_color(c)
            name = color_name(c)
            lines.append(f"  {c:x} ({name:10s}): {role}")

    # WCAG contrast warnings
    wcag_warnings = []
    for c in fg_colors:
        ratio = wcag_contrast(c, bg_color)
        if ratio < 3.0:
            name = color_name(c)
            wcag_warnings.append(
                f"  Low contrast: {c:x}({name}) on {bg_color:x}({bg_name})"
                f" — WCAG ratio {ratio:.1f}:1 (AA requires 3.0+)"
            )

    if wcag_warnings:
        lines.append("")
        lines.append("Contrast warnings (WCAG AA):")
        lines.extend(wcag_warnings)

    # Suggestions
    suggestions = []

    # Low-contrast suggestions
    for c in fg_colors:
        ratio = wcag_contrast(c, bg_color)
        if ratio < 3.0:
            name = color_name(c)
            suggestions.append(
                f"Replace {c:x}({name}) or increase contrast"
                f" against background (ratio {ratio:.1f}:1)"
            )

    # Missing hierarchy layer suggestions
    if not hierarchy["has_environment"]:
        suggestions.append(
            "No environment colors — consider adding"
            " green(3), brown(4), or gray(13)"
        )
    if not hierarchy["has_interactive"]:
        suggestions.append(
            "No interactive colors — consider adding"
            " red(8), yellow(a), or lime(b) for player/items"
        )

    # Unused color suggestions
    if len(counts) < 10:
        suggestions.append(
            f"Only {len(counts)} of 16 colors used"
            " — adding more colors improves visual richness"
            " (aim for 10-14)"
        )

    if suggestions:
        lines.append("")
        lines.append("=== Suggestions ===")
        for s in suggestions:
            lines.append(f"  - {s}")

    result = "\n".join(lines)
    if user_output:
        result = f"Script output:\n{user_output}\n\n{result}"
    if stderr_text:
        result += f"\n\nstderr: {stderr_text}"
    return result


def format_animation_report(data):
    """Format animation consistency report."""
    frames = data.get("frames", [])
    if not frames:
        return "No animation frames found."

    region = data["region"]
    lines = [
        f"Animation: image[{data['image']}] ({region['x']},{region['y']}) "
        f"{region['w']}x{region['h']} x{len(frames)} frames",
        "",
    ]

    # Palette consistency: same colors used across frames
    all_palettes = [set(f["color_count"].keys()) for f in frames]
    common = set.intersection(*all_palettes) if all_palettes else set()
    union = set.union(*all_palettes) if all_palettes else set()

    lines.append(f"Colors: {len(union)} total, {len(common)} shared across all frames")

    # Per-frame pixel count (silhouette size)
    nonzero_counts = []
    for i, f in enumerate(frames):
        nz = sum(1 for row in f["pixels"] for c in row if c != 0)
        nonzero_counts.append(nz)
        lines.append(f"  Frame {i}: {nz} filled pixels, {len(f['color_count'])} colors")

    # Pixel change between consecutive frames
    lines.append("")
    lines.append("Frame differences:")
    for i in range(1, len(frames)):
        prev = frames[i - 1]["pixels"]
        curr = frames[i]["pixels"]
        changed = sum(
            1 for y in range(len(prev)) for x in range(len(prev[0]))
            if prev[y][x] != curr[y][x]
        )
        total = len(prev) * len(prev[0])
        pct = changed / total * 100 if total > 0 else 0
        lines.append(f"  Frame {i-1}→{i}: {changed}/{total} pixels ({pct:.0f}%)")

    # Suggestions
    suggestions = []

    # Silhouette consistency
    if nonzero_counts:
        avg = sum(nonzero_counts) / len(nonzero_counts)
        for i, nz in enumerate(nonzero_counts):
            if avg > 0 and abs(nz - avg) > avg * 0.3:
                suggestions.append(
                    f"Frame {i} size differs significantly ({nz} vs avg {avg:.0f})"
                )

    # Palette drift
    for i, palette in enumerate(all_palettes):
        extra = palette - common
        if extra:
            extra_names = ", ".join(str(c) for c in sorted(extra))
            suggestions.append(f"Frame {i} uses unique colors: {extra_names}")

    if suggestions:
        lines.append("")
        lines.append("=== Suggestions ===")
        for s in suggestions:
            lines.append(f"  - {s}")

    return "\n".join(lines)


def format_state_timeline(snapshots):
    """Format multi-frame state snapshots into a timeline diff report."""
    if not snapshots:
        return "No state captured"
    if len(snapshots) == 1:
        return format_state_report(snapshots[0])

    lines = [f"State timeline ({len(snapshots)} frames)"]
    lines.append("")

    # Show first frame fully
    lines.append(format_state_report(snapshots[0]))

    # Show diffs for subsequent frames
    for i in range(1, len(snapshots)):
        prev = snapshots[i - 1].get("attributes", {})
        curr = snapshots[i].get("attributes", {})
        lines.append("")
        lines.append(f"--- Changes at frame {snapshots[i]['frame']} ---")

        changes = []
        all_keys = set(list(prev.keys()) + list(curr.keys()))
        for key in sorted(all_keys):
            if key == "__type__":
                continue
            old_val = prev.get(key)
            new_val = curr.get(key)
            if old_val != new_val:
                old_s = json.dumps(old_val, default=str) if not isinstance(old_val, str) else (old_val or "(none)")
                new_s = json.dumps(new_val, default=str) if not isinstance(new_val, str) else (new_val or "(none)")
                if len(old_s) > 80:
                    old_s = old_s[:80] + "..."
                if len(new_s) > 80:
                    new_s = new_s[:80] + "..."
                changes.append(f"  {key}: {old_s} -> {new_s}")

        if changes:
            lines.extend(changes)
        else:
            lines.append("  (no changes)")

    return "\n".join(lines)
