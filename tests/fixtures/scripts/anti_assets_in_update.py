import pyxel


class App:
    def __init__(self):
        self.frame = 0
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        # Loading asset data inside update() is an anti-pattern -- do it in __init__
        pyxel.images[0].set(0, 0, ["0000", "1111"])
        self.frame += 1

    def draw(self):
        pyxel.cls(0)
        pyxel.blt(0, 0, 0, 0, 0, 8, 8, 0)


App()
