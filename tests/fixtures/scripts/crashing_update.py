"""Fixture: script that crashes in update() at frame 5 (0-indexed)."""
import pyxel


class App:
    def __init__(self):
        pyxel.init(64, 64)
        self.tick = 0
        pyxel.run(self.update, self.draw)

    def update(self):
        if self.tick == 5:
            raise RuntimeError("update kaboom at tick 5")
        self.tick += 1

    def draw(self):
        pyxel.cls(0)


App()
