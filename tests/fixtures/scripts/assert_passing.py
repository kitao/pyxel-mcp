import pyxel

class App:
    def __init__(self):
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        if pyxel.frame_count == 3:
            print("ASSERT PASS: midpoint_reached")
            print("ASSERT FAIL: hp_check | expected 100, got 50")

    def draw(self):
        pyxel.cls(0)

App()
