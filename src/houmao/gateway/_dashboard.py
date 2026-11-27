"""Render the public gateway summary from its display fields."""

from __future__ import annotations

from functools import cache
from html import escape
from importlib.resources import files
from string import Template
from typing import Literal


@cache
def _load_page() -> Template:
    """Load the dashboard template from the gateway package."""

    return Template(files("houmao.gateway").joinpath("_dashboard.html").read_text(encoding="utf-8"))


def render_dashboard(
    *,
    agent: str,
    backend: str,
    mode: str,
    admin_mode: Literal["open", "keyed", "unavailable"],
    gateway_health: str,
    web_availability: str,
    web_entry_path: str | None,
    web_entry_reason: str,
    terminal_availability: str,
    terminal_view_path: str | None,
    terminal_interact_path: str | None,
    terminal_entry_reason: str,
) -> str:
    """Render escaped public details and links to available browser entry points."""

    if web_entry_path is None or admin_mode == "unavailable":
        web_entry = f"<p>{escape(web_entry_reason)}</p>"
    else:
        guidance = (
            "The gateway opens the native Web UI directly."
            if admin_mode == "open"
            else "The gateway asks you to sign in before opening the native Web UI."
        )
        web_entry = (
            f'<a href="{escape(web_entry_path)}">Open agent Web UI</a><p>{escape(guidance)}</p>'
        )
    if terminal_view_path is None:
        terminal_entry = f"<p>{escape(terminal_entry_reason)}</p>"
    else:
        terminal_links = [f'<a href="{escape(terminal_view_path)}">View tmux terminal</a>']
        if terminal_interact_path is not None:
            terminal_links.append(
                f'<a href="{escape(terminal_interact_path)}">Interact with tmux</a>'
            )
        console = {
            "headless": "Headless console. ",
            "service": "Supervisor console. ",
            "web": "Supervisor console. ",
        }.get(mode, "")
        guidance = {
            "open": "The gateway opens the interactive terminal directly.",
            "keyed": "Sign in with an enrolled administrator key to interact.",
            "unavailable": "Gateway administrator policy is unavailable.",
        }[admin_mode]
        terminal_entry = (
            f'<div class="action-links">{"".join(terminal_links)}</div>'
            f"<p>{console}Viewing is read-only. {guidance}</p>"
        )
    return _load_page().substitute(
        agent=escape(agent),
        backend=escape(backend),
        mode=escape(mode),
        admin_mode=escape(admin_mode.capitalize()),
        gateway_health=escape(gateway_health),
        web_availability=escape(web_availability),
        web_entry=web_entry,
        terminal_availability=escape(terminal_availability),
        terminal_entry=terminal_entry,
    )
