import pyxel


class App:
    def __init__(self):
        self.jumps = 0
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.jumps += 1

    def draw(self):
        pyxel.cls(0)


App()
