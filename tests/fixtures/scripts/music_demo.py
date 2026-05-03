"""Fixture: a script that populates pyxel.musics[0] wrapping sound 0.

Used by test_read_audio to verify the music branch of the render path
(audio_obj.seqs / snds_list detection, save with music slot index).
"""
import pyxel


class App:
    def __init__(self):
        pyxel.init(64, 64)
        pyxel.sounds[0].set("c3e3g3c4", "p", "5", "n", 30)
        # Music slot 0 plays sound 0 on channel 0; channels 1-3 silent.
        pyxel.musics[0].set([0], [], [], [])
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(0)


App()
