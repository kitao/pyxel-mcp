"""Layer 2 — judge primitives.

Each `judge_*` function is a pure mapping `(observation, contract) -> verdict`
where `observation` comes from a Layer 1 (`observe/...`) tool and `contract`
is a small dict typically sourced from PLAN.md / ASSETS.md (or omitted to use
the module's `DEFAULT_CONTRACT`).
"""
from __future__ import annotations

from pyxel_mcp.judge._impl.animation import judge_animation
from pyxel_mcp.judge._impl.audio import judge_audio
from pyxel_mcp.judge._impl.bundle import judge_bundle
from pyxel_mcp.judge._impl.genre import judge_genre
from pyxel_mcp.judge._impl.layout import judge_layout
from pyxel_mcp.judge._impl.milestone import judge_milestone
from pyxel_mcp.judge._impl.palette import judge_palette
from pyxel_mcp.judge._impl.sprite import judge_sprite

__all__ = [
    "judge_palette",
    "judge_sprite",
    "judge_animation",
    "judge_milestone",
    "judge_genre",
    "judge_bundle",
    "judge_audio",
    "judge_layout",
]
