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
    print("   You should see 9 tools (read_*, run, validate,")
    print("   pyxel_info, diff_frames).")
    print()
    print("4. (Optional) Publish the workflow skill into your host skill system:")
    print("       uvx pyxel-mcp publish-skill ~/.claude/skills/pyxel")
    print("   Then restart again. The skill activates on Pyxel-related prompts.")
    return 0


# Paths we refuse to rmtree no matter what `--force` says. They tend to
# host *other* config alongside skills (.mcp.json, CLAUDE.md, ssh keys,
# …) — a `publish-skill ~/.claude --force` typo would nuke the lot.
# Skill targets must be a dedicated subdirectory like `~/.claude/skills/pyxel`.
_HIGH_RISK_BASENAMES = frozenset({
    ".claude", ".cursor", ".codex", ".config", ".vscode",
    ".ssh", ".aws", ".gnupg", ".local",
})


def _is_dangerous_target(resolved: Path) -> bool:
    """True iff `resolved` (an already `.resolve(strict=False)`-ed Path)
    looks like a host-config root or filesystem root that we refuse to
    delete on the user's behalf."""
    home = Path.home().resolve()
    str_p = str(resolved)

    # Filesystem and OS-level roots
    if resolved == Path(resolved.anchor):  # "/" on POSIX, "C:\" on Windows
        return True
    if str_p in {"/Users", "/home", "/root", "/etc", "/var", "/usr", "/opt", "/tmp"}:
        return True

    # The user's home directory itself
    if resolved == home:
        return True

    # Common host-config roots directly under home
    if resolved.parent == home and resolved.name in _HIGH_RISK_BASENAMES:
        return True

    return False


def _publish_skill(target: str, *, force: bool, dry_run: bool) -> int:
    """Deploy the workflow skill (Layer 3) into a host skill directory.

    Safety guards (in order):
    1. `workflow_root()` must resolve — surfaces a friendly error otherwise.
    2. The target must not be a host-config root (`~/.claude`, `~/.cursor`,
       `~/.codex`, etc.). These are refused outright; only a dedicated
       subdir like `~/.claude/skills/pyxel` is accepted.
    3. The target must not be an existing file.
    4. An existing directory is overwritten only with `--force`, AND only
       if it already contains `SKILL.md` (i.e., looks like a previously
       published skill) or is empty. Otherwise we refuse.

    `dry_run` lists what would be copied without touching anything.
    """
    from pyxel_mcp.workflow import workflow_root

    try:
        src = workflow_root()
    except RuntimeError as e:
        print(
            f"Cannot publish — workflow content not available: {e}",
            file=sys.stderr,
        )
        return 3

    dst = Path(target).expanduser()
    resolved = dst.resolve(strict=False)

    if _is_dangerous_target(resolved):
        print(
            f"Refusing to publish into a high-risk path: {dst}\n"
            f"This looks like a host config root or filesystem root. "
            f"Use a skill-specific subdirectory instead, e.g. "
            f"~/.claude/skills/pyxel.",
            file=sys.stderr,
        )
        return 4

    if dst.exists() and dst.is_file():
        print(
            f"Target is a file, not a directory: {dst}",
            file=sys.stderr,
        )
        return 5

    if dst.is_dir():
        contents = [p for p in dst.iterdir() if not p.name.startswith(".DS_Store")]
        if not force:
            print(
                f"target dir already exists: {dst}\n"
                f"Pass --force to overwrite, or remove the directory manually.",
                file=sys.stderr,
            )
            return 2
        if contents and not (dst / "SKILL.md").is_file():
            print(
                f"Refusing to overwrite non-skill directory: {dst}\n"
                f"It does not contain SKILL.md — likely the wrong target. "
                f"Remove it manually if you really want to clear it.",
                file=sys.stderr,
            )
            return 6
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


if __name__ == "__main__":
    sys.exit(main())
