"""Fixture that consumes both RNGs while the App is being constructed."""

import random

import pyxel


MODULE_STDLIB_VALUE = random.getrandbits(63)
MODULE_PYXEL_VALUE = pyxel.rndi(0, 2**31 - 1)


class App:
    def __init__(self):
        pyxel.init(8, 8)
        self.module_stdlib_value = MODULE_STDLIB_VALUE
        self.module_pyxel_value = MODULE_PYXEL_VALUE
        self.stdlib_value = random.getrandbits(63)
        self.pyxel_value = pyxel.rndi(0, 2**31 - 1)
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(0)


App()
