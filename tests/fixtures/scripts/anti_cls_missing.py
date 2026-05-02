import pyxel


class App:
    def __init__(self):
        self.x = 0
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        self.x = (self.x + 1) % 64

    def draw(self):
        # Drawing before cls() -- screen accumulates ghost trails
        pyxel.pset(self.x, 32, 7)
        pyxel.cls(0)


App()
