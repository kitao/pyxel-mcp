import pyxel
import time


class App:
    def __init__(self):
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        time.sleep(60)  # hang

    def draw(self):
        pyxel.cls(0)


App()
