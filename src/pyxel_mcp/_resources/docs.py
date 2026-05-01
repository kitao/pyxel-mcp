"""Pyxel documentation files exposed as MCP resources, fetched live."""

import time
from urllib.request import urlopen

_BASE = "https://raw.githubusercontent.com/kitao/pyxel/main/docs"

_DOCS = {
    "api-reference": ("api-reference.md", "Pyxel API Reference"),
    "user-guide": ("user-guide.md", "Pyxel User Guide"),
    "mml-commands": ("mml-commands.md", "Pyxel MML Commands"),
    "pyxres-format": ("pyxres-format.md", ".pyxres File Format"),
}

# {url: (expires_at_unix, content_str)}
_CACHE: dict[str, tuple[float, str]] = {}
_TTL_SECONDS = 24 * 60 * 60  # 24h
_FETCH_TIMEOUT = 5  # seconds


def _fetch(url: str) -> str:
    with urlopen(url, timeout=_FETCH_TIMEOUT) as resp:
        return resp.read().decode("utf-8")


def _get(url: str) -> str:
    """Return cached content; refetch if expired or absent.

    On fetch failure, fall back to stale cache if present, else raise.
    """
    now = time.time()
    cached = _CACHE.get(url)
    if cached and cached[0] > now:
        return cached[1]

    try:
        content = _fetch(url)
        _CACHE[url] = (now + _TTL_SECONDS, content)
        return content
    except Exception:
        if cached:
            return cached[1]
        raise


def _make_reader(url):
    # Factory binds `url` into a fresh closure scope per call.
    # Same pattern as _resources/examples.py — FastMCP would
    # treat a function parameter as a URI placeholder.
    def _read() -> str:
        return _get(url)
    return _read


def register(mcp):
    for slug, (filename, title) in _DOCS.items():
        url = f"{_BASE}/{filename}"
        mcp.resource(
            f"pyxel://{slug}",
            name=title,
            description=f"Live-fetched Pyxel doc: {filename}",
            mime_type="text/markdown",
        )(_make_reader(url))
