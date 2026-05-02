import pyxel


class App:
    def __init__(self):
        self.last_x_axis = 0.0
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        self.last_x_axis = pyxel.btnv(pyxel.GAMEPAD1_AXIS_LEFTX)

    def draw(self): pyxel.cls(0)


App()
