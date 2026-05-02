"""Minimal DK fixture for integration smoke. ~100 lines."""
import pyxel

# Platform definitions: (x, y, width)
_PLATFORMS = [
    (0, 112, 128),   # floor
    (16, 88, 48),    # lower platform
    (64, 64, 48),    # upper platform
]

# Player sprite: 8x8 cyan square drawn at runtime (no asset files needed)
_SPRITE_COLOR = 11   # cyan


class App:
    def __init__(self):
        pyxel.init(128, 128, title="MiniDK", fps=30)

        # Minimal image-bank population: a few pixels so inspect_image has data
        pyxel.images[0].pset(0, 0, 11)   # player color sample
        pyxel.images[0].pset(1, 0, 8)    # enemy color sample
        pyxel.images[0].pset(0, 1, 7)    # text color sample

        # Tilemap population (safe: pset doesn't trigger tilemap_zero_zero detector)
        pyxel.tilemaps[0].pset(0, 0, (1, 0))  # floor tile
        pyxel.tilemaps[0].pset(1, 0, (1, 0))
        pyxel.tilemaps[0].pset(2, 0, (1, 0))

        self.player_x = 16
        self.player_y = 100
        self.vy = 0
        self.on_ground = False
        self.lives = 3
        self.score = 0
        self.scene = "play"  # "play" | "win"

        pyxel.run(self.update, self.draw)

    # -- physics helpers -------------------------------------------------------

    def _land_y(self, x: int) -> int | None:
        """Return the platform y that player is standing on, or None."""
        for px, py, pw in _PLATFORMS:
            if px <= x <= px + pw - 8:
                if self.player_y + 8 >= py and self.player_y + 8 <= py + 4:
                    return py - 8
        return None

    # -- update ----------------------------------------------------------------

    def update(self):
        if self.scene != "play":
            return

        # Horizontal movement
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.player_x = min(self.player_x + 2, 112)
        if pyxel.btn(pyxel.KEY_LEFT):
            self.player_x = max(self.player_x - 2, 0)

        # Jump
        if pyxel.btnp(pyxel.KEY_SPACE) and self.on_ground:
            self.vy = -6
            print(f"ASSERT PASS: jump_at_frame_{pyxel.frame_count}")

        # Gravity
        self.vy = min(self.vy + 1, 8)
        self.player_y += self.vy

        # Platform collision
        self.on_ground = False
        for px, py, pw in _PLATFORMS:
            if px <= self.player_x <= px + pw - 8:
                if self.vy >= 0 and self.player_y + 8 >= py and self.player_y < py:
                    self.player_y = py - 8
                    self.vy = 0
                    self.on_ground = True
                    break

        # Floor clamp
        if self.player_y >= 104:
            self.player_y = 104
            self.vy = 0
            self.on_ground = True

        # Win condition: reach right edge
        if self.player_x >= 112 and self.scene == "play":
            self.scene = "win"
            self.score = pyxel.frame_count
            print("ASSERT PASS: reached_goal")

    # -- draw ------------------------------------------------------------------

    def draw(self):
        pyxel.cls(1)

        # Platforms
        for px, py, pw in _PLATFORMS:
            pyxel.rect(px, py, pw, 4, 4)

        # Player
        pyxel.rect(self.player_x, self.player_y, 8, 8, _SPRITE_COLOR)

        # HUD
        pyxel.text(2, 2, f"Lives:{self.lives}", 7)
        pyxel.text(60, 2, f"Sc:{self.score}", 7)

        if self.scene == "win":
            pyxel.text(32, 56, "YOU WIN!", 10)


if __name__ == "__main__":
    App()
