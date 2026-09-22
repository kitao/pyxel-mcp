"""Reader subprocesses observe live state before pyxel.run returns or unwinds."""

import pytest
from PIL import Image

from pyxel_mcp import server

READERS = ["read_palette", "read_image", "read_tilemap", "read_audio"]


def _invoke(reader, script, tmp_path, *, artifact=None):
    arguments = {"script": str(script)}
    if reader == "read_image":
        arguments.update(
            image=0, w=1, h=1, render_path=str(artifact or tmp_path / "i.png")
        )
    elif reader == "read_tilemap":
        arguments.update(tilemap=0, render_path=str(artifact or tmp_path / "t.png"))
    elif reader == "read_audio":
        arguments.update(
            target={"sound": 0}, output_path=str(artifact or tmp_path / "s.wav")
        )
    return getattr(server, reader)(**arguments).structured_content


@pytest.mark.parametrize("reader", READERS)
def test_readers_observe_before_mutations_and_finish_artifacts_before_cleanup(
    tmp_path, reader
):
    script = tmp_path / "app.py"
    marker = tmp_path / "cleanup.txt"
    artifact = tmp_path / ("observed.wav" if reader == "read_audio" else "observed.png")
    artifact_check = (
        "True" if reader == "read_palette" else f"Path({str(artifact)!r}).is_file()"
    )
    script.write_text(
        "import pyxel\nfrom pathlib import Path\n"
        "pyxel.init(8, 8)\n"
        "pyxel.colors[7] = 0x123456\n"
        "pyxel.images[0].cls(7)\n"
        "pyxel.tilemaps[0].pset(0, 0, (1, 0))\n"
        "pyxel.sounds[0].set('c3', 't', '7', 'n', 8)\n"
        f"with open({str(marker)!r}, 'w') as resource:\n"
        "    try:\n"
        "        pyxel.run(lambda: None, lambda: None)\n"
        "        resource.write('returned from first run')\n"
        "        pyxel.run(lambda: None, lambda: None)\n"
        "    finally:\n"
        f"        resource.write('artifact ready' if {artifact_check} else 'artifact missing')\n"
        "        pyxel.colors[7] = 0xabcdef\n"
        "        pyxel.images[0].cls(0)\n"
        "        pyxel.tilemaps[0].cls((0, 0))\n"
        "        pyxel.sounds[0].set('', '', '', '', 8)\n"
    )
    result = _invoke(reader, script, tmp_path, artifact=artifact)
    assert result["ok"] is True
    assert marker.read_text() == "artifact ready"
    if reader == "read_palette":
        assert result["colors"]["7"] == "#123456"
        assert 7 in result["used_indices"]
    elif reader == "read_image":
        assert result["pixels"] == [[7]]
    elif reader == "read_tilemap":
        assert result["usage"] == {"1,0": 1}
        assert result["zero_tile_nonempty"] is True
    else:
        assert result["notes"][0]["note"] == "C3"
        assert result["peak_amplitude"] > 0
    if reader in {"read_image", "read_tilemap"}:
        with Image.open(artifact) as image:
            assert image.getpixel((0, 0)) == (0x12, 0x34, 0x56)


@pytest.mark.parametrize("reader", READERS)
@pytest.mark.parametrize("run_in_finally", [False, True])
def test_reader_quit_before_checkpoint_is_structured_error(
    tmp_path, reader, run_in_finally
):
    script = tmp_path / "quit.py"
    body = (
        "try:\n    pyxel.quit()\nfinally:\n    pyxel.run(lambda: None, lambda: None)\n"
        if run_in_finally
        else "pyxel.quit()\npyxel.run(lambda: None, lambda: None)\n"
    )
    script.write_text("import pyxel\npyxel.init(8, 8)\n" + body)
    result = _invoke(reader, script, tmp_path)
    assert result["ok"] is False
    assert result["errors"][0]["phase"] == "script_import"
    assert "quit before" in result["errors"][0]["message"]
    assert not any(path.suffix in {".png", ".wav"} for path in tmp_path.iterdir())


@pytest.mark.parametrize("reader", READERS)
def test_reader_cleanup_failure_does_not_report_success(tmp_path, reader):
    script = tmp_path / "cleanup_failure.py"
    script.write_text(
        "import pyxel\npyxel.init(8, 8)\n"
        "try:\n"
        "    pyxel.run(lambda: None, lambda: None)\n"
        "finally:\n"
        "    raise RuntimeError('cleanup failed on purpose')\n"
    )
    result = _invoke(reader, script, tmp_path)
    assert result["ok"] is False
    assert result["errors"][0]["phase"] == "script_exit"
    assert "cleanup failed on purpose" in result["errors"][0]["message"]


@pytest.mark.parametrize("reader", ["read_image", "read_tilemap", "read_audio"])
def test_reader_artifact_failure_keeps_artifact_phase(tmp_path, reader):
    script = tmp_path / "app.py"
    script.write_text(
        "import pyxel\npyxel.init(8, 8)\npyxel.run(lambda: None, lambda: None)\n"
    )
    parent = tmp_path / "not-a-directory"
    parent.write_text("file blocks the output directory")
    output = parent / ("output.wav" if reader == "read_audio" else "output.png")
    result = _invoke(reader, script, tmp_path, artifact=output)
    assert result["ok"] is False
    assert result["errors"][0]["phase"] == "artifact"
    assert result["errors"][0]["path"] == str(output)
