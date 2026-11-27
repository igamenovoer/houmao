"""Tests for the installed browser terminal resources and their public boundary."""

from __future__ import annotations

from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from houmao.gateway._tmux_terminal import read_terminal_asset, render_terminal_page

_ORIGIN = "http://127.0.0.1:43123"
_INTERACT = "/v1/admin/terminal/attach"
_BEARER = "a" * 43


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


def _browser_entry(**scenario: object) -> dict[str, object]:
    """Run the bundled entry module with a controlled same-origin browser environment."""

    bun = shutil.which("bun")
    if bun is None:
        pytest.skip("Bun is required for the hermetic browser entry check")
    driver = Path(__file__).with_name("tmux_terminal_entry_driver.js")
    asset = files("houmao.gateway").joinpath("_terminal_assets", "terminal.js")
    parameters = {"url": f"{_ORIGIN}{_INTERACT}", "entryPath": _INTERACT, **scenario}
    result = subprocess.run(
        [bun, str(driver), str(asset), json.dumps(parameters)],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    evidence: dict[str, object] = json.loads(result.stdout)
    return evidence


def test_bare_interactive_page_redeems_a_same_origin_receipt() -> None:
    """Request the live admin ticket anonymously and use its exact WebSocket stream."""

    result = _browser_entry(
        status=200,
        receipt={"mode": "interact", "url": f"{_ORIGIN}{_INTERACT}#ticket={_BEARER}"},
    )

    assert result["requests"] == [
        {
            "url": f"{_INTERACT}/ticket",
            "method": "POST",
            "mode": "same-origin",
            "credentials": "omit",
            "cache": "no-store",
            "redirect": "error",
        }
    ]
    assert result["sockets"] == [f"ws://127.0.0.1:43123{_INTERACT}/stream"]
    assert result["frames"] == [{"type": "grant", "ticket": _BEARER}]
    assert result["replaced"] == []


@pytest.mark.parametrize(
    ("status_code", "error_code", "message", "destination"),
    [
        (401, "proof_required", "Administrator sign-in required", f"{_INTERACT}/login"),
        (403, "insufficient_authority", "Administrator sign-in required", f"{_INTERACT}/login"),
        (403, "direct_terminal_access_required", "Terminal unavailable", _INTERACT),
        (503, "policy_unavailable", "Terminal unavailable", _INTERACT),
    ],
)
def test_interactive_page_uses_live_policy_response(
    status_code: int, error_code: str, message: str, destination: str
) -> None:
    """Use live proof requirements and display policy failures without connecting."""

    result = _browser_entry(status=status_code, receipt={"detail": {"error_code": error_code}})
    assert result["message"] == message
    assert result["action"] == destination
    assert result["sockets"] == []


@pytest.mark.parametrize(
    ("mode", "url"),
    [
        ("view", f"{_ORIGIN}{_INTERACT}#ticket={_BEARER}"),
        ("interact", f"http://127.0.0.1:43124{_INTERACT}#ticket={_BEARER}"),
        ("interact", f"{_ORIGIN}/v1/terminal/view#ticket={_BEARER}"),
        ("interact", f"{_ORIGIN}{_INTERACT}?ticket={_BEARER}"),
    ],
)
def test_interactive_page_rejects_a_mismatched_receipt(mode: str, url: str) -> None:
    """Reject wrong mode, origin, or path and require the grant in the fragment."""

    result = _browser_entry(status=200, receipt={"mode": mode, "url": url})
    assert result["message"] == "Terminal unavailable"
    assert result["action"] == _INTERACT
    assert result["sockets"] == []


def test_interactive_fragment_is_redeemed_without_a_new_ticket_request() -> None:
    """Use the original grant from the CLI or keyed login and scrub the URL."""

    result = _browser_entry(url=f"{_ORIGIN}{_INTERACT}#ticket={_BEARER}")
    assert result["requests"] == []
    assert result["replaced"] == [_INTERACT]
    assert result["frames"] == [{"type": "grant", "ticket": _BEARER}]
