import pyxel


class App:
    def __init__(self):
        self.bullets = [1, 2, 3, 4, 5]
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        # Removing items from a list while iterating it causes skipped elements
        for b in self.bullets:
            if b > 3:
                self.bullets.remove(b)

    def draw(self):
        pyxel.cls(0)


App()
