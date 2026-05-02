import pyxel


class App:
    def __init__(self):
        pyxel.init(64, 64)
        pyxel.tilemaps[0].set(0, 0, ["0102"])  # tile placed at source-bank (0, 0) = trap
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(0)


App()
