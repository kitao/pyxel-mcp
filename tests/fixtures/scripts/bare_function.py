"""Fixture script using bare functions (no App class) — used to test state snapshot."""
import pyxel

counter = 0


def update():
    global counter
    counter += 1


def draw():
    pyxel.cls(0)


if __name__ == "__main__":
    pyxel.init(64, 64)
    pyxel.run(update, draw)
