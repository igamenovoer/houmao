"""Hermetic checks for Hermes TUI admission, recovery, and terminal identity."""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from typing import Any

import pytest
from click.testing import CliRunner

from houmao.agents.realm_controller import owner_admission
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
from houmao.agents.realm_controller.managed_control import managed_control_capabilities
from houmao.agents.realm_controller.owner_admission import (
    OwnerAdmissionError,
    observe_owner_prompt,
    reserve_owner_prompt,
)
from houmao.execution.tmux import TmuxPaneRecord
from houmao.execution import application
from houmao.execution.context import current_execution_deadline
from houmao.execution.models import ExecutionRequestV1
from houmao.execution.owner import OwnerAdmissionError as ExecutionOwnerAdmissionError
from houmao.server.models import HoumaoManagedAgentIdentity
from houmao.srv_ctrl.commands import managed_agents
from houmao.srv_ctrl.commands.agents import core as agent_commands
from houmao.srv_ctrl.commands.main import cli


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


@pytest.fixture
def hermes_owner_queue(tui: HermesTuiSession, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Use the real owner queue with the synthetic Hermes manifest binding."""

    database = tui.manifest_path.parent / "gateway" / "queue.sqlite"
    database.parent.mkdir()
    with sqlite3.connect(database):
        pass
    monkeypatch.setattr(
        owner_admission,
        "_owner_manifest",
        lambda *_: SimpleNamespace(
            backend="hermes_tui",
            mode="tui",
            backend_state={"native_session_id": tui.state.native_session_id},
        ),
    )
    return database


@pytest.fixture
def manager_target(tui: HermesTuiSession, monkeypatch: pytest.MonkeyPatch):
    """Use both manager entrypaths with real Hermes admission and a stubbed owner reader."""

    controller = SimpleNamespace(
        manifest_path=tui.manifest_path,
        registry_generation_id="managed-generation",
        backend_session=tui,
        execution_scope=nullcontext,
        observe_managed_tui=tui.observe_managed_control,
        control_capabilities=lambda: managed_control_capabilities(
            tool="hermes", mode="tui", backend="hermes_tui", native_surface=None
        ),
    )
    target = managed_agents.ManagedAgentTarget(
        mode="local",
        agent_ref="hermes-manager",
        identity=HoumaoManagedAgentIdentity(
            tracked_agent_id="hermes-manager",
            agent_id="hermes-manager",
            transport="tui",
            tool="hermes",
            mode="tui",
            backend="hermes_tui",
        ),
        controller=controller,
    )
    monkeypatch.setattr(agent_commands, "resolve_managed_agent_target", lambda **_: target)
    monkeypatch.setattr(managed_agents, "resolve_managed_agent_target", lambda **_: target)
    monkeypatch.setattr(
        managed_agents,
        "_manager_prompt_readiness",
        lambda *args, **kwargs: pytest.fail("Hermes must bypass parser readiness"),
    )
    monkeypatch.setattr(tui, "terminal_attachment", lambda: "attached")
    return target


def _local_manager_prompt():
    """Invoke the maintained scoped manager command through Click."""

    return CliRunner().invoke(
        cli,
        [
            "--print-json",
            "agents",
            "single",
            "--agent-id",
            "hermes-manager",
            "prompt",
            "--prompt",
            "literal",
        ],
    )


def _delegated_manager_prompt(monkeypatch: pytest.MonkeyPatch, *, seconds: float):
    """Invoke the owner application dispatcher and its v1 prompt argument boundary."""

    record = SimpleNamespace(
        execution_binding=object(), agent_id="hermes-manager", generation_id="managed-generation"
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.registry_storage.load_managed_agent_record_by_agent_id",
        lambda _: record,
    )
    request = ExecutionRequestV1(
        operation="prompt",
        agent_id=record.agent_id,
        generation_id=record.generation_id,
        deadline_seconds=seconds,
        arguments={"prompt": "literal"},
    )
    return application.dispatch_operation(request, record.execution_binding, SimpleNamespace())


@pytest.mark.parametrize("delegated", [False, True])
@pytest.mark.parametrize("attachment", ["attached", "detached", "other_session"])
def test_manager_hermes_settles_one_native_prompt_without_gateway(
    tui, monkeypatch, hermes_owner_queue, manager_target, delegated, attachment
) -> None:
    """Observe the pinned conversation and settle its one accepted request through either command."""

    identity = _instance(tui)
    calls = []
    polls = iter(["started", "terminal"])
    monkeypatch.setattr(tui, "terminal_attachment", lambda: attachment)

    def rpc(method, **params):
        calls.append(method)
        assert params["session_id"] == tui.state.native_session_id
        if method == "prompt.submit":
            assert params["text"] == "literal"
            assert (current_execution_deadline() is not None) is delegated
            with pytest.raises(OwnerAdmissionError, match="unresolved"):
                reserve_owner_prompt(tui.manifest_path, "managed-generation", origin="gateway")
            return _receipt(tui, identity, "queued")
        if method == "prompt.receipt":
            assert params["admission_id"] == "native-admission"
            assert current_execution_deadline() is not None
            status = next(polls)
            if status == "terminal":
                return _receipt(tui, identity, status, outcome="completed")
            return _receipt(tui, identity, status)
        assert method == "session.events.since"
        return {
            "replay_epoch": "replay-one",
            "latest_seq": 2,
            "events": [
                {
                    "seq": 2,
                    "session_id": tui.state.native_session_id,
                    "admission_id": "human-turn",
                    "authority_epoch": 1,
                    "execution_generation": 3,
                    "type": "message.delta",
                    "payload": {"text": "a different turn"},
                }
            ],
        }

    _install_peer(monkeypatch, tui, SimpleNamespace(identity=identity, rpc=rpc))
    if delegated:
        response = _delegated_manager_prompt(monkeypatch, seconds=2.0)
    else:
        result = _local_manager_prompt()
        assert result.exit_code == 0, result.output
        response = json.loads(result.output)

    assert response["delivery_state"] == "completed" and response["success"] is True
    assert response["evidence_source"] == "tui_native"
    request_id = response["request_id"]
    receipt = tui.read_native_admission(request_id)
    assert receipt is not None and receipt.terminal_outcome == "completed"
    assert receipt.events == ()
    assert calls == [
        "prompt.submit",
        "prompt.receipt",
        "session.events.since",
        "prompt.receipt",
        "session.events.since",
    ]
    with sqlite3.connect(hermes_owner_queue) as connection:
        assert connection.execute(
            "SELECT request_id, state FROM managed_prompt_attempts"
        ).fetchall() == [(request_id, "completed")]


@pytest.mark.parametrize("reason", ["busy", "unavailable", "gateway-owned", "final-check"])
def test_manager_hermes_refusal_keeps_native_input_closed(
    tui, monkeypatch, hermes_owner_queue, manager_target, reason
) -> None:
    """Refuse native busy or unavailable authority without a stale reserved claim."""

    identity = _instance(tui)
    peer = SimpleNamespace(identity=identity, rpc=lambda *a, **kw: pytest.fail("Unexpected input"))
    _install_peer(monkeypatch, tui, peer, busy=reason == "busy")
    if reason == "gateway-owned":
        gateway_claim = reserve_owner_prompt(
            tui.manifest_path, "managed-generation", origin="gateway"
        )
    elif reason == "unavailable":

        def unavailable():
            raise HermesNativeError("The daemon went away.")

        monkeypatch.setattr(tui.daemon, "client", unavailable)
    elif reason == "final-check":
        resume = tui.daemon.resume_session
        checks = iter([False, True])

        def resume_after_race(client, session_id):
            snapshot = resume(client, session_id)
            return replace(snapshot, payload={**snapshot.payload, "running": next(checks)})

        monkeypatch.setattr(tui.daemon, "resume_session", resume_after_race)

    code = "unavailable" if reason == "unavailable" else "not_ready"
    with pytest.raises(ExecutionOwnerAdmissionError) as refusal:
        _delegated_manager_prompt(monkeypatch, seconds=2.0)
    assert refusal.value.code == code
    with sqlite3.connect(hermes_owner_queue) as connection:
        rows = connection.execute(
            "SELECT request_id, state FROM managed_prompt_attempts"
        ).fetchall()
    if reason == "gateway-owned":
        assert rows == [(gateway_claim.request_id, "reserved")]
    elif reason == "final-check":
        assert len(rows) == 1 and rows[0][1] == "failed"
        assert observe_owner_prompt(tui.manifest_path, "managed-generation") is None
    else:
        assert rows == []


@pytest.mark.parametrize("disposition", ["queued", "running", "wrong-receipt", "lost-ack"])
def test_delegated_hermes_reports_exact_admission_under_shorter_deadline(
    tui, monkeypatch, hermes_owner_queue, manager_target, disposition
) -> None:
    """Keep the original owner claim when the finite request cannot observe settlement."""

    identity = _instance(tui)
    calls = []
    clock = [application.monotonic()]
    monkeypatch.setattr(application, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        hermes_tui,
        "time",
        SimpleNamespace(
            monotonic=lambda: clock[0], sleep=lambda value: clock.__setitem__(0, clock[0] + value)
        ),
    )

    def rpc(method, **params):
        calls.append(method)
        if method == "prompt.receipt":
            assert disposition == "wrong-receipt"
            return _receipt(tui, identity, "terminal", outcome="completed", admission_id="human")
        assert method == "prompt.submit"
        if disposition == "lost-ack":
            raise HermesNativeError("The original acknowledgment was lost.")
        return _receipt(tui, identity, "started" if disposition == "running" else "queued")

    peer = SimpleNamespace(identity=identity, rpc=rpc)
    _install_peer(monkeypatch, tui, peer)
    if disposition == "lost-ack":
        connections = iter(
            [peer, peer, SimpleNamespace(identity=_instance(tui, name="replaced"), rpc=rpc)]
        )

        @contextmanager
        def native_client():
            yield next(connections)

        monkeypatch.setattr(tui.daemon, "client", native_client)

    response = _delegated_manager_prompt(
        monkeypatch, seconds=0.8 if disposition == "wrong-receipt" else 0.12
    )
    expected = {
        "queued": "queued",
        "running": "handed_off",
        "wrong-receipt": "queued",
        "lost-ack": "uncertain",
    }
    assert response["delivery_state"] == expected[disposition]
    assert response["success"] is (disposition != "lost-ack")
    assert calls.count("prompt.submit") == 1
    active = observe_owner_prompt(tui.manifest_path, "managed-generation")
    assert active is not None and active.request_id == response["request_id"]
    assert active.state == ("uncertain" if disposition == "lost-ack" else "handed_off")


@pytest.mark.parametrize(
    ("native_outcome", "delivery"), [("failed", "failed"), ("cancelled", "interrupted")]
)
def test_manager_reports_the_attributable_native_terminal_disposition(
    tui, monkeypatch, hermes_owner_queue, manager_target, native_outcome, delivery
) -> None:
    """Project native failure and cancellation as supported terminal outcomes."""

    identity = _instance(tui)
    calls = []

    def rpc(method, **params):
        calls.append(method)
        assert params["session_id"] == tui.state.native_session_id
        return _receipt(tui, identity, "terminal", outcome=native_outcome)

    _install_peer(monkeypatch, tui, SimpleNamespace(identity=identity, rpc=rpc))
    result = _local_manager_prompt()
    assert result.exit_code == 0, result.output
    response = json.loads(result.output)

    assert response["success"] is False and response["delivery_state"] == delivery
    assert calls == ["prompt.submit", "prompt.receipt"]
    with sqlite3.connect(hermes_owner_queue) as connection:
        assert connection.execute(
            "SELECT request_id, state FROM managed_prompt_attempts"
        ).fetchall() == [(response["request_id"], delivery)]


def test_durable_queue_receipt_recovers_an_unwritten_handoff(
    tui, monkeypatch, hermes_owner_queue, manager_target
) -> None:
    """Keep a verified admission recoverable when the SQLite handoff write is busy."""

    identity = _instance(tui)
    calls = []

    def rpc(method, **params):
        calls.append(method)
        if method == "prompt.submit":
            return _receipt(tui, identity, "queued")
        if method == "prompt.receipt":
            assert params["admission_id"] == "native-admission"
            return _receipt(tui, identity, "terminal", outcome="completed")
        assert method == "session.events.since"
        return {"replay_epoch": "replay-one", "latest_seq": 1, "events": []}

    def busy_handoff(_claim):
        raise OwnerAdmissionError("unavailable", "The owner ledger is busy.")

    _install_peer(monkeypatch, tui, SimpleNamespace(identity=identity, rpc=rpc))
    monkeypatch.setattr(owner_admission.OwnerPromptClaim, "handoff", busy_handoff)
    monkeypatch.setattr(hermes_tui, "_TURN_TIMEOUT", 0)
    result = _local_manager_prompt()
    assert result.exit_code == 0, result.output
    response = json.loads(result.output)
    assert response["delivery_state"] == "queued" and response["success"] is True
    active = observe_owner_prompt(tui.manifest_path, "managed-generation")
    assert active is not None and active.request_id == response["request_id"]
    assert active.state == "reserved"

    assert (
        observe_owner_prompt(
            tui.manifest_path, "managed-generation", reconcile_tui=tui.reconcile_owner_attempt
        )
        is None
    )
    assert calls == ["prompt.submit", "prompt.receipt", "session.events.since"]
    with sqlite3.connect(hermes_owner_queue) as connection:
        assert connection.execute(
            "SELECT request_id, state FROM managed_prompt_attempts"
        ).fetchall() == [(response["request_id"], "completed")]


@pytest.mark.parametrize("bad_receipt", ["partial", "missing-sequence", "other-session", "json"])
def test_owner_and_backend_keep_unresolved_slot_until_exact_terminal_evidence(
    tui: HermesTuiSession,
    monkeypatch: pytest.MonkeyPatch,
    hermes_owner_queue: Path,
    bad_receipt: str,
) -> None:
    """An invalid terminal receipt cannot release the slot or trigger prompt replay."""

    identity = _instance(tui)
    calls = []

    def rpc(method, **_params):
        calls.append(method)
        assert method == "prompt.submit"
        return _receipt(tui, identity, "queued")

    peer = SimpleNamespace(identity=identity, rpc=rpc)
    _install_peer(monkeypatch, tui, peer)
    generation, request_id = "managed-generation", "original-request"
    queued = tui.submit_native_prompt("literal", request_id=request_id)
    assert queued.status == "queued"
    path = tui._turn_path(request_id)
    terminal = queued.model_copy(
        update={
            "status": "completed",
            "native_outcome": "completed",
            "native_execution_generation": 3,
        }
    ).model_dump(mode="json")
    if bad_receipt == "partial":
        write_hermes_evidence(
            path,
            {
                key: terminal[key]
                for key in (
                    "request_id",
                    "generation_id",
                    "native_session_id",
                    "native_admission_id",
                    "status",
                )
            },
        )
    elif bad_receipt == "missing-sequence":
        write_hermes_evidence(
            path,
            {key: value for key, value in terminal.items() if key != "native_admission_sequence"},
        )
    elif bad_receipt == "other-session":
        write_hermes_evidence(path, {**terminal, "native_session_id": "different-native-session"})
    else:
        path.write_text("{malformed JSON")

    with sqlite3.connect(hermes_owner_queue) as connection:
        connection.execute(
            "UPDATE managed_prompt_attempts SET caller_birth_token='disconnected' WHERE request_id=?",
            (request_id,),
        )
    assert tui.read_native_admission(request_id) is None
    unresolved = observe_owner_prompt(
        tui.manifest_path, generation, reconcile_tui=tui.reconcile_owner_attempt
    )
    assert unresolved is not None and unresolved.request_id == request_id
    assert unresolved.state == "uncertain"
    with pytest.raises(OwnerAdmissionError, match="unresolved"):
        tui.submit_native_prompt("next", request_id="next-request")
    assert calls == ["prompt.submit"]

    write_hermes_evidence(path, terminal)
    recovered = tui.read_native_admission(request_id)
    assert recovered is not None and recovered.terminal_outcome == "completed"
    assert observe_owner_prompt(tui.manifest_path, generation) is None
    with sqlite3.connect(hermes_owner_queue) as connection:
        assert connection.execute(
            "SELECT request_id, state, evidence FROM managed_prompt_attempts"
        ).fetchall() == [(request_id, "completed", "tui_native")]
    assert calls == ["prompt.submit"]


def test_owner_keeps_queued_hermes_receipt_until_native_terminal_update(
    tui: HermesTuiSession, monkeypatch: pytest.MonkeyPatch, hermes_owner_queue: Path
) -> None:
    """Native rereads keep the original admission until its durable outcome changes."""

    identity = _instance(tui)
    calls = []
    status = "queued"

    def rpc(method, **params):
        calls.append(method)
        if method == "prompt.submit":
            return _receipt(tui, identity, "queued")
        if method == "prompt.receipt":
            assert params["admission_id"] == "native-admission"
            if status == "queued":
                return _receipt(tui, identity, "queued")
            return _receipt(tui, identity, "terminal", outcome="failed")
        assert method == "session.events.since"
        return {"replay_epoch": "replay-one", "latest_seq": 1, "events": []}

    _install_peer(monkeypatch, tui, SimpleNamespace(identity=identity, rpc=rpc))
    generation, request_id = "managed-generation", "original-request"
    queued = tui.submit_native_prompt("literal", request_id=request_id)
    pending = observe_owner_prompt(
        tui.manifest_path, generation, reconcile_tui=tui.reconcile_owner_attempt
    )
    assert (
        pending is not None and pending.request_id == request_id and pending.state == "handed_off"
    )
    assert tui.read_native_admission(request_id) == queued
    with pytest.raises(OwnerAdmissionError, match="unresolved"):
        reserve_owner_prompt(tui.manifest_path, generation, origin="manager")
    status = "failed"
    assert (
        observe_owner_prompt(
            tui.manifest_path, generation, reconcile_tui=tui.reconcile_owner_attempt
        )
        is None
    )
    with sqlite3.connect(hermes_owner_queue) as connection:
        assert connection.execute(
            "SELECT request_id, state, evidence FROM managed_prompt_attempts"
        ).fetchall() == [(request_id, "failed", "tui_native")]
    assert calls.count("prompt.submit") == 1


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
