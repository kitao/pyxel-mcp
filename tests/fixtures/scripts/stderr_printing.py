"""Fixture script that writes to stderr — used to test stderr capture in log."""
import sys
import pyxel


class App:
    def __init__(self):
        print("stderr message", file=sys.stderr)
        pyxel.init(64, 64, title="Stderr")
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(0)


if __name__ == "__main__":
    App()
