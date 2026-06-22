"""Fixture script with a stateful App — used to test state snapshot capture."""
import pyxel


class Hazard:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class App:
    def __init__(self):
        self.counter = 0
        self.lives = 3
        self.message = "hello"
        self.player = type("P", (), {"x": 10, "y": 20})()
        self.hazards = [Hazard(50, 100), Hazard(60, 110)]
        self.scores = [100, 200, 300]
        pyxel.init(64, 64)
        pyxel.run(self.update, self.draw)

    def update(self):
        self.counter += 1

    def draw(self):
        pyxel.cls(0)


if __name__ == "__main__":
    App()
