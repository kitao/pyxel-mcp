"""Fixture: a script that uses Python stdlib random during the game loop.

Used by test_run to verify run.py seeds both pyxel.rseed AND random.seed
when random_seed is provided (instructions.md §RNG seeding contract).
"""
import pyxel
import random


class App:
    def __init__(self):
        pyxel.init(8, 8)
        self.samples = []
        pyxel.run(self.update, self.draw)

    def update(self):
        # Capture a Python-stdlib random sample each frame.
        self.samples.append(random.random())

    def draw(self):
        pyxel.cls(0)


App()
