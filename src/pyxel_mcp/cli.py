"""pyxel-mcp CLI entry point.

Subcommands:
- (default) / `serve` - start the FastMCP server
- `install`           - print the MCP config snippet and onboarding guide

The default behaviour (no subcommand) preserves the historical entry point:
`uvx pyxel-mcp` starts the server.
"""
from __future__ import annotations
import argparse
import sys
import textwrap


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
    """Print the snippet and onboarding steps for MCP clients."""
    indented = textwrap.indent(_INSTALL_SNIPPET, "    ")
    print("Pyxel MCP - installation guide")
    print("===============================")
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
    print("3. Verify it loaded - ask your client:")
    print('       "What tools does pyxel-mcp expose?"')
    print("   You should see 8 tools: run, validate, pyxel_info,")
    print("   read_palette, read_image, read_tilemap, read_audio,")
    print("   and diff_frames.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyxel-mcp",
        description="MCP server for Pyxel - headless observation tools.",
    )
    sub = parser.add_subparsers(dest="cmd", title="commands")
    sub.add_parser("serve", help="Start the MCP server (default if no command)")
    sub.add_parser("install", help="Print MCP config snippet and onboarding guide")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. `argv=None` reads from sys.argv."""
    args = _build_parser().parse_args(argv)

    if args.cmd in (None, "serve"):
        from pyxel_mcp import server
        server.main()
        return 0
    if args.cmd == "install":
        return _print_install_guide()
    return 0


if __name__ == "__main__":
    sys.exit(main())
