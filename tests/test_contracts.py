"""Validation rules of the public input contracts."""

import pytest
from pydantic import ValidationError

from pyxel_mcp.contracts import ScreenImageSnapshotRequest


def test_screen_image_requires_a_path_except_for_a_single_inline_frame():
    with pytest.raises(ValidationError, match="only a single inline frame"):
        ScreenImageSnapshotRequest(kind="screen_image", frame=0)
    with pytest.raises(ValidationError, match="only a single inline frame"):
        ScreenImageSnapshotRequest(kind="screen_image", frames="all", inline=True)

    inline = ScreenImageSnapshotRequest(kind="screen_image", frame="end", inline=True)
    assert inline.output is None


def test_screen_image_rejects_mismatched_path_fields():
    with pytest.raises(ValidationError, match="only one"):
        ScreenImageSnapshotRequest(
            kind="screen_image", frame=0, output="/a.png", output_pattern="/{frame}.png"
        )
    with pytest.raises(ValidationError, match="not `output_pattern`"):
        ScreenImageSnapshotRequest(
            kind="screen_image", frame=0, output_pattern="/{frame}.png"
        )
    with pytest.raises(ValidationError, match="not `output`"):
        ScreenImageSnapshotRequest(kind="screen_image", frames=[0, 1], output="/a.png")
    with pytest.raises(ValidationError, match=".png"):
        ScreenImageSnapshotRequest(kind="screen_image", frame=0, output="/a.jpg")


def test_screen_image_still_accepts_explicit_paths_with_inline():
    request = ScreenImageSnapshotRequest(
        kind="screen_image", frame=3, output="/tmp/x.png", inline=True, scale=2
    )
    assert request.model_dump(exclude_none=True) == {
        "kind": "screen_image",
        "frame": 3,
        "output": "/tmp/x.png",
        "scale": 2,
        "inline": True,
    }
