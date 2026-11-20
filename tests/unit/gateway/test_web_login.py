"""Exercise the packaged browser page, shell command, and enrolled OpenSSH proof."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

import pytest

from houmao.gateway._web_login import (
    WEB_LOGIN_NAMESPACE,
    WEB_LOGIN_PROOF_MAX_BYTES,
    render_web_login_page,
    verify_web_login,
)
from houmao.gateway.access import (
    SSHSIG_NAMESPACE,
    GatewayAccessError,
    GatewayAccessPolicy,
    GatewayAccessStore,
    GatewayAdminKey,
    GatewayLaunchSeed,
    GatewayOwner,
    GatewayTarget,
    load_gateway_signer,
    sign_sshsig,
)
from houmao.gateway.access_models import MAX_ADMIN_KEYS

CHALLENGE = rb"""{"issuer":"http://127.0.0.1:12345","value":"' \u001b $(touch signed-text)"}"""
ISSUER = "http://127.0.0.1:12345"
ATTEMPT = "sample_attempt"


def _require(*commands: str) -> None:
    """Skip command interoperation when the local executable is unavailable."""

    for command in commands:
        if not shutil.which(command):
            pytest.skip(f"{command} required")


def _keygen(path: Path) -> str:
    """Generate a disposable Ed25519 identity and return its verification key."""

    _require("ssh-keygen")
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(path)],
        check=True,
        capture_output=True,
    )
    return path.with_name(path.name + ".pub").read_text().strip()


def _policy(tmp_path: Path, public_key: str) -> GatewayAccessPolicy:
    """Enroll a single operator and provision a distinct current self identity."""

    owner = GatewayOwner(agent_id="agent", context_id="context")
    store = GatewayAccessStore.from_root(tmp_path / "access", owner)
    store.initialize(
        GatewayLaunchSeed(
            admin_keys=(GatewayAdminKey(principal="operator", public_key=public_key),)
        )
    )
    store.provision_self("generation")
    return GatewayAccessPolicy(
        store=store,
        target=lambda: GatewayTarget(owner=owner, incarnation="generation"),
        current_self=lambda: store.load_self("generation"),
    )


def _stock_sign(path: Path, message: bytes = CHALLENGE, scope: str = WEB_LOGIN_NAMESPACE) -> bytes:
    """Sign challenge bytes on stdin with an unmodified OpenSSH executable."""

    return subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(path), "-n", scope],
        check=True,
        input=message,
        capture_output=True,
    ).stdout


def _command(key_path: str) -> str:
    """Run the page's packaged command generator without browser or network dependencies."""

    _require("bun")
    page = render_web_login_page("test-nonce", agent_id="<operator>")
    script = page.split('<script type="module" nonce="test-nonce">\n', 1)[1]
    script = script.split("initializeWebLogin();\n", 1)[0]
    command = f"""
const limits = {
        json.dumps(
            {
                "namespace": WEB_LOGIN_NAMESPACE,
                "proofLimit": WEB_LOGIN_PROOF_MAX_BYTES,
                "signatureLimit": MAX_ADMIN_KEYS,
            }
        )
    };
const attempt = {
        json.dumps(
            {
                "attempt_id": ATTEMPT,
                "challenge": base64.urlsafe_b64encode(CHALLENGE).decode().rstrip("="),
                "claim_secret": "tab-only-secret",
            }
        )
    };
console.log(signingCommand(attempt, {json.dumps(key_path)}, "{ISSUER}", limits));
"""
    return subprocess.run(
        ["bun", "-e", script + command], check=True, capture_output=True, text=True
    ).stdout


def _fake_curl(tmp_path: Path) -> dict[str, str]:
    """Capture the submission received by curl and return a chosen HTTP outcome."""

    shim = tmp_path / "curl"
    shim.write_text(
        "#!/bin/sh\n"
        'printf \'%s\\n\' "$@" > "$CURL_ARGUMENTS"\n'
        'cat > "$CURL_PROOF"\n'
        "printf '%s' \"$CURL_RESULT\"\n"
    )
    shim.chmod(0o700)
    environment = os.environ.copy()
    environment.pop("SSH_AUTH_SOCK", None)
    environment.update(
        PATH=f"{tmp_path}:{os.environ['PATH']}",
        CURL_ARGUMENTS=str(tmp_path / "curl-arguments"),
        CURL_PROOF=str(tmp_path / "curl-proof"),
        CURL_RESULT="204",
        TMPDIR=str(tmp_path),
    )
    return environment


def _check_curl_arguments(tmp_path: Path) -> None:
    """Verify direct POST to the callback with neither redirects nor added credentials."""

    arguments = (tmp_path / "curl-arguments").read_text().splitlines()
    assert arguments == [
        "-q",
        "--noproxy",
        "*",
        "--proto",
        "=http",
        "--silent",
        "--output",
        "/dev/null",
        "--connect-timeout",
        "5",
        "--max-time",
        "15",
        "--write-out",
        "%{http_code}",
        "--request",
        "POST",
        "--header",
        "Content-Type: text/plain",
        "--data-binary",
        "@-",
        f"{ISSUER}/v1/web/login/{ATTEMPT}/prove",
    ]


def test_login_page_escapes_identity_and_applies_nonce() -> None:
    """Render agent text and the two nonce-protected inline elements."""

    page = render_web_login_page("expected-nonce", agent_id="<operator>&admin")
    assert '<p id="login-target">&lt;operator&gt;&amp;admin</p>' in page
    assert page.count('nonce="expected-nonce"') == 2
    assert 'id="command-section" hidden' in page
    assert 'aria-describedby="key-path-help"' in page
    assert "Surrounding whitespace is trimmed." in page
    assert "claim_secret" in page
    assert "localStorage" not in page and "sessionStorage" not in page


def test_approval_accepts_stock_signatures_after_invalid_candidates(tmp_path: Path) -> None:
    """Select an enrolled valid signature even after malformed and unenrolled candidates."""

    admin = tmp_path / "admin"
    other = tmp_path / "other"
    policy = _policy(tmp_path, _keygen(admin))
    _keygen(other)
    bad_armor = b"-----BEGIN SSH SIGNATURE-----\n!\n-----END SSH SIGNATURE-----\n"
    wrong_scope = _stock_sign(admin, scope=SSHSIG_NAMESPACE)
    proof = bad_armor + _stock_sign(other) + wrong_scope + _stock_sign(admin)
    grant = verify_web_login(policy, proof, CHALLENGE)
    assert grant.role == "admin" and grant.principal == "operator"
    assert policy.revalidate(grant)
    assert grant.key_id is not None
    policy.remove_key(grant, grant.key_id)
    assert not policy.revalidate(grant)


def test_approval_refuses_wrong_scope_target_self_and_oversized_batch(tmp_path: Path) -> None:
    """Require bounded proof for the exact browser login by one currently enrolled key."""

    admin = tmp_path / "admin"
    policy = _policy(tmp_path, _keygen(admin))
    self_signer = load_gateway_signer(policy.store.self_signer_path("generation"))
    signature = _stock_sign(admin)
    for proof, challenge, status in (
        (_stock_sign(admin, scope=SSHSIG_NAMESPACE), CHALLENGE, 401),
        (signature, CHALLENGE + b"!", 401),
        (sign_sshsig(self_signer, CHALLENGE, namespace=WEB_LOGIN_NAMESPACE), CHALLENGE, 401),
        (signature + b"extra field", CHALLENGE, 401),
        (signature * (MAX_ADMIN_KEYS + 1), CHALLENGE, 401),
        (b"x" * (WEB_LOGIN_PROOF_MAX_BYTES + 1), CHALLENGE, 413),
    ):
        with pytest.raises(GatewayAccessError) as denied:
            verify_web_login(policy, proof, challenge)
        assert denied.value.status_code == status


def test_explicit_command_signs_with_literal_path_and_direct_curl(tmp_path: Path) -> None:
    """Quote whitespace, leading tilde, and shell metacharacters without interpretation."""

    name = """~operator's `touch backtick` $(touch interpreted) "$HOME" key"""
    policy = _policy(tmp_path, _keygen(tmp_path / name))
    environment = _fake_curl(tmp_path)
    command = _command(name)
    result = subprocess.run(
        ["sh", "-c", command], cwd=tmp_path, env=environment, capture_output=True, check=True
    )
    _check_curl_arguments(tmp_path)
    assert result.stdout == b"Login approved. Return to the browser.\n"
    proof = (tmp_path / "curl-proof").read_bytes()
    assert policy.revalidate(verify_web_login(policy, proof, CHALLENGE))
    assert not any(
        (tmp_path / name).exists() for name in ("backtick", "interpreted", "signed-text")
    )
    assert "tab-only-secret" not in command
    assert name.encode() not in proof
    environment["CURL_RESULT"] = "302"
    refused = subprocess.run(
        ["sh", "-c", command], cwd=tmp_path, env=environment, capture_output=True, check=False
    )
    assert refused.returncode != 0
    assert b"Select an enrolled key file" in refused.stderr


def test_absolute_key_path_ignores_surrounding_whitespace() -> None:
    """Classify the trimmed value as an absolute path and keep interior spaces."""

    path = "/home/operator/key files/admin_ed25519"
    command = _command(f"  {path}\t ")
    assert f"-f '{path}'" in command


@pytest.mark.parametrize("key_path", ["", " \t "])
def test_blank_path_submits_all_supported_agent_signatures(tmp_path: Path, key_path: str) -> None:
    """Use an isolated SSH agent holding an unenrolled and an enrolled key."""

    _require("ssh-agent", "ssh-add")
    admin = tmp_path / "admin"
    other = tmp_path / "other"
    policy = _policy(tmp_path, _keygen(admin))
    _keygen(other)
    environment = _fake_curl(tmp_path)
    command = _command(key_path)
    with tempfile.TemporaryDirectory(prefix="houmao-web-login-") as socket_root:
        socket_path = Path(socket_root) / "agent"
        environment["SSH_AUTH_SOCK"] = str(socket_path)
        agent = subprocess.Popen(
            ["ssh-agent", "-D", "-a", str(socket_path)],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(100):
                if socket_path.is_socket():
                    break
                time.sleep(0.01)
            subprocess.run(
                ["ssh-add", str(other), str(admin)],
                env=environment,
                check=True,
                capture_output=True,
            )
            subprocess.run(["sh", "-c", command], env=environment, check=True, capture_output=True)
        finally:
            agent.terminate()
            agent.wait(timeout=5)
    proof = (tmp_path / "curl-proof").read_bytes()
    assert proof.count(b"-----BEGIN SSH SIGNATURE-----") == 2
    assert policy.revalidate(verify_web_login(policy, proof, CHALLENGE))
    assert all(path.is_file() or path.name == "access" for path in tmp_path.iterdir())
    _check_curl_arguments(tmp_path)


def test_blank_path_without_agent_offers_safe_retry(tmp_path: Path) -> None:
    """Advise local key selection without sending an empty approval callback."""

    _require("ssh-add")
    environment = _fake_curl(tmp_path)
    result = subprocess.run(
        ["sh", "-c", _command("")], env=environment, capture_output=True, check=False
    )
    assert result.returncode != 0
    assert b"Select an enrolled key file" in result.stderr
    assert not (tmp_path / "curl-proof").exists()
