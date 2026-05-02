import pyxel


class App:
    def __init__(self):
        pyxel.init(64, 64)
        pyxel.sounds[0].set("c3e3g3", "p", "5", "n", 30)
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(0)


App()
