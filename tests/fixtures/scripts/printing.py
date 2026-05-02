"""Fixture script that prints during init and update — used to test log capture."""
import pyxel


class App:
    def __init__(self):
        print("init message")
        pyxel.init(64, 64, title="Printing")
        pyxel.run(self.update, self.draw)

    def update(self):
        print(f"update at frame {pyxel.frame_count}")

    def draw(self):
        pyxel.cls(0)


if __name__ == "__main__":
    App()
