"""Prepare the local browser login page and verify bounded OpenSSH proofs."""

from __future__ import annotations

from functools import cache
from html import escape
from importlib.resources import files
from string import Template

from houmao.gateway._access_sshsig import (
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

    page, script = _load_page()
    return page.substitute(
        nonce=escape(nonce),
        agent_id=escape(agent_id),
        namespace=WEB_LOGIN_NAMESPACE,
        proof_limit=WEB_LOGIN_PROOF_MAX_BYTES,
        signature_limit=MAX_ADMIN_KEYS,
        script=script,
    )


def verify_web_login(policy: GatewayAccessPolicy, proofs: bytes, challenge: bytes) -> GatewayGrant:
    """Verify a signer with Web entry permission from a bounded batch of SSHSIG blocks."""

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
    return policy.verify_web_login(challenge, tuple(candidates))
