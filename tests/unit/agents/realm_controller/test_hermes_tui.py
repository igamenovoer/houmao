"""Hermetic checks for Hermes TUI admission, recovery, and terminal identity."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from houmao.agents.realm_controller.backends import hermes_tui
from houmao.agents.realm_controller.backends.hermes_native import (
    HermesDaemonIdentity,
    HermesNativeError,
    HermesSessionSnapshot,
    write_hermes_evidence,
)
from houmao.agents.realm_controller.backends.hermes_tui import (
    HermesInputConflict,
    HermesTuiSession,
    HermesTuiSessionState,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.owner_admission import OwnerAdmissionError
from houmao.execution.tmux import TmuxPaneRecord


class FakeOwnerClaim:
    """Capture the managed slot transitions required by a native submit."""

    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = manifest_path
        self.request_id = "houmao-request"
        self.generation_id = "managed-generation"
        self.mode = "tui"
        self.handoffs = 0
        self.finished: list[str] = []

    def active(self) -> bool:
        """Model a valid owner claim throughout the test."""

        return True

    def handoff(self) -> None:
        """Record confirmation of the native receipt."""

        self.handoffs += 1

    def finish(self, outcome: str, **_metadata: Any) -> None:
        """Record terminal or uncertain attempt evidence."""

        self.finished.append(outcome)


@pytest.fixture
def tui(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> HermesTuiSession:
    """Restore a strict saved terminal and logical session binding."""

    home, hints = tmp_path / "home", tmp_path / "hints"
    home.mkdir(mode=0o700)
    hints.mkdir(mode=0o700)
    plan = LaunchPlan(
        backend="hermes_tui",
        tool="hermes",
        executable="/fixture/hermes",
        args=[],
        working_directory=tmp_path,
        home_env_var="HERMES_HOME",
        home_path=home,
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(method="none", role_name="default", prompt=""),
    )
    saved = HermesTuiSessionState(
        session_name="HOUMAO-hermes-agent",
        pane_id="%1",
        window_id="@1",
        tmux_session_id="$1",
        tmux_socket_path=str(tmp_path / "isolated-tmux.sock"),
        pane_pid=40100,
        pane_birth_token="proc:1000",
        hint_directory=str(hints),
        native_session_id="native-logical-id",
        home=str(home),
        working_directory=str(tmp_path),
    )
    session = HermesTuiSession.from_launch_plan(
        plan, session_manifest_path=tmp_path / "manifest.json", state=saved
    )
    monkeypatch.setattr(session, "_generation_id", lambda: "managed-generation")
    return session


def _instance(tui: HermesTuiSession, *, name: str = "daemon-one", epoch: int = 1):
    """Represent an authenticated socket for a single daemon incarnation."""

    return HermesDaemonIdentity(
        home=tui.plan.home_path,
        pid=40100,
        birth_token="proc:170",
        instance_id=name,
        authority_epoch=epoch,
        profile_id=str(tui.plan.home_path),
        websocket_url="ws://127.0.0.1:40100/api/ws",
    )


def _install_peer(monkeypatch, tui, peer, *, busy: bool = False):
    """Use a deterministic RPC peer and a checked idle or running snapshot."""

    @contextmanager
    def connection():
        yield peer

    def resume(native, session_id):
        assert session_id == tui.state.native_session_id
        return HermesSessionSnapshot(
            session_id,
            {
                "running": busy,
                "pending": [],
                "prompts": [],
                "open_requests": [],
                "pending_connection": None,
                "replay_epoch": "replay-one",
                "last_sequence": 1,
            },
            native.identity.instance_id,
        )

    monkeypatch.setattr(tui.daemon, "ensure", lambda: peer.identity)
    monkeypatch.setattr(tui.daemon, "client", connection)
    monkeypatch.setattr(tui.daemon, "resume_session", resume)


def _receipt(tui, identity, status, **values):
    """Build the native protocol's exact queue or terminal receipt."""

    return {
        "ref": {"session_id": tui.state.native_session_id, "profile_id": identity.profile_id},
        "admission_id": "native-admission",
        "status": status,
        "authority_epoch": identity.authority_epoch,
        "sequence": 2,
        "outcome": None,
        "execution_generation": None if status == "queued" else 3,
        **values,
    }


def test_native_busy_refuses_before_writing_prompt(tui, monkeypatch):
    """Native readiness prevents all submissions when a human is already active."""

    identity = _instance(tui)
    calls = []
    peer = SimpleNamespace(identity=identity, rpc=lambda *args, **kwargs: calls.append(args))
    _install_peer(monkeypatch, tui, peer, busy=True)
    claim = FakeOwnerClaim(tui.manifest_path)
    with pytest.raises(OwnerAdmissionError, match="busy") as failure:
        tui.submit_native_prompt("literal", request_id=claim.request_id, owner_claim=claim)
    assert failure.value.code == "not_ready"
    assert not calls
    assert claim.handoffs == 0
    assert claim.finished == ["failed"]


@pytest.mark.parametrize("lost_ack", [False, True])
def test_revoked_submit_authority_preserves_possible_native_handoff(tui, monkeypatch, lost_ack):
    """Release a pre-submit revocation and retain an unresolved transmitted request."""

    identity = _instance(tui)
    calls = []

    def rpc(method, **params):
        calls.append(method)
        raise HermesNativeError("Lost acknowledgment")

    def authorize():
        if not lost_ack or calls:
            raise RuntimeError("Gateway grant revoked")

    peer = SimpleNamespace(identity=identity, rpc=rpc)
    _install_peer(monkeypatch, tui, peer)
    claim = FakeOwnerClaim(tui.manifest_path)
    with pytest.raises(RuntimeError):
        tui.submit_native_prompt(
            "literal", request_id=claim.request_id, owner_claim=claim, authorize=authorize
        )
    assert calls == (["prompt.submit"] if lost_ack else [])
    assert claim.handoffs == 0
    assert claim.finished == (["uncertain"] if lost_ack else ["failed"])


def test_native_queued_receipt_survives_lost_ack_and_rejects_conflicting_payload(tui, monkeypatch):
    """A second RPC recovers the same stable native submission and positive queue receipt."""

    identity = _instance(tui)
    requests = []

    def rpc(method, **params):
        if method == "prompt.submit":
            requests.append(params)
            if len(requests) == 1:
                raise HermesNativeError("lost reply")
            return _receipt(tui, identity, "queued")
        raise AssertionError(method)

    peer = SimpleNamespace(identity=identity, rpc=rpc)
    _install_peer(monkeypatch, tui, peer)
    claim = FakeOwnerClaim(tui.manifest_path)
    accepted = tui.submit_native_prompt(
        "line one\nline two", request_id=claim.request_id, owner_claim=claim
    )
    assert accepted.state == "queued"
    assert accepted.native_admission_id == "native-admission"
    assert requests[0] == requests[1]
    assert requests[0]["text"] == "line one\nline two"
    assert claim.handoffs == 1
    assert not claim.finished
    with pytest.raises(HermesInputConflict, match="already seen"):
        tui.submit_native_prompt(
            "different payload", request_id=claim.request_id, owner_claim=claim
        )
    assert len(requests) == 2
    assert not claim.finished


def test_native_recovery_filters_human_output_and_refuses_stale_cancellation(tui, monkeypatch):
    """Keep exact admission identity across a restart and recover settlement after an event gap."""

    first, second = _instance(tui), _instance(tui, name="daemon-two", epoch=2)
    claim = FakeOwnerClaim(tui.manifest_path)
    disposition, requests = "queued", []

    def rpc(method, **params):
        requests.append(method)
        if method == "prompt.submit":
            return _receipt(tui, first, "queued")
        if method == "prompt.receipt":
            assert params["admission_id"] == "native-admission"
            if disposition == "terminal":
                return _receipt(
                    tui,
                    second,
                    "terminal",
                    outcome="completed",
                    result={"final_response": "our answer"},
                )
            return _receipt(tui, first, disposition)
        if method == "session.events.since":
            if disposition == "terminal":
                return {"replay_epoch": "replay-two", "latest_seq": 3, "snapshot_required": True}
            return {
                "replay_epoch": "replay-one",
                "latest_seq": 3,
                "events": [
                    {
                        "seq": 2,
                        "session_id": tui.state.native_session_id,
                        "admission_id": "human",
                        "authority_epoch": 1,
                        "execution_generation": 3,
                        "type": "message.delta",
                        "payload": {"text": "human answer"},
                    },
                    {
                        "seq": 3,
                        "session_id": tui.state.native_session_id,
                        "admission_id": "native-admission",
                        "authority_epoch": 1,
                        "execution_generation": 3,
                        "type": "message.delta",
                        "payload": {"text": "our deltas"},
                    },
                ],
            }
        raise AssertionError(method)

    peer = SimpleNamespace(identity=first, rpc=rpc)
    _install_peer(monkeypatch, tui, peer)
    accepted = tui.submit_native_prompt("literal", request_id=claim.request_id, owner_claim=claim)
    assert accepted.state == "queued"
    disposition = "started"
    following = tui.read_native_admission(claim.request_id)
    assert following is not None and following.state == "running"
    assert [event.message for event in following.events] == ["our deltas"]
    peer.identity, disposition = second, "terminal"
    terminal = tui.read_native_admission(claim.request_id)
    assert terminal is not None and terminal.state == "completed"
    assert terminal.native_admission_id == accepted.native_admission_id
    assert terminal.replay_gap
    assert terminal.output_text == "our answer"
    assert tui.interrupt_native_admission(claim.request_id).status == "error"
    assert "prompt.cancel" not in requests


def test_lost_ack_during_daemon_replacement_preserves_uncertainty(tui, monkeypatch):
    """Reconnect can verify the same home without reissuing across a new authority."""

    first, second = _instance(tui), _instance(tui, name="daemon-two", epoch=2)
    calls = []

    def lost(method, **params):
        calls.append(method)
        raise HermesNativeError("Transport interrupted")

    start = SimpleNamespace(identity=first, rpc=lost)
    replacement = SimpleNamespace(identity=second, rpc=pytest.fail)
    _install_peer(monkeypatch, tui, start)
    peers = iter((start, replacement))

    @contextmanager
    def connection():
        yield next(peers)

    monkeypatch.setattr(tui.daemon, "client", connection)
    claim = FakeOwnerClaim(tui.manifest_path)
    with pytest.raises(HermesNativeError, match="admission could not be recovered"):
        tui.submit_native_prompt("literal", request_id=claim.request_id, owner_claim=claim)
    evidence = tui.read_native_admission(claim.request_id)
    assert evidence is not None and evidence.state == "uncertain"
    assert evidence.native_admission_id is None
    assert calls == ["prompt.submit"]
    assert claim.handoffs == 0
    assert claim.finished == ["uncertain"]


@pytest.mark.parametrize(
    "contradiction",
    [
        {"sequence": False},
        {"outcome": "completed"},
        {"execution_generation": 3},
        {"authority_epoch": 2},
    ],
)
def test_malformed_queued_receipt_never_claims_handoff(tui, monkeypatch, contradiction):
    """A queued receipt needs coherent native identity and lifecycle fields."""

    identity = _instance(tui)
    peer = SimpleNamespace(
        identity=identity,
        rpc=lambda *args, **kwargs: _receipt(tui, identity, "queued", **contradiction),
    )
    _install_peer(monkeypatch, tui, peer)
    claim = FakeOwnerClaim(tui.manifest_path)
    with pytest.raises(HermesNativeError, match="admission could not be recovered"):
        tui.submit_native_prompt("literal", request_id=claim.request_id, owner_claim=claim)
    assert claim.handoffs == 0
    assert claim.finished == ["uncertain"]


def test_native_turn_loss_keeps_uncertainty_without_submitting_again(tui, monkeypatch):
    """A successor with only an unknown receipt cannot manufacture another submission."""

    identity = _instance(tui)
    calls = []

    def rpc(method, **params):
        calls.append(method)
        if method == "prompt.submit":
            return _receipt(tui, identity, "started")
        if method == "prompt.receipt":
            return _receipt(tui, identity, "unknown")
        if method == "session.events.since":
            return {"replay_epoch": "replay-lost", "latest_seq": 0, "snapshot_required": True}
        raise AssertionError(method)

    peer = SimpleNamespace(identity=identity, rpc=rpc)
    _install_peer(monkeypatch, tui, peer)
    claim = FakeOwnerClaim(tui.manifest_path)
    accepted = tui.submit_native_prompt("literal", request_id=claim.request_id, owner_claim=claim)
    assert accepted.state == "running"
    pending = tui.read_native_admission(claim.request_id)
    assert pending is not None and pending.state == "uncertain"
    assert pending.native_admission_id == accepted.native_admission_id
    assert calls.count("prompt.submit") == 1
    assert not claim.finished


def test_cancel_targets_the_recorded_native_admission(tui, monkeypatch):
    """Read and cancel only the exact queued admission belonging to this request."""

    identity = _instance(tui)
    cancelled = []

    def rpc(method, **params):
        if method == "prompt.submit":
            return _receipt(tui, identity, "queued")
        if method == "prompt.cancel":
            cancelled.append(params)
        if method in {"prompt.receipt", "prompt.cancel"}:
            if cancelled:
                return _receipt(
                    tui, identity, "terminal", outcome="cancelled", execution_generation=None
                )
            return _receipt(tui, identity, "queued")
        if method == "session.events.since":
            return {"replay_epoch": "replay-one", "latest_seq": 1, "events": []}
        raise AssertionError(method)

    peer = SimpleNamespace(identity=identity, rpc=rpc)
    _install_peer(monkeypatch, tui, peer)
    claim = FakeOwnerClaim(tui.manifest_path)
    monkeypatch.setattr(
        tui, "_finish_claim", lambda _, admission: claim.finished.append(admission.state)
    )
    accepted = tui.submit_native_prompt("literal", request_id=claim.request_id, owner_claim=claim)
    claim.finished.clear()
    assert tui.interrupt_native_admission(claim.request_id).status == "ok"
    assert cancelled == [
        {"session_id": tui.state.native_session_id, "admission_id": accepted.native_admission_id}
    ]
    assert claim.finished == ["interrupted"]


def test_terminal_hint_tracks_switch_and_exit_without_changing_managed_session(tui, monkeypatch):
    """Only the live exact pane can supply its current Ink attachment hint."""

    state = tui.state
    pane = TmuxPaneRecord(
        pane_id=state.pane_id,
        session_name=state.session_name,
        window_id=state.window_id,
        window_index="0",
        window_name="agent",
        pane_index="0",
        pane_active=True,
        pane_pid=state.pane_pid,
        session_id=state.tmux_session_id,
    )
    monkeypatch.setattr(hermes_tui, "tmux_session_exists", lambda **kwargs: True)
    monkeypatch.setattr(hermes_tui, "list_tmux_panes", lambda **kwargs: (pane,))
    monkeypatch.setattr(
        hermes_tui, "_dispatch_origin_birth_token", lambda pid: state.pane_birth_token
    )
    hint = Path(state.hint_directory) / "hermes-tui-active-session-fixture.json"
    assert tui.terminal_attachment() == "unverified"
    write_hermes_evidence(hint, {"session_id": state.native_session_id})
    assert tui.terminal_attachment() == "attached"
    hint.write_text("{", encoding="utf-8")
    assert tui.terminal_attachment() == "unverified"
    write_hermes_evidence(hint, {"session_id": "other-session"})
    assert tui.terminal_attachment() == "other_session"
    assert tui.state.native_session_id == state.native_session_id
    pane = replace(pane, pane_pid=state.pane_pid + 1)
    assert tui.terminal_attachment() == "unverified"
    pane = replace(pane, pane_dead=True)
    assert tui.terminal_attachment() == "detached"
