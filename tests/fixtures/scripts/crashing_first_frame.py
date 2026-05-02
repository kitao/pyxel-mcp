"""Script that crashes on the very first update() call — frame_count must be 0
and exit_status crashed."""
import pyxel


class App:
    def __init__(self):
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        raise RuntimeError("crash at frame 0")

    def draw(self):
        pyxel.cls(0)


if __name__ == "__main__":
    App()
