"""Scheduled input application."""

from __future__ import annotations

from pydantic import TypeAdapter
from pydantic import ValidationError as ModelValidationError

from pyxel_mcp.contracts import InputEvent


class ValidationError(ValueError):
    """Raised by InputScheduler when input is malformed."""


_EVENTS = TypeAdapter(list[InputEvent])


class InputScheduler:
    """Tracks held button / axis / mouse state across scheduled events."""

    def __init__(self, events: list[InputEvent | dict]):
        try:
            parsed = _EVENTS.validate_python(events)
        except ModelValidationError as exc:
            raise ValidationError(str(exc)) from exc
        self._validate(parsed)
        self.events = [
            event.model_dump(exclude_none=True)
            for event in sorted(parsed, key=lambda event: event.frame)
        ]
        self._held_buttons: set[str] = set()
        # Buttons held during the previous apply_to_pyxel() call. Pyxel fires
        # btnp when set_btn(True) lands on a fresh post-flip slate, so only new
        # presses may call it; continued holds skip the call and releases call
        # set_btn(False).
        self._prev_held_buttons: set[str] = set()
        self._held_axes: dict[str, float] = {}
        self._prev_held_axes: set[str] = set()
        self._mouse_pos: tuple[int, int] = (0, 0)
        self._next_event_idx = 0

    def _validate(self, events: list[InputEvent]) -> None:
        seen_frames: set[int] = set()
        for event in events:
            if event.frame in seen_frames:
                raise ValidationError(f"duplicate frame: {event.frame}")
            seen_frames.add(event.frame)
            for name in event.buttons or []:
                self._verify_pyxel_constant(name, "button")
            for name in event.axes or {}:
                self._verify_pyxel_constant(name, "axis")

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

        Called at the start of each frame after advance_to_frame(frame).

        Edge contract: set_btn(K, True) on a fresh post-flip slate makes btnp(K)
        true; skipping the call for a held key keeps btn(K) true and btnp false;
        set_btn(K, False) releases it. Only press edges therefore call
        set_btn(True).
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

        # An explicit axes map replaces the held map. Pyxel retains axis
        # values across flip(), so omitted axes must be returned to neutral.
        for name in self._prev_held_axes - self._held_axes.keys():
            pyxel.set_btnv(getattr(pyxel, name), 0)

        # Axes: scale [-1.0, 1.0] → int range -32768..32767 (Pyxel set_btnv convention).
        for name, value in self._held_axes.items():
            scaled = round(value * 32767)
            pyxel.set_btnv(getattr(pyxel, name), scaled)
        self._prev_held_axes = set(self._held_axes)

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
