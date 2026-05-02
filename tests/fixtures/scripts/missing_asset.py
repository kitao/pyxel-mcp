"""Fixture: script that fails loading a nonexistent asset in __init__."""
import pyxel


class App:
    def __init__(self):
        pyxel.init(64, 64)
        pyxel.images[0].load(0, 0, "/nonexistent/sprite.png")
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(0)


App()
