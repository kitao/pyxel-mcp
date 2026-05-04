import pyxel


class App:
    def __init__(self):
        pyxel.init(64, 64)
        # 8x8 sprite — 8 hex chars per row expected, but row 2 is 6 chars
        pyxel.images[0].set(0, 0, [
            "00ff00ff",
            "00ff00",          # ragged: only 6 chars
            "00ff00ff",
            "00ff00ff",
            "00ff00ff",
            "00ff00ff",
            "00ff00ff",
            "00ff00ff",
        ])
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(0)


App()
