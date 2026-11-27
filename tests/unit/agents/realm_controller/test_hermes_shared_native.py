"""Exercise shared-host acquisition, profile attestation, and release."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest

from houmao.agents.hermes_configuration import hermes_unattended_approval_policy
from houmao.agents.hermes_installation import (
    PreparedHermesEvidence,
    PreparedHermesInstallation,
)
from houmao.agents.hermes_profile import (
    HERMES_PROFILE_RECORD,
    HermesProfileBinding,
    write_hermes_profile_record,
)
from houmao.agents.realm_controller import hermes_tool_origin
from houmao.agents.realm_controller.backends import hermes_native
from houmao.agents.realm_controller.backends.hermes_native import HermesDaemon, HermesNativeError
from houmao.agents.realm_controller.startup_rollback import runtime_startup_scope


@pytest.fixture
def native_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide one process serving two independently staged named profiles."""

    root = tmp_path / "prepared"
    root.mkdir(mode=0o700)
    (root / "profiles").mkdir(mode=0o700)
    lock_dir = root / "gateway-locks"
    lock_dir.mkdir(mode=0o700)
    build = "8fc037444731" + "a" * 28
    executable = str(root / "hermes")
    context_id = str(uuid4())
    broker_socket = Path("/tmp") / f"houmao-test-{uuid4().hex}.sock"
    installation = PreparedHermesInstallation(
        root,
        executable,
        lock_dir,
        PreparedHermesEvidence(build, "0.23.4", root / "installs" / "active", "stamp"),
        root / "tools" / "node",
    )
    root_info: dict[str, Any] = {
        "pid": 40193,
        "start_time": 12,
        "state": "ready",
        "runtime_protocol": 1,
        "code_sha": build,
        "authority_epoch": 41,
        "instance_id": "shared-one",
        "capabilities": ["session-authority-v1"],
        "hermes_home": str(root),
        "api_origin": "http://127.0.0.1:53201",
    }
    daemons = {}
    profiles = {}
    epochs = {}
    for name in ("alpha", "beta"):
        home = root / "profiles" / name
        home.mkdir(mode=0o700)
        (home / "gateway.parked").touch(mode=0o600)
        workspace = tmp_path / f"work-{name}"
        workspace.mkdir(mode=0o700)
        binding = HermesProfileBinding(
            prepared_root=root,
            profile_home=home,
            profile_name=name,
            context_id=context_id,
            gateway_lock_dir=lock_dir,
            project_home_link=workspace / "home",
            installation_build=build,
            profile_owner_id=str(uuid4()),
            executable=executable,
            broker_socket=broker_socket,
        )
        write_hermes_profile_record(home, binding)
        daemon = HermesDaemon.from_inputs(
            executable=executable,
            home=home,
            workspace=workspace,
            env={"HERMES_MANAGED_API_KEY": f"synthetic-{name}"},
            root=workspace / "native",
            profile=binding,
        )
        daemons[name] = daemon
        profiles[str(home)] = daemon
        epochs[str(home)] = 0

    hosted: set[str] = set()
    retained: set[str] = set()
    grants: list[dict[str, Any]] = []
    rpcs: list[tuple[str, dict[str, Any]]] = []
    spawned = Mock(return_value=Mock(pid=root_info["pid"]))
    wire_override: dict[str, Any] = {}

    def control(home: Path, verb: str, params=None, **_options: Any):
        """Answer only on the root socket and honor the exact requested named profile."""

        assert home == root
        if not spawned.called:
            raise FileNotFoundError
        pid = root_info["pid"]
        if verb == "identify":
            return {
                **root_info,
                "served_profiles": [{"profile_id": item, "home": item} for item in sorted(hosted)],
            }, pid
        assert isinstance(params, dict)
        if verb == "resolve-profile":
            requested = params["home"]
            assert requested in hosted
            return {
                "resolve_protocol": 1,
                "state": "ready",
                "attachable": True,
                "update_fenced": False,
                "control": "host",
                "install_code_sha": build,
                "endpoint": {
                    "control_home": str(root),
                    "code_sha": build,
                    "profile_id": requested,
                    "instance_id": root_info["instance_id"],
                    "authority_epoch": root_info["authority_epoch"],
                    "runtime_protocol": 1,
                    "ws_protocol": "hermes-gateway-v1",
                    "ticket_protocol_prefix": "hermes-gateway-ticket.",
                    "ws_url": "ws://127.0.0.1:53201/api/ws",
                    **wire_override,
                },
            }, pid
        if verb == "session-ticket":
            assert params["profile_id"] in hosted
            assert params["scope"] == "profile"
            grants.append(params)
            return {**params, "ticket": f"opaque-{len(grants)}"}, pid
        requested = str(root / "profiles" / params["name"])
        if verb == "serve-profile":
            assert not (Path(requested) / "gateway.parked").exists()
            hosted.add(requested)
            epochs[requested] += 1
            return {"served": params["name"]}, pid
        assert verb == "unserve-profile"
        assert (Path(requested) / "gateway.parked").is_file()
        hosted.discard(requested)
        return {"unserved": params["name"]}, pid

    class Peer:
        """Emulate a transport scoped permanently by the mint operation."""

        subprotocol = "hermes-gateway-v1"

        def __init__(self, home: str) -> None:
            self.home = home
            self.socket = Mock()

        def send(self, request: str) -> None:
            self.request = json.loads(request)
            rpcs.append((self.home, self.request))

        def recv(self, **_options: Any) -> str:
            method = self.request["method"]
            params = self.request["params"]
            info = {
                "profile_id": self.home,
                "profile_name": Path(self.home).name,
                "cwd": str(profiles[self.home].workspace),
            }
            approval = hermes_unattended_approval_policy()
            if method == "runtime.describe":
                result = {
                    "profile_id": self.home,
                    "instance_id": root_info["instance_id"],
                    "authority_epoch": epochs[self.home],
                    "capabilities": sorted(hermes_native._PROFILE_CAPABILITIES),
                }
            elif method == "plugins.list":
                result = {
                    "plugins": [
                        {
                            "key": "houmao-tool-origin",
                            "version": "1.0.0",
                            "enabled": True,
                            "error": "",
                        }
                    ]
                }
            elif method == "config.get":
                result = (
                    {"value": approval["mode"]}
                    if params["key"] == "approvals.mode"
                    else {"config": {"approvals": approval}}
                )
            elif method == "session.info":
                result = dict(info)
            else:
                assert method == "session.resume"
                result = {
                    "session_id": params["session_id"],
                    "stored_session_id": params["session_id"],
                    "authority_epoch": epochs[self.home],
                    "info": info,
                }
            return json.dumps({"id": self.request["id"], "result": result})

    @contextmanager
    def connect(url: str, **options: Any):
        """Verify socket target and recover the actual profile scoped by its ticket."""

        assert url == "ws://127.0.0.1:53201/api/ws"
        ticket = options["subprotocols"][1]
        index = int(ticket.removeprefix("hermes-gateway-ticket.opaque-")) - 1
        yield Peer(grants[index]["profile_id"])

    monkeypatch.setattr(
        hermes_native, "load_prepared_hermes_installation", lambda *a, **k: installation
    )
    monkeypatch.setattr(
        hermes_tool_origin, "ensure_hermes_tool_origin_broker", lambda *a, **k: broker_socket
    )
    monkeypatch.setattr(hermes_tool_origin, "require_hermes_tool_origin_hook", Mock())
    monkeypatch.setattr(hermes_native, "_dispatch_origin_birth_token", lambda _: "proc:12")
    monkeypatch.setattr(
        hermes_native, "_runtime_lock_held", lambda home: str(home) in hosted | retained
    )
    monkeypatch.setattr(hermes_native, "_control_query", control)
    monkeypatch.setattr(hermes_native, "connect", connect)
    monkeypatch.setattr(hermes_native.subprocess, "Popen", spawned)
    return daemons, root_info, hosted, retained, epochs, rpcs, spawned, wire_override


def test_concurrent_named_profile_launches_share_one_host(native_host) -> None:
    """The root lock serializes host creation while each ticket selects its own profile."""

    daemons, _, hosted, _, _, _, spawned, _ = native_host
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(daemon.ensure, unattended=True) for daemon in daemons.values()]
        alpha, beta = [future.result(timeout=5) for future in futures]
    spawned.assert_called_once()
    host_environment = spawned.call_args.kwargs["env"]
    assert "HERMES_MANAGED_API_KEY" not in host_environment
    assert host_environment["GATEWAY_MULTIPLEX_PROFILES"] == "1"
    assert host_environment["HERMES_DISABLE_LAZY_INSTALLS"] == "1"
    assert alpha.pid == beta.pid and alpha.instance_id == beta.instance_id
    assert {(alpha.profile_id, alpha.authority_epoch), (beta.profile_id, beta.authority_epoch)} == {
        (profile, 1) for profile in hosted
    }
    command, environment = daemons["alpha"].native_command(["acp"])
    assert command[1:] == ["--profile", "alpha", "acp"]
    assert environment["HERMES_HOME"] == alpha.profile_id


def test_same_host_profile_epoch_change_requires_exact_recovery(native_host) -> None:
    """A new profile epoch cannot silently accept input or replace sibling proof."""

    daemons, _, _, _, epochs, rpcs, _, _ = native_host
    target, sibling = daemons["alpha"], daemons["beta"]
    initial = target.ensure(unattended=True)
    sibling_identity = sibling.ensure(unattended=True)
    epochs[initial.profile_id] += 1
    changed = target.discover()
    assert (
        changed is not None
        and changed.pid == initial.pid
        and changed.instance_id == initial.instance_id
    )
    assert changed.authority_epoch != initial.authority_epoch
    with pytest.raises(HermesNativeError, match="verified recovery"):
        target.require_recorded_authority(changed)
    assert target.recover_shared("exact-saved-session", unattended=True) == changed
    target.require_recorded_authority(changed)
    assert any(request["params"].get("session_id") == "exact-saved-session" for _, request in rpcs)
    assert all(request["method"] != "prompt.submit" for _, request in rpcs)
    assert sibling.discover() == sibling_identity


def test_replaced_host_requires_each_profile_to_recover(native_host) -> None:
    """Recover the selected conversation without publishing authority for its sibling."""

    daemons, root_info, _, _, _, rpcs, _, _ = native_host
    target, sibling = daemons["alpha"], daemons["beta"]
    initial = target.ensure(unattended=True)
    sibling.ensure(unattended=True)
    root_info.update(pid=40194, instance_id="shared-two")

    replacement = target.recover_shared("exact-saved-session", unattended=True)
    assert replacement.pid != initial.pid and replacement.instance_id != initial.instance_id
    target.require_recorded_authority(replacement)
    sibling_authority = sibling.discover()
    assert sibling_authority is not None and sibling_authority.pid == replacement.pid
    with pytest.raises(HermesNativeError, match="verified recovery"):
        sibling.require_recorded_authority(sibling_authority)
    assert all(request["method"] != "prompt.submit" for _, request in rpcs)


def test_park_release_and_failed_start_preserve_sibling_and_warm_host(
    native_host, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A native route disappearing alone cannot grant permission to reuse its profile."""

    daemons, _, hosted, retained, _, _, spawned, _ = native_host
    target, sibling = daemons["alpha"], daemons["beta"]
    sibling_identity = sibling.ensure(unattended=True)
    with pytest.raises(RuntimeError, match="injected startup failure"), runtime_startup_scope():
        identity = target.ensure(unattended=True)
        raise RuntimeError("injected startup failure")
    target.require_released()
    assert identity.profile_id not in hosted and sibling.discover() == sibling_identity
    second = target.ensure(unattended=True)
    assert second.pid == identity.pid and second.authority_epoch != identity.authority_epoch
    retained.add(second.profile_id)
    monkeypatch.setattr(hermes_native, "_PROFILE_WAIT_TIMEOUT", 0.1)
    with pytest.raises(HermesNativeError, match="release remains unconfirmed"):
        target.stop(expected=second)
    with pytest.raises(HermesNativeError, match="not released"):
        target.require_released()
    retained.clear()
    target.require_released()
    sibling.stop(expected=sibling_identity)
    assert not hosted
    assert target.ensure(unattended=True).pid == identity.pid
    spawned.assert_called_once()
    spawned.return_value.terminate.assert_not_called()


@pytest.mark.parametrize(
    "mismatch", ("wrong_root", "peer_birth", "profile_id", "code_sha", "capability")
)
def test_shared_profile_refuses_mismatched_native_authority(
    native_host, monkeypatch: pytest.MonkeyPatch, mismatch: str
) -> None:
    """An unqualified owner or endpoint cannot redirect a native ticket."""

    daemons, root_info, _, _, _, rpcs, _, wire = native_host
    target = daemons["alpha"]
    target.ensure(unattended=True)
    if mismatch == "wrong_root":
        root_info["hermes_home"] = str(target.workspace)
    elif mismatch == "peer_birth":
        monkeypatch.setattr(hermes_native, "_dispatch_origin_birth_token", lambda _: "proc:13")
    elif mismatch == "profile_id":
        wire["profile_id"] = str(daemons["beta"].workspace)
    elif mismatch == "capability":
        root_info["capabilities"] = []
    else:
        wire["code_sha"] = "0" * 40
    before = len(rpcs)
    with pytest.raises(HermesNativeError):
        target.discover()
    assert len(rpcs) == before


def test_shared_profile_refuses_control_after_home_ownership_changes(native_host) -> None:
    """An available native route alone cannot authorize managing a replaced home."""

    daemons, _, hosted, _, _, _, _, _ = native_host
    target = daemons["alpha"]
    sibling = daemons["beta"]
    target_identity = target.ensure(unattended=True)
    sibling_identity = sibling.ensure(unattended=True)
    (target_identity.home / HERMES_PROFILE_RECORD).unlink()

    with pytest.raises(HermesNativeError, match="profile ownership is unavailable"):
        target.discover()
    with pytest.raises(HermesNativeError, match="profile ownership is unavailable"):
        target.stop()

    assert str(target_identity.home) in hosted
    assert sibling.discover() == sibling_identity
