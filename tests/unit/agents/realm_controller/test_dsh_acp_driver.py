"""Verify exact continuation and native handoff in isolated ACP subprocesses."""

from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import threading

import pytest

from houmao.agents.realm_controller.backends.dsh_acp_connection import (
    DshAcpProtocolError,
    DshAcpRequestError,
)
from houmao.agents.realm_controller.backends.dsh_acp_driver import (
    DshAcpInvocation,
    run_dsh_acp_turn,
)


PEER = """
import json, os, sys
from pathlib import Path
control = json.loads(Path(os.environ['FAKE_CONTROL']).read_text())
native = control['native_session_id']
model_value = json.dumps(['controlled-route', 'initial'])
sequence = 0
def options():
    return [{'id':'model', 'type':'select', 'currentValue':model_value,
             'options':[{'group':'controlled-route', 'options':[
                 {'value':json.dumps(['controlled-route', name]), 'name':name}
                 for name in ['initial', 'override']]}]}]
def evidence(event, **fields):
    global sequence
    row = {**control, 'version':1, 'event':event, 'sequence':sequence,
           'process_id':os.getpid(), 'host_incarnation':'host-a',
           'agent_incarnation':None if event=='loaded' else 'agent-a', **fields}
    with Path(control['evidence_path']).open('a') as out:
        out.write(json.dumps(row)+'\\n')
    sequence += 1
def send(frame):
    print(json.dumps({'jsonrpc':'2.0', **frame}), flush=True)
evidence('loaded', native_session_id=None)
for line in sys.stdin:
    frame = json.loads(line)
    method = frame['method']
    params = frame.get('params', {})
    if method=='initialize':
        send({'id':frame['id'], 'result':{'protocolVersion':1,
            'agentInfo':{'name':'deepseek-harness-acp','version':'0.0.1'},
            'agentCapabilities':{'sessionCapabilities':{'close':{},'resume':{}}}}})
    elif method in ('session/new','session/resume'):
        if method=='session/resume' and params['sessionId'] != native:
            send({'id':frame['id'],'error':{'code':-32602,'message':'missing session'}})
            continue
        evidence('created')
        send({'id':frame['id'], 'result':{'sessionId':native, 'configOptions':options()}})
    elif method=='session/set_config_option':
        assert params['sessionId']==native
        assert params['configId']=='model'
        model_value=params['value']
        send({'id':frame['id'], 'result':{'configOptions':options()}})
    elif method=='session/prompt':
        binding = json.loads(Path(control['binding_path']).read_text())
        assert binding['native_session_id']==native
        if os.environ.get('FAKE_EXPECT_MODEL'):
            assert json.loads(model_value)==['controlled-route', os.environ['FAKE_EXPECT_MODEL']]
        if os.environ.get('FAKE_FAIL_BEFORE_ADMISSION'):
            sys.exit(1)
        evidence('admitted', message_id='message-a')
        if os.environ.get('FAKE_DIE_AT')=='admission':
            sys.exit(1)
        evidence('claimed', message_id='message-a', turn=1)
        if os.environ.get('FAKE_DIE_AT')=='claim':
            sys.exit(1)
        send({'method':'session/update','params':{'sessionId':'unrelated', 'update':{'text':'unrelated'}}})
        send({'method':'session/update','params':{'sessionId':native,'update':{'sessionUpdate':'agent_message_chunk','content':{'type':'text','text':'hello'}}}})
        if os.environ.get('FAKE_WAIT_FOR_CANCEL'):
            cancel = json.loads(input())
            assert cancel['method']=='session/cancel'
            reason = 'cancelled'
        else:
            reason = os.environ.get('FAKE_STOP_REASON','end_turn')
        send({'id':frame['id'],'result':{'stopReason':reason}})
    elif method=='session/close':
        if os.environ.get('FAKE_CLOSE_ERROR'):
            send({'id':frame['id'], 'error':{'code':-32603, 'message':'controlled persistence failure'}})
            continue
        send({'id':frame['id'],'result':{}})
"""


def _invocation(tmp_path: Path, attempt: str = "attempt-a") -> DshAcpInvocation:
    """Create private run inputs and a peer that writes bound native receipts."""

    turn_dir = tmp_path / attempt
    turn_dir.mkdir()
    control = {
        "attempt_id": attempt,
        "runtime_session_id": "runtime-a",
        "generation": "generation-a",
        "native_session_id": "native-a",
        "evidence_path": str(turn_dir / "dsh-native-evidence.jsonl"),
        "binding_path": str(turn_dir / "dsh-native-binding.json"),
    }
    control_path = turn_dir / "peer-control.json"
    control_path.write_text(json.dumps(control))
    return DshAcpInvocation(
        command=(sys.executable, "-u", "-c", PEER),
        working_directory=tmp_path,
        environment={**os.environ, "FAKE_CONTROL": str(control_path)},
        prompt="exercise the native interval",
        session_id=None,
        attempt_id=attempt,
        runtime_session_id="runtime-a",
        generation="generation-a",
        turn_dir=turn_dir,
        lock_path=tmp_path / "invocation.lock",
        evidence_path=turn_dir / "dsh-native-evidence.jsonl",
        setup_timeout=2,
        close_timeout=0.2,
    )


def test_two_workers_preserve_exact_session_and_separate_raw_frames(tmp_path: Path) -> None:
    """Each turn closes its worker and the next selects the saved exact identity."""

    observed: list[dict[str, object]] = []
    admissions: list[str] = []
    first = _invocation(tmp_path)
    outcome = run_dsh_acp_turn(
        first,
        emit=observed.append,
        interrupted=threading.Event(),
        confirmed=lambda: admissions.append("first"),
    )
    second = replace(_invocation(tmp_path, "attempt-b"), session_id=outcome.session_id)
    result = run_dsh_acp_turn(
        second,
        emit=observed.append,
        interrupted=threading.Event(),
        confirmed=lambda: admissions.append("second"),
    )
    assert result.session_id == "native-a"
    assert result.stop_reason == "end_turn"
    assert admissions == ["first", "second"]
    assert all(event["session_id"] == "native-a" for event in observed)
    raw = (first.turn_dir / "provider-stdout.jsonl").read_text()
    assert '"sessionId": "unrelated"' in raw
    assert all("jsonrpc" not in event for event in observed)
    assert (first.turn_dir / "dsh-native-binding.json").stat().st_mode & 0o777 == 0o600


def test_missing_resume_does_not_create_replacement_or_claim_handoff(tmp_path: Path) -> None:
    """A failed exact continuation has no fallback to new or latest."""

    invocation = replace(_invocation(tmp_path), session_id="missing-native")
    admissions: list[bool] = []
    with pytest.raises(DshAcpRequestError):
        run_dsh_acp_turn(
            invocation,
            emit=lambda event: None,
            interrupted=threading.Event(),
            confirmed=lambda: admissions.append(True),
        )
    assert not admissions
    assert not (invocation.turn_dir / "dsh-native-binding.json").exists()


def test_worker_failure_before_admission_never_confirms_helper_launch(tmp_path: Path) -> None:
    """Starting the helper and native worker does not prove input admission."""

    invocation = _invocation(tmp_path)
    invocation.environment["FAKE_FAIL_BEFORE_ADMISSION"] = "1"
    admissions: list[bool] = []
    with pytest.raises(DshAcpProtocolError):
        run_dsh_acp_turn(
            invocation,
            emit=lambda event: None,
            interrupted=threading.Event(),
            confirmed=lambda: admissions.append(True),
        )
    assert not admissions
    assert (invocation.turn_dir / "dsh-native-binding.json").exists()


@pytest.mark.parametrize("reason", ["max_tokens", "refusal", "cancelled"])
def test_native_incomplete_reason_is_preserved(tmp_path: Path, reason: str) -> None:
    """The managed result can distinguish each non-completed native outcome."""

    invocation = _invocation(tmp_path)
    invocation.environment["FAKE_STOP_REASON"] = reason
    outcome = run_dsh_acp_turn(
        invocation,
        emit=lambda event: None,
        interrupted=threading.Event(),
        confirmed=lambda: None,
    )
    assert outcome.stop_reason == reason


def test_explicit_interrupt_sends_native_cancel_and_waits_for_settlement(tmp_path: Path) -> None:
    """Cancellation remains serviceable while the original prompt is pending."""

    invocation = _invocation(tmp_path)
    invocation.environment["FAKE_WAIT_FOR_CANCEL"] = "1"
    interruption = threading.Event()

    def observe(event: dict[str, object]) -> None:
        """Request interruption after observing the admitted native activity."""

        if event["type"] == "session_update":
            interruption.set()

    outcome = run_dsh_acp_turn(
        invocation,
        emit=observe,
        interrupted=interruption,
        confirmed=lambda: None,
    )
    assert outcome.stop_reason == "cancelled"


def test_stale_native_receipt_cannot_confirm_new_attempt(tmp_path: Path) -> None:
    """A sidecar copied from another attempt fails binding validation."""

    invocation = _invocation(tmp_path)
    control = Path(invocation.environment["FAKE_CONTROL"])
    payload = json.loads(control.read_text())
    payload["generation"] = "older-generation"
    control.write_text(json.dumps(payload))
    with pytest.raises(DshAcpProtocolError, match="invocation"):
        run_dsh_acp_turn(
            invocation,
            emit=lambda event: None,
            interrupted=threading.Event(),
            confirmed=lambda: None,
        )


def test_exact_resume_applies_explicit_native_model_before_prompt(tmp_path: Path) -> None:
    """A resumed selection changes through advertised ACP options before work."""

    invocation = replace(
        _invocation(tmp_path), session_id="native-a", model=("controlled-route", "override")
    )
    invocation.environment["FAKE_EXPECT_MODEL"] = "override"
    outcome = run_dsh_acp_turn(
        invocation, emit=lambda event: None, interrupted=threading.Event(), confirmed=lambda: None
    )
    assert outcome.stop_reason == "end_turn"


def test_unadvertised_model_refuses_without_native_input(tmp_path: Path) -> None:
    """Missing exact catalog entries preserve identity and never submit a prompt."""

    invocation = replace(_invocation(tmp_path), model=("other-route", "override"))
    with pytest.raises(DshAcpProtocolError, match="native catalog"):
        run_dsh_acp_turn(
            invocation,
            emit=lambda event: None,
            interrupted=threading.Event(),
            confirmed=lambda: pytest.fail("no native admission"),
        )
    assert (invocation.turn_dir / "dsh-native-binding.json").is_file()
    evidence = invocation.evidence_path.read_text()
    assert '"event": "admitted"' not in evidence


def test_flush_failure_retains_observed_native_outcome(tmp_path: Path) -> None:
    """A successful prompt result remains distinct from failed native closure."""

    invocation = _invocation(tmp_path)
    invocation.environment["FAKE_CLOSE_ERROR"] = "1"
    events: list[dict[str, object]] = []
    with pytest.raises(DshAcpRequestError):
        run_dsh_acp_turn(
            invocation, emit=events.append, interrupted=threading.Event(), confirmed=lambda: None
        )
    results = [event for event in events if event["type"] == "native_result"]
    assert len(results) == 1 and results[0]["stop_reason"] == "end_turn"


@pytest.mark.parametrize("boundary", ["admission", "claim"])
def test_abrupt_native_death_retains_identity_without_replaying_input(
    tmp_path: Path, boundary: str
) -> None:
    """Death before or after claim preserves evidence and never starts replacement work."""

    invocation = _invocation(tmp_path)
    invocation.environment["FAKE_DIE_AT"] = boundary
    with pytest.raises(DshAcpProtocolError):
        run_dsh_acp_turn(
            invocation,
            emit=lambda event: None,
            interrupted=threading.Event(),
            confirmed=lambda: None,
        )
    binding = json.loads((invocation.turn_dir / "dsh-native-binding.json").read_text())
    assert binding["native_session_id"] == "native-a"
    rows = [json.loads(line) for line in invocation.evidence_path.read_text().splitlines()]
    assert len([row for row in rows if row["event"] == "admitted"]) == 1
    assert len([row for row in rows if row["event"] == "claimed"]) == (boundary == "claim")
    assert (invocation.turn_dir / "provider-stderr.log").stat().st_mode & 0o777 == 0o600
