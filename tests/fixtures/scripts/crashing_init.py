"""Fixture: script that crashes during __init__ before pyxel.init."""
import pyxel


class App:
    def __init__(self):
        raise RuntimeError("init kaboom")
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pass


App()
