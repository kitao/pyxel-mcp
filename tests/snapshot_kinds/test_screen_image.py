"""Tests for snapshot_kinds.screen_image (spec §6.4.1)."""
import struct
from pyxel_mcp._harnesses._common.snapshot_kinds.screen_image import capture
from pyxel_mcp._harnesses._common.pyxel_patcher import headless_pyxel


def _png_size(path) -> tuple[int, int]:
    """Read PNG IHDR to get (width, height) without depending on PIL."""
    data = path.read_bytes()
    # PNG signature (8 bytes) + IHDR chunk: length(4) + "IHDR"(4) + w(4) + h(4)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width = struct.unpack(">I", data[16:20])[0]
    height = struct.unpack(">I", data[20:24])[0]
    return width, height


def test_capture_writes_png(tmp_path):
    """capture should write a PNG of the current pyxel screen."""
    import pyxel
    with headless_pyxel():
        pyxel.init(32, 32)
        pyxel.cls(0)
    out = tmp_path / "shot.png"
    result = capture({"frame": 0, "kind": "screen_image", "output": str(out), "scale": 1})
    assert out.exists()
    assert result["frame"] == 0
    assert result["kind"] == "screen_image"
    assert result["path"] == str(out.resolve())
    # headless_pyxel skips re-init when Pyxel is already up; use the actual
    # runtime dimensions rather than hard-coding the requested 32x32.
    assert result["size"] == [pyxel.width, pyxel.height]
    assert _png_size(out) == (pyxel.width, pyxel.height)


def test_capture_with_scale(tmp_path):
    """capture should scale the PNG by the given integer factor."""
    import pyxel
    with headless_pyxel():
        # headless_pyxel skips re-init if Pyxel is already up; use whatever
        # width/height are current (set by the first test that ran init).
        pyxel.init(32, 32)
        pyxel.cls(0)
    scale = 3
    out = tmp_path / "shot.png"
    capture({"frame": 0, "kind": "screen_image", "output": str(out), "scale": scale})
    w, h = _png_size(out)
    assert w == pyxel.width * scale
    assert h == pyxel.height * scale


def test_capture_creates_parent_dirs(tmp_path):
    """capture should create missing parent directories automatically."""
    import pyxel
    with headless_pyxel():
        pyxel.init(16, 16)
        pyxel.cls(0)
    out = tmp_path / "deeper" / "path" / "shot.png"
    capture({"frame": 0, "kind": "screen_image", "output": str(out), "scale": 1})
    assert out.exists()
