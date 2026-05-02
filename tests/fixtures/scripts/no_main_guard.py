"""Script that instantiates App() at module top level (no `if __name__ == "__main__":`
guard) — must still be loaded and run correctly by the harness."""
import pyxel


class App:
    def __init__(self):
        pyxel.init(64, 64, title="NoMainGuard")
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(0)


App()
