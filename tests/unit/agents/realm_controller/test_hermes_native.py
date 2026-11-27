"""Hermetic coverage of Hermes home authority and native session verification."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from houmao.agents.realm_controller.backends import hermes_native
from houmao.agents.realm_controller.backends.hermes_native import (
    HermesClient,
    HermesDaemon,
    HermesDeadlineExpired,
    HermesNativeError,
    read_hermes_evidence,
)
from houmao.agents.realm_controller.startup_rollback import runtime_startup_scope
from houmao.execution.context import execution_deadline_scope


@pytest.fixture
def native_setup(tmp_path: Path) -> tuple[HermesDaemon, Path, dict[str, Any]]:
    """Create two private roots and one ready native identity."""

    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    root = tmp_path / "runtime"
    daemon = HermesDaemon.from_inputs(
        executable="/fixture/hermes", home=home, workspace=tmp_path, env={}, root=root
    )
    payload = {
        "hermes_home": str(home),
        "pid": 40141,
        "start_time": 10,
        "state": "ready",
        "runtime_protocol": 1,
        "authority_epoch": 7,
        "instance_id": "native-one",
        "capabilities": ["session-authority-v1"],
        "served_profiles": [{"profile_id": str(home), "home": str(home)}],
        "api_origin": "http://127.0.0.1:58242",
    }
    return daemon, root, payload


def test_daemon_adopts_only_its_launch_home(
    native_setup: tuple[HermesDaemon, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reuse an independently started daemon and reject a served secondary."""

    daemon, root, payload = native_setup
    monkeypatch.setattr(hermes_native, "_dispatch_origin_birth_token", lambda pid: "proc:10")
    monkeypatch.setattr(hermes_native, "_control_query", lambda *args: (payload, payload["pid"]))
    started = []
    monkeypatch.setattr(daemon, "_start", lambda: started.append(True))
    assert daemon.ensure().pid == payload["pid"]
    record = read_hermes_evidence(root / "hermes-daemon.json")
    assert record is not None
    assert record["instance_id"] == "native-one"
    assert "api_origin" not in record
    assert not started
    payload["hermes_home"] = str(root / "unrelated")
    with pytest.raises(HermesNativeError, match="different launch home"):
        daemon.ensure()
    assert not started


def test_daemon_starts_once_and_waits_for_exact_home(
    native_setup: tuple[HermesDaemon, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A vacant home starts one daemon, then captures its authenticated identity."""

    daemon, _, payload = native_setup
    started: list[str] = []

    def control(*_args: object) -> tuple[dict[str, Any], int]:
        if not started:
            raise FileNotFoundError
        return payload, payload["pid"]

    monkeypatch.setattr(hermes_native, "_dispatch_origin_birth_token", lambda pid: "proc:10")
    monkeypatch.setattr(hermes_native, "_control_query", control)
    monkeypatch.setattr(daemon, "_start", lambda: started.append(str(daemon.workspace)))
    assert daemon.ensure().home == Path(payload["hermes_home"])
    assert started == [str(daemon.workspace)]


@pytest.mark.parametrize("already_running", [False, True])
def test_failed_launch_stops_only_its_new_hermes_daemon(
    already_running: bool,
    native_setup: tuple[HermesDaemon, Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use the actual daemon acquisition path without signaling a reused process."""

    daemon, root, payload = native_setup
    root.mkdir(mode=0o700, exist_ok=True)
    process = Mock(pid=payload["pid"], **{"poll.return_value": None})
    spawn = Mock(return_value=process)
    stop_identity = Mock()

    def identify(*args: object) -> tuple[dict[str, Any], int]:
        if not already_running and not spawn.called:
            raise FileNotFoundError
        return payload, payload["pid"]

    monkeypatch.setattr(hermes_native.subprocess, "Popen", spawn)
    monkeypatch.setattr(hermes_native, "_control_query", identify)
    monkeypatch.setattr(hermes_native, "_dispatch_origin_birth_token", lambda pid: "proc:10")
    monkeypatch.setattr(hermes_native, "_stop_identity", stop_identity)
    with pytest.raises(OSError, match="injected startup failure"), runtime_startup_scope():
        assert daemon.ensure().pid == payload["pid"]
        raise OSError("injected startup failure")

    assert spawn.call_count == int(not already_running)
    assert process.terminate.call_count == int(not already_running)
    stop_identity.assert_not_called()


def test_daemon_rejects_stale_process_and_non_loopback_endpoint(
    native_setup: tuple[HermesDaemon, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Require current OS process evidence and a private native endpoint."""

    daemon, _, payload = native_setup
    monkeypatch.setattr(hermes_native, "_control_query", lambda *args: (payload, payload["pid"]))
    monkeypatch.setattr(hermes_native, "_dispatch_origin_birth_token", lambda pid: "proc:11")
    with pytest.raises(HermesNativeError, match="process identity is stale"):
        daemon.discover()
    monkeypatch.setattr(hermes_native, "_dispatch_origin_birth_token", lambda pid: "proc:10")
    payload["api_origin"] = "http://192.0.2.1:58242"
    with pytest.raises(HermesNativeError, match="private loopback"):
        daemon.discover()


def test_native_rpc_uses_delegated_budget_for_send_and_receive(
    native_setup: tuple[HermesDaemon, Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Clamp the actual native transport waits and refuse an expired RPC before sending."""

    daemon, _, payload = native_setup
    monkeypatch.setattr(hermes_native, "_dispatch_origin_birth_token", lambda _: "proc:10")
    monkeypatch.setattr(hermes_native, "_control_query", lambda *args: (payload, payload["pid"]))
    identity = daemon.discover()
    assert identity is not None
    sent: list[dict[str, Any]] = []
    socket_timeouts: list[float | None] = []
    receive_timeouts: list[float] = []
    clock = [100.0]
    monkeypatch.setattr(hermes_native, "time", SimpleNamespace(monotonic=lambda: clock[0]))

    def receive(*, timeout: float) -> str:
        """Expose the native RPC receive budget without opening a network socket."""

        receive_timeouts.append(timeout)
        return json.dumps({"id": sent[-1]["id"], "result": {"status": "queued"}})

    peer = SimpleNamespace(
        socket=SimpleNamespace(settimeout=socket_timeouts.append),
        send=lambda raw: sent.append(json.loads(raw)),
        recv=receive,
    )
    client = HermesClient(peer, identity)
    with execution_deadline_scope(100.125):
        assert client.rpc("prompt.receipt") == {"status": "queued"}
        clock[0] = 100.125
        with pytest.raises(HermesDeadlineExpired, match="execution deadline expired"):
            client.rpc("prompt.submit", text="must never be sent")

    assert socket_timeouts == [0.125, None]
    assert receive_timeouts == [0.125]
    assert [message["method"] for message in sent] == ["prompt.receipt"]


def test_stop_adopts_exact_unready_process_without_touching_other_home(
    native_setup: tuple[HermesDaemon, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stop can verify a draining process while structured RPC is unavailable."""

    daemon, root, payload = native_setup
    payload["state"] = "draining"
    monkeypatch.setattr(hermes_native, "_control_query", lambda *args: (payload, payload["pid"]))
    monkeypatch.setattr(hermes_native, "_dispatch_origin_birth_token", lambda pid: "proc:10")
    monkeypatch.setattr(hermes_native, "owner_process_has_exited", lambda *args: False)
    monkeypatch.setattr(hermes_native.os, "waitpid", lambda *args: (0, 0))
    stopped = []
    monkeypatch.setattr(hermes_native, "_stop_identity", lambda *args: stopped.append(args))
    assert daemon.discover() is None
    daemon.stop()
    assert stopped == [(payload["pid"], "proc:10")]
    payload["hermes_home"] = str(root / "secondary-home")
    with pytest.raises(HermesNativeError, match="different launch home"):
        daemon.stop()
    assert len(stopped) == 1


def test_authentication_and_exact_session_follow_same_home_replacement(
    native_setup: tuple[HermesDaemon, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mint a new private ticket and retain the verified logical session across daemon restart."""

    daemon, root, payload = native_setup
    messages: list[dict[str, Any]] = []
    grants: list[dict[str, Any]] = []
    session_id = "logical-id"

    def control(
        home: Path, verb: str, params: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], int]:
        if verb == "identify":
            return payload, payload["pid"]
        assert params is not None
        assert params == {
            "profile_id": str(home),
            "instance_id": payload["instance_id"],
            "purpose": "interactive",
            "scope": "profile",
        }
        grants.append(params)
        return {**params, "ticket": "private-fixture-ticket"}, payload["pid"]

    class Peer:
        """Provide the exact authenticated native response addressed by an ID."""

        subprotocol = "hermes-gateway-v1"

        def send(self, raw: str) -> None:
            """Record outbound RPC without exposing the bootstrap grant."""

            messages.append(json.loads(raw))

        def recv(self, **_kwargs: object) -> str:
            """Return the requested authority or exact session binding."""

            request = messages[-1]
            result = {
                "profile_id": payload["hermes_home"],
                "instance_id": payload["instance_id"],
                "authority_epoch": payload["authority_epoch"],
            }
            if request["method"] == "session.resume":
                assert request["params"] == {"session_id": session_id, "omit_messages": True}
                result.update(
                    session_id=session_id,
                    stored_session_id=session_id,
                    info={"profile_id": payload["hermes_home"], "cwd": str(daemon.workspace)},
                    physical_session_id="compressed-physical-row",
                )
            return json.dumps({"id": request["id"], "result": result})

    @contextmanager
    def connect(url: str, **configuration: Any):
        """Require a private ticket on the negotiated loopback connection."""

        assert url == "ws://127.0.0.1:58242/api/ws"
        assert configuration["subprotocols"] == [
            "hermes-gateway-v1",
            "hermes-gateway-ticket.private-fixture-ticket",
        ]
        yield Peer()

    monkeypatch.setattr(
        hermes_native, "_dispatch_origin_birth_token", lambda pid: f"proc:{payload['start_time']}"
    )
    monkeypatch.setattr(hermes_native, "_control_query", control)
    monkeypatch.setattr(hermes_native, "connect", connect)
    first = daemon.resolve_session(session_id)
    assert first.daemon_instance_id == "native-one"
    payload.update(instance_id="native-two", authority_epoch=8, pid=40142, start_time=11)
    second = daemon.resolve_session(session_id)
    assert first.session_id == second.session_id
    assert second.daemon_instance_id == "native-two"
    assert [grant["instance_id"] for grant in grants] == ["native-one", "native-two"]
    assert "private-fixture-ticket" not in (root / "hermes-daemon.json").read_text()


def test_exact_session_verification_rejects_workspace_or_logical_id_mismatch(
    native_setup: tuple[HermesDaemon, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the full logical ID and workspace authoritative independent of compaction."""

    daemon, _, payload = native_setup
    monkeypatch.setattr(hermes_native, "_dispatch_origin_birth_token", lambda pid: "proc:10")
    monkeypatch.setattr(hermes_native, "_control_query", lambda *args: (payload, payload["pid"]))
    identity = daemon.discover()
    assert identity is not None
    snapshot = {
        "session_id": "logical",
        "stored_session_id": "logical",
        "physical_session_id": "compressed",
        "authority_epoch": identity.authority_epoch,
        "info": {"profile_id": identity.profile_id, "cwd": str(daemon.workspace)},
    }
    assert daemon.verify_snapshot(snapshot, identity, session_id="logical").session_id == "logical"
    with pytest.raises(HermesNativeError, match="exact session"):
        daemon.verify_snapshot(snapshot, identity, session_id="missing-looks-like-title")
    snapshot["info"]["cwd"] = str(daemon.workspace / "unexpected")
    with pytest.raises(HermesNativeError, match="managed workspace"):
        daemon.verify_snapshot(snapshot, identity, session_id="logical")
