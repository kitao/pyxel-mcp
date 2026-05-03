"""video snapshot — GIF/MP4 encoding (spec §6.4.5)."""
from __future__ import annotations
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image


class ExtensionError(ValueError):
    """Raised when output extension is not .gif or .mp4."""


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


class VideoAccumulator:
    def __init__(self, snapshot: dict[str, Any]):
        out = Path(snapshot["output"])
        ext = out.suffix.lower()
        if ext not in (".gif", ".mp4"):
            raise ExtensionError(
                f"output extension must be .gif or .mp4, got: {ext or '(none)'}"
            )
        self.snapshot = snapshot
        self.requested_output = out
        self.start_frame = int(snapshot["start_frame"])
        self.end_frame = int(snapshot["end_frame"])
        self.fps = int(snapshot.get("fps", 30))
        self.scale = int(snapshot.get("scale", 1))
        self.frames: list[Image.Image] = []
        self._tempdir = tempfile.mkdtemp(prefix="pyxel-mcp-video-")

    def add_frame(self, frame_index: int, img: Image.Image) -> None:
        if not (self.start_frame <= frame_index < self.end_frame):
            return
        if self.scale > 1:
            img = img.resize(
                (img.width * self.scale, img.height * self.scale),
                resample=Image.NEAREST,
            )
        self.frames.append(img)

    def encode(self) -> dict[str, Any]:
        warnings: list[str] = []
        out = self.requested_output
        out.parent.mkdir(parents=True, exist_ok=True)

        target_format = out.suffix.lower().lstrip(".")
        if target_format == "mp4" and not _ffmpeg_available():
            new_out = out.with_suffix(".gif")
            warnings.append(f"ffmpeg unavailable; fell back to GIF: {new_out}")
            out = new_out
            target_format = "gif"

        if target_format == "gif":
            if self.frames:
                first = self.frames[0]
                first.save(
                    out,
                    save_all=True,
                    append_images=self.frames[1:],
                    loop=0,
                    duration=int(1000 / self.fps),
                    optimize=False,
                )
            else:
                Image.new("RGB", (1, 1)).save(out)
        else:  # mp4
            for i, img in enumerate(self.frames):
                img.save(Path(self._tempdir) / f"{i:05d}.png")
            cmd = [
                "ffmpeg", "-y", "-framerate", str(self.fps),
                "-i", str(Path(self._tempdir) / "%05d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(out),
            ]
            subprocess.run(cmd, check=True, capture_output=True)

        # Cleanup temp dir
        shutil.rmtree(self._tempdir, ignore_errors=True)

        frames_encoded = len(self.frames)
        return {
            "kind": "video",
            "path": str(out.resolve()),
            "format": target_format,
            "frames_encoded": frames_encoded,
            "duration_seconds": frames_encoded / self.fps,
            "warnings": warnings,
        }
