import pyxel


class App:
    def __init__(self):
        self.x = 0
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.x += 1
        elif pyxel.btn(pyxel.KEY_LEFT):
            self.x -= 1

    def draw(self):
        pyxel.cls(0)


App()
