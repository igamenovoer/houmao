"""Exercise the direct versioned mount between separately owned managed agents."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from click.testing import CliRunner
import pytest

from houmao.agents.realm_controller.backends.dsh_web import DshWebSession
from houmao.agents.realm_controller.backends.dsh_web_file_mount import QUALIFIED_BUILD
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.gateway_service import create_app
from houmao.agents.realm_controller.models import RelaunchChatSessionSelection
from houmao.gateway.deployment import GatewayEndpointDescriptor
from houmao.srv_ctrl.commands.main import cli
from tests.fixtures.gateway_access import fixture_admin_key
from tests.integration.agents.dsh.conftest import ControlledModelGate
from tests.integration.agents.dsh.web.conftest import call_native_request
from tests.integration.agents.dsh.web.refresh_model import controlled_skill_model
from tests.integration.agents.dsh.web.test_gateway_native import _runtime, _stop
from tests.integration.agents.dsh.web.test_refresh_gateway import _serve
from tests.integration.agents.realm_controller.test_gateway_https_access import (
    _PeerAccount,
    _provision_peer_account,
)

_TARGET = "versioned-skills-target"
_PRINCIPAL = "versioned-skills-peer"


def _coordinates(url: str, descriptor: GatewayEndpointDescriptor) -> tuple[str, ...]:
    """Select the caller's exact remote target and ingress before using proof."""

    return (
        "--url",
        url,
        "--context-id",
        descriptor.target.owner.context_id,
        "--generation",
        descriptor.target.incarnation,
        "--presence",
        descriptor.presence_id,
    )


def _owner_cli(*arguments: str, code: int = 0) -> dict[str, Any]:
    """Run the target-owner CLI against the actual fixture policy and listener."""

    result = CliRunner().invoke(
        cli, ["--print-json", "agents", "single", "--agent-id", _TARGET, *arguments]
    )
    assert result.exit_code == code, (result.output, result.exception)
    return json.loads(result.output)


def _peer_file_cli(
    peer: _PeerAccount, coordinates: tuple[str, ...], source: str, *arguments: str
) -> subprocess.CompletedProcess[str]:
    """Use the second account's configured signer and verified direct endpoint."""

    return peer.python(
        "cli",
        "--print-json",
        "agents",
        "single",
        "--agent-id",
        _TARGET,
        "files",
        *coordinates,
        "--source-agent-id",
        source,
        *arguments,
        check=False,
    )


def _peer_json(
    peer: _PeerAccount, coordinates: tuple[str, ...], source: str, *arguments: str
) -> dict[str, Any]:
    """Decode a successful command run with the enrolled peer identity."""

    result = _peer_file_cli(peer, coordinates, source, *arguments)
    assert result.returncode == 0, (result.stdout, result.stderr)
    return json.loads(result.stdout)


def _wait_native(backend: DshWebSession, operation_id: str) -> None:
    """Join the exact native turn created explicitly by the fixture."""

    client = backend._client()
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        receipt = client.receipt(backend.state.web_identity, operation_id)
        if receipt and receipt["status"] == "terminal":
            assert receipt["result"] == "completed", receipt
            return
        time.sleep(0.02)
    raise AssertionError("Controlled native work did not finish")


def test_cross_account_versioned_files_use_the_target_gateway(
    tmp_path: Path,
    dsh_executable: Path,
    isolated_tmux: Path,
    monkeypatch: pytest.MonkeyPatch,
    controlled_model_gate: ControlledModelGate,
) -> None:
    """Publish a peer-authored revision while the native owner preserves its conversation."""

    peer_user = os.environ.get("HOUMAO_TEST_PEER_USER")
    if not peer_user:
        pytest.skip("Set HOUMAO_TEST_PEER_USER to an existing account accessible with sudo -n -u")
    version = subprocess.check_output([str(dsh_executable), "--version"], text=True).strip()
    if version != QUALIFIED_BUILD:
        pytest.skip(f"Versioned Web skills qualify DSH {QUALIFIED_BUILD}")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "owner"))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._build_provider_start_launch_plan_for_relaunch",
        lambda current: current.launch_plan,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._activate_hook_observation_for_controller",
        lambda **kwargs: kwargs["launch_plan"],
    )
    with (
        _provision_peer_account(peer_user) as (peer, public),
        controlled_skill_model(read_asset=True, hold_first=controlled_model_gate) as model,
    ):
        source = str(public["logical_agent_id"])
        runtime, backend = _runtime(
            tmp_path,
            dsh_executable,
            model.endpoint,
            monkeypatch,
            isolated_tmux,
            agent_id=_TARGET,
            managed_web_skills=True,
        )
        selected = backend
        try:
            mount = backend.skill_file_mount()
            assert mount is not None
            mounted = mount.storage.describe()
            base = mounted.published_commit
            mount_id = mounted.mount_id
            assert isolated_tmux != peer.root / "tmux.sock"
            assert peer.run("test", "-r", str(mount.storage.root), check=False).returncode == 1
            peer.run(
                sys.executable,
                "-c",
                "import sys; from houmao.agents.realm_controller.registry_storage import "
                "load_managed_agent_record_by_agent_id; "
                "record = load_managed_agent_record_by_agent_id(sys.argv[1]); "
                "assert record is not None and record.gateway is None",
                source,
            )
            admin_key, admin_secret = fixture_admin_key(tmp_path, "versioned-owner")
            admin_public = tmp_path / "admin.pub"
            admin_public.write_text(admin_key.public_key)
            peer_public = tmp_path / "peer.pub"
            peer_public.write_text(str(public["public_key"]))
            identity = dict(backend.state.web_identity)
            with _serve(
                create_app(runtime=runtime),
                bind=lambda port: runtime.set_listener(host="127.0.0.1", port=port),
            ) as (url, _port):
                runtime.start()
                descriptor = GatewayClient(base_url=url).describe_endpoint()
                coordinates = _coordinates(url, descriptor)
                _owner_cli(
                    "access",
                    "admin-add",
                    *coordinates,
                    "--first",
                    "--signer",
                    str(admin_secret),
                    "--principal",
                    admin_key.principal,
                    "--public-key",
                    str(admin_public),
                )
                _owner_cli(
                    "access",
                    "principal-add",
                    _PRINCIPAL,
                    "--kind",
                    "agent",
                    "--label",
                    "Versioned skills peer",
                    "--logical-agent-id",
                    source,
                )
                _owner_cli(
                    "access", "credential-enroll", _PRINCIPAL, "--public-key", str(peer_public)
                )
                for action in ("files.read", "files.edit"):
                    _owner_cli("access", "grant", _PRINCIPAL, mounted.resource, action)
                mounts = _peer_json(peer, coordinates, source, "mounts")
                assert mounts["mounts"] == [mounted.model_dump(mode="json")]
                peer.run(
                    "sh",
                    "-c",
                    'printf "%s" "$1" > "$2"',
                    "write-fixture",
                    "---\nname: alpha\ndescription: Peer authored skill\n---\nPeer body\n",
                    str(peer.root / "SKILL.md"),
                )
                peer.run(
                    "sh",
                    "-c",
                    'printf "%s" "$1" > "$2"',
                    "write-fixture",
                    "Peer asset\n",
                    str(peer.root / "asset.txt"),
                )
                selector = ("--mount", mount_id)

                def candidate(message: str) -> dict[str, Any]:
                    """Author a candidate entirely through the second account's file client."""

                    lease = _peer_json(
                        peer,
                        coordinates,
                        source,
                        *selector,
                        "lease",
                        "open",
                        "--expected-base",
                        base,
                    )
                    assert lease["actor"]["logical_agent_id"] == source
                    draft = (*selector, "--draft", lease["draft_id"])
                    for filename in ("SKILL.md", "asset.txt"):
                        _peer_json(
                            peer,
                            coordinates,
                            source,
                            *draft,
                            "write",
                            f"alpha/{filename}",
                            "--from-file",
                            str(peer.root / filename),
                        )
                    return _peer_json(
                        peer, coordinates, source, *draft, "commit", "--message", message
                    )

                first = candidate("Peer writes alpha")
                stale = candidate("Peer saves another candidate on the old base")
                for receipt in (first, stale):
                    assert receipt["author"]["kind"] == "agent"
                    assert receipt["author"]["principal_id"] == _PRINCIPAL
                    assert receipt["author"]["logical_agent_id"] == source
                    assert receipt["committer"] == _TARGET
                assert _peer_json(peer, coordinates, source, *selector, "list")["entries"] == []
                denied = _peer_file_cli(
                    peer,
                    coordinates,
                    source,
                    *selector,
                    "push",
                    first["commit_id"],
                    "--expected-base",
                    base,
                    "--operation-id",
                    "unauthorized-peer",
                )
                assert denied.returncode == 1 and "HTTP 403" in denied.stderr
                owner = ("files", *coordinates, "--signer", str(admin_secret), *selector)
                native = backend._client()
                native.prompt(
                    identity,
                    "hold this independent model turn",
                    operation_id="busy-turn",
                    deadline_epoch_ms=int(time.time() * 1000) + 10000,
                )
                try:
                    assert controlled_model_gate.entered.wait(5)
                    busy = _owner_cli(
                        *owner,
                        "push",
                        first["commit_id"],
                        "--expected-base",
                        base,
                        "--operation-id",
                        "busy-push",
                        code=1,
                    )
                    assert busy["outcome"] == "busy" and busy["published_commit"] is None
                    assert mount.projection.published_marker() == base
                finally:
                    controlled_model_gate.release.set()
                _wait_native(backend, "busy-turn")
                cursor = native.conversation(identity)["current_cursor"]
                pushed = _owner_cli(
                    *owner,
                    "push",
                    first["commit_id"],
                    "--expected-base",
                    base,
                    "--operation-id",
                    "publish",
                )
                assert (
                    pushed["published_commit"] == pushed["effective_commit"] == first["commit_id"]
                )
                assert pushed["publisher"]["kind"] == "operator"
                assert pushed["publisher"]["principal_id"] != _PRINCIPAL
                assert pushed["native_ready"] and pushed["native_settled"]
                assert native.conversation(identity)["current_cursor"] == cursor
                assert len(model.requests) == 1
                status = _peer_json(peer, coordinates, source, *selector, "status", "publish")
                assert status == pushed
                stale_push = _owner_cli(
                    *owner,
                    "push",
                    stale["commit_id"],
                    "--expected-base",
                    base,
                    "--operation-id",
                    "stale-push",
                    code=1,
                )
                assert stale_push["outcome"] == "conflict"
                history = _peer_json(peer, coordinates, source, *selector, "history")
                assert history["commits"][0]["author"] == first["author"]
                assert first["commit_id"] == history["commits"][0]["commit_id"]
                skills = call_native_request(
                    native, "skills/list", {"request": {"sessionId": identity["native_session_id"]}}
                )
                assert any(row["name"] == "alpha" for row in skills["skills"])
                native.prompt(
                    identity,
                    "load alpha and its asset",
                    operation_id="read-alpha",
                    deadline_epoch_ms=int(time.time() * 1000) + 10000,
                )
                _wait_native(backend, "read-alpha")
                assert len(model.requests) == 4
                last = json.dumps(model.requests[-1])
                assert "Peer body" in last and "Peer asset" in last and first["commit_id"] in last
                controller = runtime.m_adapter._resume_controller()
                assert isinstance(controller.backend_session, DshWebSession)
                selected = controller.backend_session
                result = controller.relaunch(
                    chat_session=RelaunchChatSessionSelection(
                        mode="exact", session_id=identity["native_session_id"]
                    )
                )
                assert result.status == "ok", result.detail
                replacement = GatewayClient(base_url=url).describe_endpoint()
                assert replacement.target != descriptor.target
                stale_target = _peer_file_cli(peer, coordinates, source, "mounts")
                assert stale_target.returncode == 1 and "verify" in stale_target.stderr
                current = _coordinates(url, replacement)
                assert (
                    _peer_json(peer, current, source, "mounts")["mounts"][0]["published_commit"]
                    == first["commit_id"]
                )
                wrong_listener = _coordinates(
                    url, replacement.model_copy(update={"presence_id": "retired-listener"})
                )
                stale_listener = _peer_file_cli(peer, wrong_listener, source, "mounts")
                assert stale_listener.returncode == 1 and "verify" in stale_listener.stderr
                _owner_cli("access", "credential-revoke", str(public["key_id"]))
                revoked = _peer_file_cli(peer, current, source, "mounts")
                assert revoked.returncode == 1 and "HTTP 401" in revoked.stderr
            absent = _peer_file_cli(peer, current, source, "mounts")
            assert absent.returncode == 1 and "could not be confirmed" in absent.stderr
        finally:
            _stop(runtime, selected)
