"""Render the public gateway summary from its display fields."""

from __future__ import annotations

from functools import cache
from html import escape
from importlib.resources import files
from string import Template


@cache
def _load_page() -> Template:
    """Load the dashboard template from the gateway package."""

    return Template(files("houmao.gateway").joinpath("_dashboard.html").read_text(encoding="utf-8"))


def render_dashboard(
    *,
    agent: str,
    backend: str,
    mode: str,
    gateway_health: str,
    web_availability: str,
    web_entry_path: str | None,
    web_entry_reason: str,
) -> str:
    """Render an escaped dashboard and the gateway's Web entry action."""

    if web_entry_path is None:
        web_entry = f"<p>{escape(web_entry_reason)}</p>"
    else:
        web_entry = f'<a href="{escape(web_entry_path)}">Open agent Web UI</a>'
    return _load_page().substitute(
        agent=escape(agent),
        backend=escape(backend),
        mode=escape(mode),
        gateway_health=escape(gateway_health),
        web_availability=escape(web_availability),
        web_entry=web_entry,
    )
