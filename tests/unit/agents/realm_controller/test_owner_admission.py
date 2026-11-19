"""Check cross-caller prompt ownership and durable handoff evidence."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
from threading import Barrier
from types import SimpleNamespace

import pytest

from houmao.agents.realm_controller import owner_admission
from houmao.agents.realm_controller.owner_admission import (
    OwnerAdmissionError,
    OwnerPromptClaim,
    exact_web_prompt_result,
    observe_owner_prompt,
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
