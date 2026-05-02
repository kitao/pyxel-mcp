import pyxel


class App:
    def __init__(self):
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(0)
        pyxel.blt(0, 0, 0, 0, 0, 16, 16)  # missing colkey


App()
