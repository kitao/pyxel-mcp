import pyxel


class App:
    def __init__(self):
        self.t = 0
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        self.t += 1

    def draw(self):
        pyxel.cls(0)
        # Mutating palette colors inside a loop per frame is a perf trap
        for i in range(8):
            pyxel.colors[i] = (self.t * i) % 0xFFFFFF


App()
