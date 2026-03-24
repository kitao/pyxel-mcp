"""Report formatters: convert harness JSON output into readable text."""

import json

from pyxel_mcp._palette import color_name


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

    return "\n".join(lines)


def format_layout_report(data):
    """Format layout analysis JSON into a readable report."""
    screen = data["screen"]
    sw, sh = screen["w"], screen["h"]
    bg = data["bg_color"]
    warnings = []
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
        if max(l, r) > 0 and min(l, r) >= 0:
            h_ratio = max(l, r) / max(min(l, r), 1)
            if h_ratio > 2.0 and abs(l - r) > 4:
                warnings.append(
                    f"Horizontal margin imbalance: left={l} vs right={r}"
                    f" — content not horizontally centered"
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
    if v_bal < 0.7:
        warnings.append("Significant top/bottom imbalance")

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
