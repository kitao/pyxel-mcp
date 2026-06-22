"""Repository-level checks for stale public workflow-skill content."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "skill"
SKILL_MD = ROOT / "SKILL.md"
ALLOWED_FRONTMATTER_KEYS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
STALE_PATTERNS = [
    "inspect_",
    "render_audio",
    "compare_frames",
    "run_and_capture",
    "0.10.0",
    "0.9.3",
    "v0.2.0",
    "Donkey",
    "DK",
    "Mario",
    "Princess",
    "princess",
    "barrel",
    "barrels",
    "girder",
    "girders",
    "hammer",
    "hammers",
    "13-check",
    "15-check",
    "docs/superpowers",
    "superpowers/",
]


def test_public_skill_markdown_has_no_stale_tool_or_validation_lore():
    offenders: list[str] = []
    for path in ROOT.rglob("*.md"):
        text = path.read_text().lower()
        for pattern in STALE_PATTERNS:
            if pattern.lower() in text:
                offenders.append(f"{path.relative_to(ROOT)}: {pattern}")

    assert offenders == []


def test_skill_frontmatter_uses_spec_fields():
    lines = SKILL_MD.read_text().splitlines()
    assert lines[0] == "---"
    end = lines.index("---", 1)
    keys = {
        line.split(":", 1)[0]
        for line in lines[1:end]
        if line and not line.startswith(" ") and ":" in line
    }

    assert "version" not in keys
    assert keys <= ALLOWED_FRONTMATTER_KEYS
    assert "metadata" in keys
    assert any(line == '  version: "1.0.0"' for line in lines[1:end])


def test_bundled_skill_default_surface_stays_lean():
    forbidden = {
        "visual-target.md",
        "decomposer.md",
        "scaffold.md",
        "asset-planner.md",
        "asset-gen.md",
        "task-execution.md",
        "quality-gate.md",
        "test-harness.md",
        "capture.md",
        "quirks.md",
    }
    present = {p.name for p in ROOT.glob("*.md")}
    assert forbidden.isdisjoint(present)
    assert not (ROOT / "knowledge").exists()
    assert not (ROOT / "hooks").exists()

    words = SKILL_MD.read_text().split()
    assert len(words) <= 850

    assert (ROOT / "strict-mode.md").is_file()
    assert (ROOT / "pyxel-notes.md").is_file()

def test_audio_examples_include_output_path():
    offenders = []
    for path in ROOT.rglob("*.md"):
        text = path.read_text()
        if "read_audio(target=" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
