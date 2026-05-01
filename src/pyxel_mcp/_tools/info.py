"""Tool for reporting Pyxel installation info."""

import asyncio
import glob
import os

from pyxel_mcp._common.pyxel_env import (
    check_updates,
    pyxel_dir,
)


def register(mcp):
    @mcp.tool()
    async def pyxel_info() -> str:
        """Get Pyxel installation info: package location, examples path, and API stubs path."""
        pyxel_path = pyxel_dir()
        if not pyxel_path:
            return (
                "Pyxel is not installed.\n"
                "Install it with: pip install pyxel-mcp\n"
                "See https://github.com/kitao/pyxel for details."
            )
        examples = os.path.join(pyxel_path, "examples")
        pyi = os.path.join(pyxel_path, "__init__.pyi")
        lines = [
            f"Pyxel package: {pyxel_path}",
            f"API type stubs: {pyi}" + (" (found)" if os.path.isfile(pyi) else " (not found)"),
            f"Examples dir: {examples}" + (" (found)" if os.path.isdir(examples) else " (not found)"),
        ]
        if os.path.isdir(examples):
            files = sorted(glob.glob(os.path.join(examples, "*.py")))
            lines.append(f"Examples: {', '.join(os.path.basename(f) for f in files)}")

        updates = await asyncio.to_thread(check_updates)
        if updates:
            lines.append("")
            lines.extend(updates)

        return "\n".join(lines)
