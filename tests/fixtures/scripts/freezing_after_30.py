"""Fixture: state increments for the first 30 frames, then freezes.

Used to exercise stall_window_frames detection. Visible state attrs
(those a state snapshot would read) stop advancing at frame 30; the
harness's rolling buffer of state.values should converge to a single
value and trigger exit_status='stalled'.
"""
import pyxel


class App:
    def __init__(self):
        self._internal_tick = 0
        self.frozen_value = 0
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        self._internal_tick += 1
        # Stop advancing the observable state past frame 30. The single
        # leading-underscore tick counter keeps incrementing internally
        # but is excluded from state snapshots (which read top-level
        # non-underscore attrs by default, and explicit `attrs` lists
        # must reference public attrs to be useful).
        if self._internal_tick <= 30:
            self.frozen_value = self._internal_tick

    def draw(self):
        pyxel.cls(0)
        # Draw a single pixel that depends on frozen_value — once frozen,
        # the screen_grid signature stops changing too.
        pyxel.pset(self.frozen_value % 64, 0, 11)


if __name__ == "__main__":
    App()
