"""Fixture: attribute appears only after frame 2 — tests until NameError tolerance."""
import pyxel


class App:
    def __init__(self):
        self.tick = 0
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        self.tick += 1
        if self.tick == 3:
            self.goal_reached = True

    def draw(self):
        pyxel.cls(0)


if __name__ == "__main__":
    App()
