"""Check cross-caller prompt ownership and durable handoff evidence."""

from concurrent.futures import ThreadPoolExecutor
import json
from multiprocessing import get_context
from multiprocessing.connection import Connection
import os
from pathlib import Path
import sqlite3
from threading import Barrier
from types import SimpleNamespace
from typing import Literal
from unittest.mock import patch

import pytest

from houmao.agents.realm_controller import owner_admission
from houmao.agents.realm_controller.owner_admission import (
    OwnerAdmissionError,
    OwnerMaintenanceClaim,
    OwnerPromptClaim,
    ensure_owner_input_allowed,
    exact_web_prompt_result,
    guard_owner_operation,
    load_owner_maintenance,
    observe_owner_maintenance,
    observe_owner_prompt,
    owner_process_has_exited,
    reserve_owner_maintenance,
    reserve_owner_prompt,
)


@pytest.fixture
def manifest_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Supply a private queue and substitute the separately tested owner verifier."""

    gateway = tmp_path / "gateway"
    gateway.mkdir()
    with sqlite3.connect(gateway / "queue.sqlite"):
        pass
    monkeypatch.setattr(
        owner_admission,
        "_owner_manifest",
        lambda _path, _generation: SimpleNamespace(
            mode="headless", backend="kimi_headless", headless=None
        ),
    )
    return tmp_path / "manifest.json"


def test_two_callers_reserve_only_one_native_attempt(manifest_path: Path) -> None:
    """Manager and gateway callers contend for the same durable slot."""

    start = Barrier(2)

    def reserve(origin: str) -> OwnerPromptClaim | str:
        start.wait(timeout=2)
        try:
            return reserve_owner_prompt(manifest_path, "generation", origin=origin)
        except OwnerAdmissionError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(reserve, ("manager", "gateway")))
    claims = [claim for claim in outcomes if isinstance(claim, OwnerPromptClaim)]
    assert len(claims) == 1
    assert "not_ready" in outcomes
    active = observe_owner_prompt(manifest_path, "generation")
    assert active is not None and active.request_id == claims[0].request_id
    assert active.state == "reserved"
    claims[0].handoff()
    active = observe_owner_prompt(manifest_path, "generation")
    assert active is not None and active.state == "handed_off"
    claims[0].finish("completed", evidence="headless_artifacts")
    assert observe_owner_prompt(manifest_path, "generation") is None


def test_disconnected_turn_cannot_be_retaken_without_exact_native_evidence(
    manifest_path: Path,
) -> None:
    """Caller loss leaves an uncertain attempt, even if the native process was unseen."""

    claim = reserve_owner_prompt(manifest_path, "generation", origin="gateway")
    claim.handoff()
    database = manifest_path.parent / "gateway" / "queue.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE managed_prompt_attempts SET caller_birth_token='previous-process'"
        )
    active = observe_owner_prompt(manifest_path, "generation")
    assert active is not None and active.state == "uncertain"
    with pytest.raises(OwnerAdmissionError) as exc:
        reserve_owner_prompt(manifest_path, "generation", origin="manager")
    assert exc.value.code == "uncertain"
    active.turn_dir.mkdir(parents=True)
    (active.turn_dir / "exitcode").write_text("0\n")
    still_unproven = observe_owner_prompt(manifest_path, "generation")
    assert still_unproven is not None and still_unproven.state == "uncertain"
    (active.turn_dir / "exitcode").write_text("1\n")
    assert observe_owner_prompt(manifest_path, "generation") is None
    with pytest.raises(OwnerAdmissionError) as exc:
        reserve_owner_prompt(
            manifest_path, "generation", request_id=claim.request_id, origin="manager"
        )
    assert exc.value.code == "duplicate_request"


def test_explicit_web_queueing_and_ordinary_work_share_native_owner(
    manifest_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit native queuing requires handoff and keeps the ordinary slot closed."""

    monkeypatch.setattr(owner_admission, "_owner_manifest", lambda *_: SimpleNamespace(mode="web"))
    first = reserve_owner_prompt(manifest_path, "generation", origin="gateway_web")
    with pytest.raises(OwnerAdmissionError, match="unresolved"):
        reserve_owner_prompt(manifest_path, "generation", origin="gateway_deferred")
    first.handoff()
    queued = reserve_owner_prompt(manifest_path, "generation", origin="gateway_deferred")
    queued.handoff()
    first.finish("completed", evidence="web_native")
    with pytest.raises(OwnerAdmissionError, match="unresolved"):
        reserve_owner_prompt(manifest_path, "generation", origin="manager")
    queued.finish("completed", evidence="web_native")
    assert observe_owner_prompt(manifest_path, "generation") is None


def _owner_child(
    sender: Connection,
    manifest_path: Path,
    operation: Literal["prompt", "maintenance", "handoff"],
) -> None:
    """Exercise owner admission under a new process birth identity."""

    with (
        sender,
        patch.object(
            owner_admission,
            "_owner_manifest",
            return_value=SimpleNamespace(mode="web", backend="dsh_web", backend_state={}),
        ),
    ):
        try:
            if operation == "prompt":
                result: str | OwnerMaintenanceClaim | OwnerPromptClaim = reserve_owner_prompt(
                    manifest_path, "generation", origin="manager"
                )
            else:
                result = reserve_owner_maintenance(
                    manifest_path, "generation", operation_id="child-publish"
                )
                if operation == "handoff":
                    result.handoff()
        except OwnerAdmissionError as exc:
            result = exc.code
        sender.send(result)


def _run_owner_child(
    manifest_path: Path, operation: Literal["prompt", "maintenance", "handoff"]
) -> str | OwnerMaintenanceClaim | OwnerPromptClaim:
    """Run one guarded operation in a distinct process and await its outcome."""

    context = get_context("fork")
    receiver, sender = context.Pipe(duplex=False)
    child = context.Process(target=_owner_child, args=(sender, manifest_path, operation))
    with receiver, sender:
        child.start()
        try:
            assert receiver.poll(8)
            outcome = receiver.recv()
            child.join(timeout=4)
            assert child.exitcode == 0
            assert isinstance(outcome, (str, OwnerMaintenanceClaim, OwnerPromptClaim))
            return outcome
        finally:
            if child.is_alive():
                child.kill()
                child.join(timeout=4)
            child.close()


def test_prompt_admission_precedes_publication_in_another_process(manifest_path: Path) -> None:
    """A direct manager prompt reserves first, so a gateway publisher must wait."""

    prompt = reserve_owner_prompt(manifest_path, "generation", origin="manager")
    assert _run_owner_child(manifest_path, "maintenance") == "not_ready"
    assert observe_owner_maintenance(manifest_path, "generation") is None
    prompt.finish("completed")
    claim = _run_owner_child(manifest_path, "maintenance")
    assert isinstance(claim, OwnerMaintenanceClaim)
    assert claim.finish(evidence="readiness_proved_no_effect", settled=True, ready=True)


def test_publication_admission_precedes_prompt_and_lifecycle(manifest_path: Path) -> None:
    """A durable publication claim refuses ordinary input before it reaches the target."""

    claim = reserve_owner_maintenance(manifest_path, "generation", operation_id="publisher")
    assert _run_owner_child(manifest_path, "prompt") == "not_ready"
    with pytest.raises(OwnerAdmissionError, match="unresolved maintenance"):
        with guard_owner_operation(manifest_path, "generation"):
            pytest.fail("Immediate owner operation bypassed maintenance")
    with pytest.raises(OwnerAdmissionError, match="unresolved maintenance"):
        with guard_owner_operation(manifest_path, "generation", recover_lost_maintenance=True):
            pytest.fail("Lifecycle recovery fenced a live caller")
    claim.release_before_handoff(evidence="native_refused")
    prompt = _run_owner_child(manifest_path, "prompt")
    assert isinstance(prompt, OwnerPromptClaim)


def test_immediate_owner_operations_can_overlap_and_exclude_publication(
    manifest_path: Path,
) -> None:
    """An interrupt can overlap a prompt while both exclude maintenance."""

    def interrupt() -> None:
        """Acquire ordinary admission on an independent native-effect thread."""

        with guard_owner_operation(manifest_path, "generation"):
            pass

    with guard_owner_operation(manifest_path, "generation"):
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(interrupt).result(timeout=2)
        assert _run_owner_child(manifest_path, "maintenance") == "not_ready"


def test_missing_birth_observation_cannot_fence_a_live_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A visible process with unreadable identity remains unsafe to supersede."""

    monkeypatch.setattr(owner_admission, "_dispatch_origin_birth_token", lambda _: None)
    assert not owner_process_has_exited(os.getpid(), "proc:0")


def test_pre_handoff_uncertainty_retains_admission_until_exact_reconciliation(
    manifest_path: Path,
) -> None:
    """Only the original caller can end a live reservation without resuming its effect."""

    prior = _run_owner_child(manifest_path, "maintenance")
    assert isinstance(prior, OwnerMaintenanceClaim)
    prior.retain_before_handoff(evidence="other_process_cannot_change_reservation")
    assert prior.state() == "reserved"
    assert prior.finish(evidence="prior_process_settled", settled=True, ready=True)

    claim = reserve_owner_maintenance(manifest_path, "generation", operation_id="publisher")
    claim.retain_before_handoff(evidence="native_close_unconfirmed")
    assert claim.state() == "uncertain"
    assert not claim.active()
    with pytest.raises(OwnerAdmissionError) as handoff:
        claim.handoff()
    assert handoff.value.code == "duplicate_request"
    with pytest.raises(OwnerAdmissionError) as prompt:
        reserve_owner_prompt(manifest_path, "generation", origin="manager")
    assert prompt.value.code == "uncertain"
    assert not claim.finish(evidence="native_still_unready", settled=True, ready=False)
    assert claim.finish(evidence="native_settled_and_ready", settled=True, ready=True)
    assert observe_owner_maintenance(manifest_path, "generation") is None


def test_lost_maintenance_can_settle_without_dispatching_again(manifest_path: Path) -> None:
    """Reattachment observes the same claim and must prove readiness as well as settlement."""

    claim = _run_owner_child(manifest_path, "handoff")
    assert isinstance(claim, OwnerMaintenanceClaim)
    loaded = load_owner_maintenance(manifest_path, "generation", claim.operation_id)
    assert loaded == claim
    assert observe_owner_maintenance(manifest_path, "generation") == claim
    assert not claim.active()
    assert claim.state() == "handed_off"
    with pytest.raises(OwnerAdmissionError) as exc:
        reserve_owner_prompt(manifest_path, "generation", origin="manager")
    assert exc.value.code == "uncertain"
    with pytest.raises(OwnerAdmissionError) as exc:
        claim.handoff()
    assert exc.value.code == "duplicate_request"
    assert not claim.finish(evidence="settled_but_unready", settled=True, ready=False)
    assert claim.state() == "uncertain"
    assert observe_owner_maintenance(manifest_path, "generation") == claim
    assert claim.finish(evidence="confirmed_native_readiness", settled=True, ready=True)
    assert observe_owner_maintenance(manifest_path, "generation") is None


def test_owner_lifecycle_recovery_fences_only_lost_generation(manifest_path: Path) -> None:
    """Late completion may not take or release the replacement owner's slot."""

    old = _run_owner_child(manifest_path, "handoff")
    assert isinstance(old, OwnerMaintenanceClaim)
    with guard_owner_operation(
        manifest_path, "generation", recover_lost_maintenance=True
    ) as recovering:
        assert recovering == old
        assert recovering is not None
        recovering.fence_after_recovery()
    replacement = reserve_owner_maintenance(
        manifest_path, "replacement", operation_id=old.operation_id
    )
    assert not old.finish(evidence="late_native_receipt", settled=True, ready=True)
    assert old.state() == "fenced"
    assert replacement.active()
    assert observe_owner_maintenance(manifest_path, "replacement") == replacement


def test_native_refusal_and_accepted_gateway_queue_leave_no_maintenance(
    manifest_path: Path,
) -> None:
    """An immediate readiness refusal and queued work both release pre-effect admission."""

    def refuse() -> None:
        """Report busy before any effect has been authorized or started."""

        raise OwnerAdmissionError("not_ready", "Native maintenance is busy.")

    with pytest.raises(OwnerAdmissionError, match="Native maintenance is busy"):
        reserve_owner_maintenance(
            manifest_path, "generation", operation_id="publisher", readiness=refuse
        )
    assert observe_owner_maintenance(manifest_path, "generation") is None

    database = manifest_path.parent / "gateway" / "queue.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE gateway_requests (state TEXT NOT NULL)")
        connection.execute("INSERT INTO gateway_requests VALUES ('accepted')")
    with pytest.raises(OwnerAdmissionError, match="pending gateway requests"):
        reserve_owner_maintenance(manifest_path, "generation", operation_id="publisher")
    assert observe_owner_maintenance(manifest_path, "generation") is None
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM gateway_requests")
    guard = reserve_owner_maintenance(manifest_path, "generation", operation_id="publisher")
    with sqlite3.connect(database) as connection:
        connection.execute("BEGIN IMMEDIATE")
        with pytest.raises(OwnerAdmissionError, match="unresolved maintenance"):
            ensure_owner_input_allowed(connection, manifest_path, "generation")
    guard.release_before_handoff(evidence="test_finished")


def test_web_terminal_projection_requires_exact_operation_and_native_turn(tmp_path: Path) -> None:
    """Only a matching Web receipt can settle its AG-UI operation."""

    identity = {
        "protocol_version": 1,
        "agent_id": "agent",
        "runtime_session_id": "runtime",
        "generation": "generation",
        "host_incarnation": "host",
        "agent_incarnation": "body",
        "native_session_id": "session",
    }
    path = tmp_path / "web-result.json"
    evidence = {
        "operation_id": "request",
        "outcome": "completed",
        "identity": identity,
        "receipt": {
            "operation_id": "request",
            "status": "terminal",
            "identity": identity,
            "turns": [8],
        },
    }
    path.write_text(json.dumps(evidence))
    assert exact_web_prompt_result(tmp_path, "request", "stale") is None
    assert exact_web_prompt_result(tmp_path, "different", "generation") is None
    assert exact_web_prompt_result(tmp_path, "request", "generation") == {
        "operation_id": "request",
        "outcome": "completed",
        "source": "web_native",
        "native_session_id": "session",
        "native_turn_ids": ["8"],
        "identity": identity,
    }
    evidence["receipt"]["turns"] = []
    path.write_text(json.dumps(evidence))
    assert exact_web_prompt_result(tmp_path, "request", "generation") is None
