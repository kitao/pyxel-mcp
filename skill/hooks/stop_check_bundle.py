#!/usr/bin/env python3
"""pyxel-skill Stop hook: warn (don't block) on missing/incomplete proof bundle.

Best-effort. The hook never blocks Claude Code from stopping. It silently no-ops
when the cwd is not a pyxel-skill project (no .pyxel-skill/ marker).

The hook is a tripwire for missing artifacts only. The gate-report.json content
is the agent's responsibility; the hook does not re-evaluate it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def repo_root_from(cwd_str: str) -> Path:
    """Return the cwd as a Path. Caller already passes a usable directory."""
    return Path(cwd_str).resolve()


def is_pyxel_skill_project(root: Path) -> bool:
    return (root / ".pyxel-skill").is_dir()


def latest_bundle(root: Path) -> Path | None:
    results = root / "screenshots" / "result"
    if not results.is_dir():
        return None
    numbered: list[tuple[int, Path]] = []
    for child in results.iterdir():
        if not child.is_dir():
            continue
        try:
            numbered.append((int(child.name), child))
        except ValueError:
            continue
    if not numbered:
        return None
    numbered.sort(key=lambda pair: pair[0])
    return numbered[-1][1]


def warn(msg: str) -> None:
    print(f"[pyxel-skill] WARN: {msg}", file=sys.stderr)


def _has_video(bundle: Path, stem: str) -> bool:
    return (bundle / f"{stem}.gif").is_file() or (bundle / f"{stem}.mp4").is_file()


def _bundle_warnings(bundle: Path) -> list[str]:
    warnings: list[str] = []
    if not _has_video(bundle, "win-path"):
        warnings.append(f"bundle {bundle.name} is incomplete: missing win-path.gif/mp4.")
    if not _has_video(bundle, "lose-path"):
        warnings.append(f"bundle {bundle.name} is incomplete: missing lose-path.gif/mp4.")
    frames = bundle / "frames"
    if not frames.is_dir() or len(list(frames.glob("*.png"))) < 5:
        warnings.append(f"bundle {bundle.name} is incomplete: expected at least 5 frame PNGs.")
    audio = bundle / "audio"
    if not audio.is_dir() or not any(audio.glob("*.wav")):
        warnings.append(f"bundle {bundle.name} is incomplete: expected audio/*.wav.")
    if not (bundle / "notes.md").is_file():
        warnings.append(f"bundle {bundle.name} is incomplete: missing notes.md.")
    if not (bundle / "gate-report.json").is_file():
        warnings.append(f"bundle {bundle.name} has no gate-report.json — quality gate did not run.")
    return warnings


def main() -> None:
    # Always print {} on stdout to be non-blocking. Even if input is malformed.
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        return

    cwd = event.get("cwd", ".")
    root = repo_root_from(cwd)

    if not is_pyxel_skill_project(root):
        # Not a pyxel-skill project; silent no-op.
        print(json.dumps({}))
        return

    bundle = latest_bundle(root)
    if bundle is None:
        warn("no proof bundle found at screenshots/result/<N>/. The quality gate may have been skipped.")
        print(json.dumps({}))
        return

    for warning in _bundle_warnings(bundle):
        warn(warning)

    print(json.dumps({}))


if __name__ == "__main__":
    main()
