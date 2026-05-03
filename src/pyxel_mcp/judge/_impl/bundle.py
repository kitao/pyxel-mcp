"""judge_bundle — proof bundle completeness + dead-time check (Pattern G).

Verifies the deliverable bundle directory contains the required videos,
enough captured frames, the audio files declared in the manifest, and
that the captured frames actually move (mid-bundle pixel diff > threshold).

Pixel comparison is done inline with PIL + numpy rather than calling
into Layer 1's `diff_frames` tool, so Layer 2 stays independent of
Layer 1 (the 4-layer invariant: judge does not import observe). PIL
and numpy are already runtime dependencies, so no new imports are
introduced.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, UnidentifiedImageError

DEFAULT_CONTRACT: dict[str, Any] = {
    "required_videos": ["win-path.gif", "lose-path.gif"],
    "min_frames": 5,
    "min_dead_time_diff": 0.05,
    "audio_manifest": [],
}


def _list_pngs(frames_dir: Path) -> list[Path]:
    if not frames_dir.is_dir():
        return []
    return sorted(p for p in frames_dir.iterdir() if p.suffix.lower() == ".png")


def _png_diff_ratio(a: Path, b: Path) -> tuple[float, dict[str, Any]]:
    """Return (changed-pixel ratio, debug-dict) for two PNG paths.

    Returns ratio 0.0 with a `reason` in debug when the comparison
    can't be performed (decode failure, size mismatch). The judge
    treats those as "no movement detected" — semantically equivalent
    to a stalled frame range and routed to bundle failure.
    """
    try:
        ia = Image.open(a).convert("RGB")
        ib = Image.open(b).convert("RGB")
    except (UnidentifiedImageError, OSError) as e:
        return 0.0, {"reason": f"cannot decode: {e}"}
    if ia.size != ib.size:
        return 0.0, {
            "reason": "size mismatch",
            "size_a": list(ia.size),
            "size_b": list(ib.size),
        }
    arr_a = np.asarray(ia)
    arr_b = np.asarray(ib)
    mask = (arr_a != arr_b).any(axis=2)
    if mask.size == 0:
        return 0.0, {"reason": "empty image"}
    ratio = float(mask.sum()) / float(mask.size)
    return ratio, {"ratio": ratio}


def _dead_time_diff(frames_dir: Path) -> tuple[float, dict[str, Any]]:
    """Compare first frame against mid frame; return (ratio, debug)."""
    pngs = _list_pngs(frames_dir)
    if len(pngs) < 2:
        return 0.0, {"reason": "fewer than 2 frames available", "n_frames": len(pngs)}
    first = pngs[0]
    mid = pngs[len(pngs) // 2]
    ratio, debug = _png_diff_ratio(first, mid)
    debug["first"] = str(first)
    debug["mid"] = str(mid)
    return ratio, debug


def judge_bundle(
    observation: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a deliverable bundle directory against a contract."""
    c = {**DEFAULT_CONTRACT, **(contract or {})}
    required_videos: list[str] = c["required_videos"]
    min_frames: int = c["min_frames"]
    min_diff: float = c["min_dead_time_diff"]
    audio_manifest: list[dict[str, Any]] = c["audio_manifest"]

    bundle_dir = Path(observation.get("bundle_dir", ""))
    details: dict[str, Any] = {"bundle_dir": str(bundle_dir)}
    failures: list[str] = []

    if not bundle_dir.is_dir():
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": f"bundle dir does not exist: {bundle_dir}",
            "fail_route": "bundle",
            "details": details,
        }

    missing_videos = [v for v in required_videos if not (bundle_dir / v).is_file()]
    if missing_videos:
        failures.append(f"missing videos: {missing_videos}")
    details["missing_videos"] = missing_videos

    pngs = _list_pngs(bundle_dir / "frames")
    details["n_frames"] = len(pngs)
    if len(pngs) < min_frames:
        failures.append(f"frames/ has {len(pngs)} PNGs, need >= {min_frames}")

    audio_dir = bundle_dir / "audio"
    missing_audio = [m["name"] for m in audio_manifest if not (audio_dir / m["name"]).is_file()]
    if missing_audio:
        failures.append(f"missing audio: {missing_audio}")
    details["missing_audio"] = missing_audio

    dead_time_ratio, dt_debug = _dead_time_diff(bundle_dir / "frames")
    details["dead_time_diff_ratio"] = dead_time_ratio
    details["dead_time_debug"] = dt_debug
    if dead_time_ratio < min_diff:
        failures.append(
            f"dead-time check failed: mid-bundle frame diff {dead_time_ratio:.4f} < {min_diff}"
        )

    if failures:
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": "; ".join(failures),
            "fail_route": "bundle",
            "details": details,
        }

    return {
        "ok": True,
        "verdict": "pass",
        "evidence": (
            f"all videos present, {len(pngs)} frames, "
            f"audio manifest satisfied, dead-time diff {dead_time_ratio:.4f}"
        ),
        "fail_route": None,
        "details": details,
    }
