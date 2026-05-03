"""Scheduled input application (spec §6.3)."""
from __future__ import annotations
from typing import TypedDict


class ValidationError(ValueError):
    """Raised by InputScheduler when input is malformed."""


class InputEvent(TypedDict, total=False):
    frame: int
    buttons: list[str]
    axes: dict[str, float]
    mouse_pos: list[int]


class InputScheduler:
    """Tracks held button / axis / mouse state across scheduled events."""

    def __init__(self, events: list[InputEvent]):
        self._validate(events)
        self.events = sorted(events, key=lambda e: e["frame"])
        self._held_buttons: set[str] = set()
        # Tracks which buttons were held in the previous apply_to_pyxel() call.
        # Pyxel 2.9.4 derives btnp from set_btn(True) being called on a fresh
        # post-flip slate; re-calling set_btn(True) for already-held buttons
        # would spuriously re-fire btnp. Only new-press edges call set_btn(True);
        # continued holds skip the call; releases call set_btn(False).
        self._prev_held_buttons: set[str] = set()
        self._held_axes: dict[str, float] = {}
        self._mouse_pos: tuple[int, int] = (0, 0)
        self._next_event_idx = 0

    def _validate(self, events: list[InputEvent]) -> None:
        seen_frames: set[int] = set()
        for ev in events:
            if "frame" not in ev or not isinstance(ev["frame"], int):
                raise ValidationError(f"event missing or non-int frame: {ev}")
            if ev["frame"] in seen_frames:
                raise ValidationError(f"duplicate frame: {ev['frame']}")
            seen_frames.add(ev["frame"])

            if "buttons" in ev and ev["buttons"] is not None:
                if not isinstance(ev["buttons"], list):
                    raise ValidationError(f"buttons must be list, got {type(ev['buttons'])}")
                for name in ev["buttons"]:
                    self._verify_pyxel_constant(name, "button")

            if "axes" in ev and ev["axes"] is not None:
                if not isinstance(ev["axes"], dict):
                    raise ValidationError(f"axes must be dict, got {type(ev['axes'])}")
                for name, value in ev["axes"].items():
                    self._verify_pyxel_constant(name, "axis")
                    if not isinstance(value, (int, float)) or not (-1.0 <= float(value) <= 1.0):
                        raise ValidationError(f"axes value out of [-1.0, 1.0]: {name}={value}")

    def _verify_pyxel_constant(self, name: str, kind: str) -> None:
        import pyxel
        if not hasattr(pyxel, name):
            raise ValidationError(f"unknown {kind} name: {name}")

    def advance_to_frame(self, frame: int) -> None:
        """Apply all events whose frame <= the given frame, updating held state."""
        while (
            self._next_event_idx < len(self.events)
            and self.events[self._next_event_idx]["frame"] <= frame
        ):
            ev = self.events[self._next_event_idx]
            if "buttons" in ev and ev["buttons"] is not None:
                self._held_buttons = set(ev["buttons"])
            if "axes" in ev and ev["axes"] is not None:
                self._held_axes = dict(ev["axes"])
            if "mouse_pos" in ev and ev["mouse_pos"] is not None:
                x, y = ev["mouse_pos"]
                self._mouse_pos = (int(x), int(y))
            self._next_event_idx += 1

    def held_buttons(self) -> set[str]:
        """Return the current set of held button names."""
        return set(self._held_buttons)

    def held_axes(self) -> dict[str, float]:
        """Return the current axis name → value mapping."""
        return dict(self._held_axes)

    def mouse_pos(self) -> tuple[int, int]:
        """Return the current mouse position as (x, y)."""
        return self._mouse_pos

    def apply_to_pyxel(self) -> None:
        """Push held state into pyxel using set_btn / set_btnv / set_mouse_pos.

        Called at the start of each frame F by the run loop. The scheduler must
        first have been advanced to F via advance_to_frame(F).

        Edge-detection contract (Pyxel 2.9.4):
        - set_btn(K, True) on a post-flip fresh slate → btnp(K) returns True
        - Skipping set_btn(K, ...) for a held key → btn(K) stays True, btnp False
        - set_btn(K, False) → btn(K) becomes False, btnp False
        To correctly model btnp, only newly-pressed buttons (press edges) call
        set_btn(True); continuously-held buttons skip the call; releases call False.
        """
        import pyxel

        prev = self._prev_held_buttons
        curr = self._held_buttons

        # New press edges: call set_btn(True) to trigger btnp
        for name in curr - prev:
            pyxel.set_btn(getattr(pyxel, name), True)

        # Released keys: call set_btn(False) to clear btn and trigger btnr
        for name in prev - curr:
            pyxel.set_btn(getattr(pyxel, name), False)

        # Continuously held keys: no set_btn call; Pyxel retains btn=True, btnp=False

        self._prev_held_buttons = set(curr)

        # Axes: scale [-1.0, 1.0] → int range -32768..32767 (Pyxel set_btnv convention).
        for name, value in self._held_axes.items():
            scaled = int(round(value * 32767))
            pyxel.set_btnv(getattr(pyxel, name), scaled)

        # Mouse position: prefer Pyxel 2.9+ set_mouse_pos; fall back to attribute patch.
        x, y = self._mouse_pos
        if hasattr(pyxel, "set_mouse_pos"):
            pyxel.set_mouse_pos(x, y)
        else:
            try:
                pyxel.mouse_x = x  # type: ignore[attr-defined]
                pyxel.mouse_y = y  # type: ignore[attr-defined]
            except (AttributeError, TypeError):
                pass  # mouse simulation requires Pyxel 2.9+ if attribute is read-only
