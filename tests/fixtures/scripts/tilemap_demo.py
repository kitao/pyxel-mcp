import pyxel
class App:
    def __init__(self):
        pyxel.init(64, 64)
        pyxel.images[0].pset(8, 0, 11)   # mark (1,0) as non-empty
        pyxel.images[0].pset(16, 0, 8)   # mark (2,0) as non-empty
        for ty in range(5, 8):
            for tx in range(5, 8):
                pyxel.tilemaps[0].pset(tx, ty, (1, 0))
        pyxel.run(self.update, self.draw)
    def update(self): pass
    def draw(self): pyxel.cls(0)
App()
