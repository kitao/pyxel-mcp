import pyxel
import math


class App:
    def __init__(self):
        self.t = 0
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        self.t += 1

    def draw(self):
        pyxel.cls(0)
        # math.sin takes radians, pyxel.sin takes degrees -- mixing them is a bug
        x = 32 + int(math.sin(self.t * 0.1) * 20)  # radians
        y = 32 + int(pyxel.sin(self.t * 3) * 20)    # degrees
        pyxel.pset(x, y, 7)


App()
