"""pyxel-mcp CLI entry point.

Subcommands:
- (default) / `serve` - start the MCP server
- `install`           - print client setup commands and the config snippet

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

_CLIENT_COMMANDS = [
    ("Claude Code", "claude mcp add --scope user pyxel -- uvx pyxel-mcp"),
    ("Codex CLI", "codex mcp add pyxel -- uvx pyxel-mcp"),
    ("Gemini CLI", "gemini mcp add pyxel uvx pyxel-mcp"),
]

_CLIENT_FILES = [
    ("Claude Code (project)", ".mcp.json in the project root"),
    ("Cursor", "~/.cursor/mcp.json"),
    ("Codex CLI", "~/.codex/config.toml as [mcp_servers.pyxel] with command/args"),
    (
        "VS Code",
        '.vscode/mcp.json under a top-level "servers" key with "type": "stdio"',
    ),
]


def _print_aligned(rows: list[tuple[str, str]]) -> None:
    width = max(len(name) for name, _ in rows) + 1
    for name, value in rows:
        print(f"   {name + ':':<{width}}  {value}")


def _print_install_guide() -> int:
    """Print client commands, the config snippet, and the verification step."""
    print("Pyxel MCP - installation guide")
    print("===============================")
    print()
    print("1. Register the server with one command:")
    print()
    _print_aligned(_CLIENT_COMMANDS)
    print()
    print("   Or add this stdio server to a client's config file:")
    print()
    print(textwrap.indent(_INSTALL_SNIPPET, "    "))
    print()
    _print_aligned(_CLIENT_FILES)
    print()
    print("2. Restart the client to load the server.")
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
    sub.add_parser("install", help="Print client setup commands and the config snippet")
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
