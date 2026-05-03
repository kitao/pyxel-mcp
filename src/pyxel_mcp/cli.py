"""pyxel-mcp CLI entry point.

Subcommands:
- (default) / `serve` — start the FastMCP server
- `install`            — print the MCP-config snippet + onboarding guide
- `publish-skill DIR`  — copy the workflow skill into a host skill dir

The default behaviour (no subcommand) preserves the historical entry
point: `uvx pyxel-mcp` still starts the server.
"""
from __future__ import annotations
import argparse
import shutil
import sys
import textwrap
from pathlib import Path


_INSTALL_SNIPPET = textwrap.dedent("""\
    {
      "mcpServers": {
        "pyxel": {
          "command": "uvx",
          "args": ["pyxel-mcp"]
        }
      }
    }""")


def _print_install_guide() -> int:
    """Option C — print the snippet and onboarding steps for the user to
    copy/paste. We deliberately don't edit any host config file here:
    different hosts (Claude Code, Cursor, Codex CLI) keep their config
    in different places, and silent edits are a foot-gun.
    """
    indented = textwrap.indent(_INSTALL_SNIPPET, "    ")
    print("Pyxel MCP — installation guide")
    print("==============================")
    print()
    print("1. Add this snippet to your MCP-compatible client's config:")
    print()
    print("   Claude Code:  ~/.claude/.mcp.json   (or per-project .mcp.json)")
    print("   Cursor:       ~/.cursor/mcp.json")
    print("   Codex CLI:    ~/.codex/mcp.json")
    print()
    print(indented)
    print()
    print("2. Restart your client to load the server.")
    print()
    print("3. Verify it loaded — ask your client:")
    print('       "What tools does pyxel-mcp expose?"')
    print("   You should see 17 tools across two layers")
    print("   (read_*, judge_*, run, validate, ...).")
    print()
    print("4. (Optional) Publish the workflow skill into your host skill system:")
    print("       uvx pyxel-mcp publish-skill ~/.claude/skills/pyxel")
    print("   Then restart again. The skill activates on Pyxel-related prompts.")
    return 0


def _publish_skill(target: str, *, force: bool, dry_run: bool) -> int:
    """Deploy the workflow skill (Layer 3) into a host skill directory.

    `force` removes an existing target before copying. `dry_run` lists
    the files that would be copied without touching the filesystem.
    """
    from pyxel_mcp.workflow import workflow_root

    src = workflow_root()
    dst = Path(target).expanduser()

    if dst.exists():
        if not force:
            print(
                f"target dir already exists: {dst}\n"
                f"Pass --force to overwrite, or remove the directory manually.",
                file=sys.stderr,
            )
            return 2
        if not dry_run:
            shutil.rmtree(dst)

    if dry_run:
        files = sorted(p for p in src.rglob("*") if p.is_file())
        print(f"[dry-run] would copy {len(files)} files from {src} to {dst}:")
        for p in files:
            print(f"  {p.relative_to(src)}")
        return 0

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)
    print(f"Skill published to {dst}")
    print("Restart your client to activate.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyxel-mcp",
        description="MCP server for Pyxel — run, verify, iterate on retro-game scripts.",
    )
    sub = parser.add_subparsers(dest="cmd", title="commands")

    sub.add_parser("serve", help="Start the MCP server (default if no command)")
    sub.add_parser("install", help="Print MCP-config snippet + onboarding guide")

    pub = sub.add_parser(
        "publish-skill",
        help="Copy the workflow skill into a host skill directory",
    )
    pub.add_argument("target_dir", help="Destination dir (e.g., ~/.claude/skills/pyxel)")
    pub.add_argument("--force", action="store_true", help="Overwrite if target exists")
    pub.add_argument("--dry-run", action="store_true", help="List intended copies; do nothing")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. `argv=None` reads from sys.argv (real CLI use).

    Returns the process exit code; the script wrapper translates this
    into the OS exit status.
    """
    args = _build_parser().parse_args(argv)

    if args.cmd in (None, "serve"):
        # Lazy import: starting the server is heavy, importing it for
        # every CLI subcommand call would balloon startup time.
        from pyxel_mcp import server
        server.main()
        return 0
    if args.cmd == "install":
        return _print_install_guide()
    if args.cmd == "publish-skill":
        return _publish_skill(
            args.target_dir, force=args.force, dry_run=args.dry_run,
        )
    return 0
