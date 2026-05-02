"""Smallest valid Pyxel script — used as a test fixture."""
import pyxel


class App:
    def __init__(self):
        pyxel.init(64, 64, title="Minimal")
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(0)


if __name__ == "__main__":
    App()
