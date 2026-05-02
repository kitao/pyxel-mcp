"""Script that initializes Pyxel but never calls pyxel.run — should trigger
RunNotCalledError on the harness side."""
import pyxel


class App:
    def __init__(self):
        pyxel.init(64, 64)
        # intentionally no pyxel.run() call


if __name__ == "__main__":
    App()
