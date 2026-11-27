"""Serve the packaged browser terminal page and its explicitly listed assets."""

from __future__ import annotations

from functools import cache
from importlib.resources import files
from string import Template

from houmao.gateway.terminal_entry_contracts import (
    TERMINAL_INTERACT_PATH,
    TERMINAL_VIEW_PATH,
    GatewayTerminalEntryMode,
)

_ASSETS = {
    "terminal.js": "text/javascript",
    "terminal.css": "text/css",
    "xterm.mjs": "text/javascript",
    "xterm.css": "text/css",
    "addon-fit.mjs": "text/javascript",
}


@cache
def _terminal_template() -> Template:
    """Read the terminal template from the installed package."""

    return Template(files("houmao.gateway").joinpath("_tmux_terminal.html").read_text("utf-8"))


def render_terminal_page(mode: GatewayTerminalEntryMode) -> str:
    """Render one terminal page with its mode and gateway-relative entry path."""

    interactive = mode == "interact"
    return _terminal_template().substitute(
        mode=mode,
        label="Interactive" if interactive else "Read-only",
        entry_path=TERMINAL_INTERACT_PATH if interactive else TERMINAL_VIEW_PATH,
    )


@cache
def _read_asset(name: str) -> bytes:
    """Load a known asset from the installed package."""

    return files("houmao.gateway").joinpath("_terminal_assets", name).read_bytes()


def read_terminal_asset(name: str) -> tuple[bytes, str] | None:
    """Return the bytes and MIME type of a browser asset in the public allowlist."""

    media_type = _ASSETS.get(name)
    if media_type is None:
        return None
    return _read_asset(name), media_type
