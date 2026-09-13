"""Fixture: loads an image asset by a path relative to this script."""

import pyxel


class App:
    def __init__(self):
        pyxel.init(32, 32)
        # conftest generates this PNG; the path is relative to the script.
        pyxel.images[0].load(0, 0, "../images/reference_a.png")
        self.loaded_color = pyxel.images[0].pget(0, 0)
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(0)
        pyxel.blt(0, 0, 0, 0, 0, 32, 32)


App()
