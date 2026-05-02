import pyxel
class App:
    def __init__(self):
        self.last_x = -1
        self.last_y = -1
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)
    def update(self):
        self.last_x = pyxel.mouse_x
        self.last_y = pyxel.mouse_y
    def draw(self): pyxel.cls(0)
App()
