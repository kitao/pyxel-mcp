"""Sanity checks on instructions.md content."""

import os
import re

INSTRUCTIONS_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "src",
    "pyxel_mcp",
    "instructions.md",
)


def test_gen_bgm_calls_have_four_args():
    """Every gen_bgm() example in instructions.md uses the 2.9 signature."""
    with open(INSTRUCTIONS_PATH) as f:
        content = f.read()

    for match in re.finditer(r"gen_bgm\(([^)]*)\)", content):
        args = match.group(1)
        if "=" in args and "preset=" in args:
            # keyword form — must include transp= and instr= and seed=
            assert "transp" in args, f"missing transp in call: {match.group(0)}"
            assert "instr" in args, f"missing instr in call: {match.group(0)}"
            assert "seed" in args, f"missing seed in call: {match.group(0)}"
        else:
            # positional form — must have at least 4 commas-separated args
            commas = len([s for s in args.split(",") if s.strip()])
            assert commas >= 4, f"old-form gen_bgm call: {match.group(0)}"
