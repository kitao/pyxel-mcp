from pathlib import Path


def test_instructions_present():
    # Resolve relative to this file so the test works regardless of CWD.
    repo_root = Path(__file__).parent.parent.parent
    text = (repo_root / "src/pyxel_mcp/instructions.md").read_text()
    for marker in ["## Contract", "## Tools", "## Resources", "pyxel://run-snapshots-schema"]:
        assert marker in text, f"missing section: {marker}"


def test_instructions_match_the_factual_v2_surface():
    repo_root = Path(__file__).parent.parent.parent
    text = (repo_root / "src/pyxel_mcp/instructions.md").read_text()

    for tool in [
        "`run`",
        "`validate`",
        "`pyxel_info`",
        "`read_palette`",
        "`read_image`",
        "`read_tilemap`",
        "`read_audio`",
        "`diff_frames`",
    ]:
        assert tool in text

    for removed in [
        "read_animation",
        "layout",
        "ASSERT PASS",
        "hierarchy hints",
        "contrast warnings",
        "pyxel://api-reference",
    ]:
        assert removed not in text


def test_run_examples_do_not_show_relative_artifact_paths():
    from pyxel_mcp.server import run as run_tool

    repo_root = Path(__file__).parent.parent.parent
    schema = (repo_root / "src/pyxel_mcp/_resources/run-snapshots-schema.md").read_text()
    doc = run_tool.__doc__ or ""

    assert '"output": "out.png"' not in doc
    assert '"output": "clip.gif"' not in doc
    assert '"output": "<path>.png"' not in schema
    assert '"output_pattern": "<path>/{frame}_screen.png"' not in schema
    assert '"output": "<path>.gif"' not in schema
