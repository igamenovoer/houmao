"""Tests for the installed browser terminal resources and their public boundary."""

from __future__ import annotations

from hashlib import sha256
from importlib.resources import files

from houmao.gateway._tmux_terminal import read_terminal_asset, render_terminal_page


def test_terminal_pages_bind_their_mode_and_entry_path() -> None:
    """Render both entry points with their own stream prefix and shared local assets."""

    viewer = render_terminal_page("view")
    interactive = render_terminal_page("interact")

    assert 'data-mode="view" data-entry-path="/v1/terminal/view"' in viewer
    assert 'data-mode="interact" data-entry-path="/v1/admin/terminal/attach"' in interactive
    for page in (viewer, interactive):
        assert 'src="/v1/terminal/assets/terminal.js"' in page
        assert 'href="/v1/terminal/assets/xterm.css"' in page


def test_only_browser_assets_are_served() -> None:
    """Report expected MIME types and confine reads to explicit public resources."""

    for name in ("terminal.js", "xterm.mjs", "addon-fit.mjs"):
        assert read_terminal_asset(name)[1] == "text/javascript"
    for name in ("terminal.css", "xterm.css"):
        assert read_terminal_asset(name)[1] == "text/css"
    for name in ("", "../_web_login.js", "xterm.LICENSE", "vendor.sha256", "xterm.mjs.map"):
        assert read_terminal_asset(name) is None


def test_vendor_digests_match_all_module_and_license_files() -> None:
    """Verify the packaged bytes against the pinned upstream members."""

    assets = files("houmao.gateway").joinpath("_terminal_assets")
    recorded_names = set()
    for line in assets.joinpath("vendor.sha256").read_text("utf-8").splitlines():
        digest, name = line.split()
        assert sha256(assets.joinpath(name).read_bytes()).hexdigest() == digest
        recorded_names.add(name)
    assert recorded_names == {
        "xterm.mjs",
        "xterm.css",
        "xterm.LICENSE",
        "addon-fit.mjs",
        "addon-fit.LICENSE",
    }
