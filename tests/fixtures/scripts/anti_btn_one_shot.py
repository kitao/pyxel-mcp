import pyxel


class App:
    def __init__(self):
        self.score = 0
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        # btn() fires every frame the key is held -- should use btnp() for one-shot actions
        if pyxel.btn(pyxel.KEY_SPACE):
            pyxel.play(3, 0)

    def draw(self):
        pyxel.cls(0)
        pyxel.text(4, 4, str(self.score), 7)


App()
