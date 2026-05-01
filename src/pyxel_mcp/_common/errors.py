"""Error handling utilities for pyxel-mcp."""

import re

_MAX_STDERR = 4000

# Prefix added to harness JSON output to distinguish it from user print output
HARNESS_JSON_PREFIX = "__PYXEL_MCP_JSON__:"

_ERROR_HINTS = [
    (
        r"TypeError.*blt\(\)",
        "blt(x, y, img, u, v, w, h, [colkey], [rotate], [scale])."
        " img can be int 0-2 or an Image instance. Use colkey=0 for transparency.",
    ),
    (
        r"TypeError.*bltm\(\)",
        "bltm(x, y, tm, u, v, w, h, [colkey], [rotate], [scale]). u,v,w,h are in pixels."
        " tm can be int 0-7 or a Tilemap instance.",
    ),
    (
        r"IndexError.*(image|sound|music|tilemap)",
        "Default slots: images[0-2], tilemaps[0-7], sounds[0-63], musics[0-7]."
        " All lists are extensible via append()/slice assignment."
        " You can also create standalone instances with Image(), Sound(), etc.",
    ),
    (
        r"AttributeError.*module.*pyxel.*has no attribute",
        "Check API spelling. Common: btnp (not button_pressed),"
        " rndi (not randint), cls (not clear). Run pyxel_info for stubs.",
    ),
    (
        r"NameError.*name '(\w+)' is not defined",
        "If using a Pyxel constant like KEY_SPACE, use pyxel.KEY_SPACE.",
    ),
    (
        r"TypeError.*'int' object is not callable",
        "pyxel.mouse_x and pyxel.mouse_y are variables, not functions."
        " Use them without ().",
    ),
    (
        r"RecursionError",
        "Check that update()/draw() don't call pyxel.run() again."
        " Ensure __init__ doesn't create recursive instances.",
    ),
]


def enrich_error(text):
    """Append fix suggestions to common Pyxel error messages."""
    if not text:
        return text
    hints = []
    for pattern, suggestion in _ERROR_HINTS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            hints.append(suggestion)
    if not hints:
        return text
    return text + "\n\nHint: " + " ".join(hints)


def decode_stderr(stderr):
    """Decode subprocess stderr, truncating if too long."""
    if not stderr:
        return ""
    text = stderr.decode(errors="replace").strip()
    if len(text) > _MAX_STDERR:
        text = text[:_MAX_STDERR] + "\n... (truncated)"
    return enrich_error(text)


def extract_stdout(raw_stdout):
    """Separate user print output from harness JSON in stdout.

    Returns (json_str, user_output). The harness prints JSON with a unique
    prefix (HARNESS_JSON_PREFIX). Everything before that line is user output.

    Falls back to the legacy heuristic (last line starting with { or [) for
    backwards compatibility with harnesses that predate the prefix.
    """
    text = raw_stdout.decode(errors="replace").strip()
    if not text:
        return "", ""
    lines = text.split("\n")

    # Primary: look for the harness marker prefix
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith(HARNESS_JSON_PREFIX):
            json_str = stripped[len(HARNESS_JSON_PREFIX):]
            user_output = "\n".join(lines[:i]).strip()
            return json_str, user_output

    # Fallback: last non-empty line starting with { or [ (legacy behaviour)
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith(("{", "[")):
            json_str = stripped
            user_lines = lines[:i]
            user_output = "\n".join(user_lines).strip()
            return json_str, user_output

    return text, ""
