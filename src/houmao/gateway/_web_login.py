"""Prepare the local browser login page and verify bounded OpenSSH proofs."""

from __future__ import annotations

from functools import cache
from html import escape
from importlib.resources import files
from string import Template

from houmao.gateway._access_sshsig import (
    TERMINAL_LOGIN_NAMESPACE as TERMINAL_LOGIN_NAMESPACE,
    WEB_LOGIN_NAMESPACE as WEB_LOGIN_NAMESPACE,
    sshsig_header,
)
from houmao.gateway.access import (
    MAX_ACCESS_DOCUMENT,
    GatewayAccessError,
    GatewayAccessPolicy,
    GatewayGrant,
)
from houmao.gateway.access_models import MAX_ADMIN_KEYS
from houmao.gateway.terminal_entry_contracts import TERMINAL_INTERACT_PATH, TERMINAL_LOGIN_PATH

WEB_LOGIN_PROOF_MAX_BYTES = MAX_ACCESS_DOCUMENT
_ARMOR_END = b"-----END SSH SIGNATURE-----"


@cache
def _load_page() -> tuple[Template, str]:
    """Read the login page and its script from the installed package."""

    package = files("houmao.gateway")
    return (
        Template(package.joinpath("_web_login.html").read_text(encoding="utf-8")),
        package.joinpath("_web_login.js").read_text(encoding="utf-8"),
    )


def render_web_login_page(nonce: str, *, agent_id: str = "") -> str:
    """Serve the login controls with an escaped agent name and CSP nonce."""

    return _render_login_page(
        nonce,
        agent_id=agent_id,
        title="Houmao Web Login",
        namespace=WEB_LOGIN_NAMESPACE,
        login_path="/v1/web/login",
        entry_path="/v1/web/enter",
        claim_header="X-Houmao-Web-Claim",
        ticket_location="query",
    )


def render_terminal_login_page(nonce: str, *, agent_id: str = "") -> str:
    """Serve the same browser login controls for terminal administrator entry."""

    return _render_login_page(
        nonce,
        agent_id=agent_id,
        title="Houmao Terminal Admin Login",
        namespace=TERMINAL_LOGIN_NAMESPACE,
        login_path=TERMINAL_LOGIN_PATH,
        entry_path=TERMINAL_INTERACT_PATH,
        claim_header="X-Houmao-Terminal-Claim",
        ticket_location="fragment",
    )


def _render_login_page(
    nonce: str,
    *,
    agent_id: str,
    title: str,
    namespace: str,
    login_path: str,
    entry_path: str,
    claim_header: str,
    ticket_location: str,
) -> str:
    """Bind the browser login script to one server-selected set of routes."""

    page, script = _load_page()
    return page.substitute(
        nonce=escape(nonce),
        agent_id=escape(agent_id),
        title=escape(title),
        namespace=escape(namespace),
        login_path=escape(login_path),
        entry_path=escape(entry_path),
        claim_header=escape(claim_header),
        ticket_location=escape(ticket_location),
        proof_limit=WEB_LOGIN_PROOF_MAX_BYTES,
        signature_limit=MAX_ADMIN_KEYS,
        script=script,
    )


def verify_web_login(policy: GatewayAccessPolicy, proofs: bytes, challenge: bytes) -> GatewayGrant:
    """Verify a signer with Web entry permission from a bounded batch of SSHSIG blocks."""

    return policy.verify_web_login(challenge, _proof_candidates(proofs))


def verify_terminal_login(
    policy: GatewayAccessPolicy, proofs: bytes, challenge: bytes
) -> GatewayGrant:
    """Verify a currently enrolled administrator using terminal-specific signatures."""

    return policy.verify_terminal_login(challenge, _proof_candidates(proofs))


def _proof_candidates(proofs: bytes) -> tuple[str, ...]:
    """Parse a bounded envelope of independently verifiable OpenSSH armor blocks."""

    if len(proofs) > WEB_LOGIN_PROOF_MAX_BYTES:
        raise GatewayAccessError(413, "proof_too_large")
    blocks = proofs.split(_ARMOR_END, maxsplit=MAX_ADMIN_KEYS + 1)
    if not 2 <= len(blocks) <= MAX_ADMIN_KEYS + 1 or blocks[-1].strip():
        raise GatewayAccessError(401, "invalid_proof")
    candidates = []
    for block in blocks[:-1]:
        try:
            candidates.append(sshsig_header(block.lstrip() + _ARMOR_END))
        except ValueError:
            continue
    return tuple(candidates)
