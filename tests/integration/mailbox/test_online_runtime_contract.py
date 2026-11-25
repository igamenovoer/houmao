"""Real body/gateway/provider processes preserve online lifecycle boundaries."""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from typing import Any

import httpx
import pytest
import uvicorn

from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime, create_app
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    mutate_session_mailbox_binding,
    update_session_manifest,
)
from houmao.mailbox.notifier_admission import ReminderOrigin, admit_mail_reminder
from houmao.mailbox.observation import observe_online, read_online_sync_status
from houmao.mailbox.online_models import OnlineAuthorityContext
from tests.fixtures.gateway_access import configure_fixture_gateway_access, self_fixture_auth
from tests.unit.agents.realm_controller.test_gateway_dual_mail import _runtime
from tests.unit.agents.realm_controller.test_gateway_support import _sample_cao_plan_with_mailbox
from tests.unit.mailbox.test_stalwart_jmap import _WireState, wire as wire


@contextmanager
def _body(root: Path) -> Iterator[tuple[subprocess.Popen[bytes], Path, dict[str, Any]]]:
    """Run an isolated fake agent whose PID and conversation survive gateway changes."""
    program = root / "fake_body.py"
    marker = root / "body-state.json"
    program.write_text(
        "import json,os,pathlib,sys,time\npathlib.Path(sys.argv[1]).write_text(json.dumps({'pid':os.getpid(),'conversation':'unchanged-conversation-marker'}))\nwhile True: time.sleep(0.1)\n"
    )
    process = subprocess.Popen(
        [sys.executable, str(program), str(marker)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 5
    try:
        while not marker.exists() and time.monotonic() < deadline:
            assert process.poll() is None
            time.sleep(0.01)
        snapshot = json.loads(marker.read_text())
        assert snapshot["pid"] == process.pid
        yield process, marker, snapshot
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@contextmanager
def _gateway(runtime: GatewayServiceRuntime) -> Iterator[Any]:
    """Run the real loopback HTTP facade and workers with finite teardown."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    runtime.set_listener(host="127.0.0.1", port=port)
    # The body is an explicit subprocess rather than a tmux CLI. No TUI polling is needed.
    runtime._start_tui_tracking_locked = lambda: None  # type: ignore[method-assign]
    runtime.start()
    server = uvicorn.Server(
        uvicorn.Config(create_app(runtime=runtime), log_level="error", access_log=False)
    )
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    try:
        while not server.started and time.monotonic() < deadline:
            assert thread.is_alive()
            time.sleep(0.01)
        assert server.started

        with httpx.Client(
            base_url=runtime.owner_connect_url,
            auth=self_fixture_auth(runtime),
            timeout=15,
            trust_env=False,
        ) as client:

            def request(
                method: str, path: str, payload: dict[str, Any] | None = None
            ) -> tuple[int, dict[str, Any]]:
                """Use actual HTTP and preserve structured non-success responses."""

                response = client.request(method, path, json=payload)
                return response.status_code, response.json()

            assert request("GET", "/health")[0] == 200
            yield request
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        runtime.shutdown()
        listener.close()
        assert not thread.is_alive()


def _context(runtime: GatewayServiceRuntime) -> OnlineAuthorityContext:
    """Read owner/session authority from the persisted manifest."""
    assert runtime.m_manifest_path is not None
    payload = load_session_manifest(runtime.m_manifest_path).payload
    return OnlineAuthorityContext(
        runtime.m_manifest_path, payload["agent_id"], payload["runtime"]["session_id"]
    )


def _authorized_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GatewayServiceRuntime:
    """Give the synthetic body its real, independently stored fixture credentials."""

    configure_fixture_gateway_access(tmp_path, monkeypatch)
    return _runtime(tmp_path, monkeypatch, dual=False, enabled=False)


def _attach(
    request: Any, state: _WireState, source: Path, revision: str, **kwargs: Any
) -> tuple[int, dict[str, Any]]:
    """Attach an explicitly selected normal account without management access."""
    return request(
        "PUT",
        "/v1/mail/online/binding",
        {
            "expected_revision": revision,
            "address": "alice@example.test",
            "login_identity": "login-is-not-address",
            "credential_source_ref": str(source),
            "jmap_url": state.url + "/.well-known/jmap",
            **kwargs,
        },
    )


def _assert_body(process: subprocess.Popen[bytes], marker: Path, expected: dict[str, Any]) -> None:
    """Check the actual process and its persisted conversation marker."""
    assert process.poll() is None
    os.kill(process.pid, 0)
    assert json.loads(marker.read_text()) == expected


def test_disabled_running_body_attaches_refreshes_restarts_and_detaches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wire: tuple[_WireState, Path]
) -> None:
    state, source = wire
    state.state = "stable-state"
    state.changes = {
        "oldState": "stable-state",
        "newState": "stable-state",
        "hasMoreChanges": False,
        "created": [],
        "updated": [],
        "destroyed": [],
    }
    runtime = _authorized_runtime(tmp_path, monkeypatch)
    with _body(tmp_path) as (process, marker, body):
        context = _context(runtime)
        payload = load_session_manifest(context.manifest_path).payload
        backend = {
            **payload["backend_state"],
            "body_pid": process.pid,
            "conversation_marker": body["conversation"],
        }
        update_session_manifest(context.manifest_path, {"backend_state": backend})
        with _gateway(runtime) as request:
            initial = request("GET", "/v1/mail/status")[1]
            assert initial["offline"] is None and initial["online"] is None
            # Add foundation offline membership before online control; both share the same owner.
            offline = _sample_cao_plan_with_mailbox(tmp_path).mailboxes.offline.binding
            assert offline is not None
            payload = load_session_manifest(context.manifest_path).payload
            mutate_session_mailbox_binding(
                context.manifest_path,
                channel="offline",
                expected_revision=payload["launch_plan"]["mailboxes"]["offline"]["revision"],
                binding=offline,
                agent_id=context.agent_id,
                session_id=context.session_id,
            )
            offline_slot = load_session_manifest(context.manifest_path).payload["launch_plan"][
                "mailboxes"
            ]["offline"]
            revision = request("GET", "/v1/mail/online/binding")[1]["revision"]
            code, attached = _attach(request, state, source, revision)
            assert code == 200, attached
            assert attached["account_id"] == "account-a"
            _assert_body(process, marker, body)
            current = attached
            # A provider auth rejection never replaces the accepted account or leaks response text.
            state.http_errors["Identity/get"] = 401
            code, rejected = _attach(request, state, source, current["revision"])
            assert code == 502 and rejected["detail"]["error_code"] == "jmap_authentication_failed"
            assert "private credential text" not in json.dumps(rejected)
            state.http_errors.clear()
            assert request("GET", "/v1/mail/online/binding")[1]["revision"] == current["revision"]
            # A selected but non-listening endpoint is deterministic and cannot receive credentials.
            with socket.socket() as unavailable:
                unavailable.bind(("127.0.0.1", 0))
                code, failed = _attach(
                    request,
                    state,
                    source,
                    current["revision"],
                    jmap_url=f"http://127.0.0.1:{unavailable.getsockname()[1]}/.well-known/jmap",
                    timeout_seconds=0.1,
                )
                assert code == 502, failed
                assert failed["detail"]["error_code"] == "endpoint_unavailable"
            assert (
                request("GET", "/v1/mail/online/binding")[1]["binding_id"] == current["binding_id"]
            )
            common = {"schema_version": 3, "expected_binding_id": current["binding_id"]}
            code, page = request("POST", "/v1/mail/online/list", {**common, "limit": 2})
            assert code == 200 and page["message_count"] == 1
            reference = page["messages"][0]["message_ref"]
            assert page["messages"][0]["body_text"] is None
            code, content = request(
                "POST", "/v1/mail/online/read", {**common, "message_ref": reference}
            )
            assert code == 200 and content["message"]["body_text"] == "Selected content"
            code, sent = request(
                "POST",
                "/v1/mail/online/send",
                {
                    **common,
                    "to": ["bob@example.test"],
                    "subject": "integration send",
                    "body_content": "Explicit content",
                },
            )
            assert code == 200, sent
            assert sent["message"]["mutation_receipt"]["outcome"] == "confirmed"
            code, replied = request(
                "POST",
                "/v1/mail/online/reply",
                {**common, "message_ref": reference, "body_content": "Integration reply"},
            )
            assert code == 200, replied
            assert state.messages["old"]["keywords"]["$answered"] is True
            code, archived = request(
                "POST", "/v1/mail/online/archive", {**common, "message_refs": [reference]}
            )
            assert code == 200 and archived["messages"][0]["archived"] is True
            assert "inbox-id" not in state.messages["old"]["mailboxIds"]
            # Atomically replace the external source inode, then refresh only the same account.
            rotated = source.with_name("rotated-source.json")
            rotated.write_text(json.dumps({"password": "rotated-test-only-secret"}))
            rotated.chmod(0o600)
            os.replace(rotated, source)
            code, refreshed = request(
                "POST",
                "/v1/mail/online/binding/refresh",
                {"expected_revision": current["revision"]},
            )
            assert code == 200 and refreshed["binding_id"] == current["binding_id"]
            assert refreshed["revision"] != current["revision"]
            code, reconnected = request(
                "POST",
                "/v1/mail/online/binding/reconnect",
                {"expected_revision": refreshed["revision"]},
            )
            assert code == 200 and reconnected["revision"] == refreshed["revision"]
            assert reconnected["epoch_id"] != refreshed["epoch_id"]
            observed = observe_online(
                context=context,
                sqlite_path=runtime.m_paths.queue_path,
                binding_id=current["binding_id"],
                mode="any_inbox",
            )
            assert not observed.sync_view.superseded
            assert (
                load_session_manifest(context.manifest_path).payload["launch_plan"]["mailboxes"][
                    "offline"
                ]
                == offline_slot
            )
            _assert_body(process, marker, body)
        # Recreate the live gateway from current authority, retaining body and sync data.
        restarted = GatewayServiceRuntime.from_gateway_root(
            gateway_root=runtime.m_paths.gateway_root, host="127.0.0.1", port=43123
        )
        with _gateway(restarted) as request:
            restored = request("GET", "/v1/mail/online/binding")[1]
            assert restored["revision"] == reconnected["revision"]
            assert restored["epoch_id"] == reconnected["epoch_id"]
            sync = read_online_sync_status(
                restarted.m_paths.queue_path,
                agent_id=context.agent_id,
                binding_id=restored["binding_id"],
                account_id="account-a",
                mode="any_inbox",
            )
            assert sync["available"]
            code, detached = request(
                "DELETE", "/v1/mail/online/binding", {"expected_revision": restored["revision"]}
            )
            assert code == 200 and detached["state"] == "absent"
            status = request("GET", "/v1/mail/status")[1]
            assert status["canonical_mail_identity"]["channel"] == "offline"
            assert status["online"] is None
            assert source.exists() and state.messages
            payload = load_session_manifest(context.manifest_path).payload
            assert payload["backend_state"] == backend
            assert payload["launch_plan"]["mailboxes"]["offline"] == offline_slot
            _assert_body(process, marker, body)
    assert not any(path == "/api" or path.startswith("/api/") for _, path, _, _ in state.requests)


def test_replacement_cancels_pending_and_discards_late_provider_poll(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wire: tuple[_WireState, Path]
) -> None:
    state, source = wire
    state.state = "s0"
    state.changes = {
        "oldState": "s0",
        "newState": "s0",
        "hasMoreChanges": False,
        "created": [],
        "updated": [],
        "destroyed": [],
    }
    runtime = _authorized_runtime(tmp_path, monkeypatch)
    with _body(tmp_path) as (process, marker, body), _gateway(runtime) as request:
        revision = request("GET", "/v1/mail/online/binding")[1]["revision"]
        code, old = _attach(request, state, source, revision)
        assert code == 200
        context = _context(runtime)
        reached, release = threading.Event(), threading.Event()
        respond = state.respond

        def blocked(method: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
            """Delay one old-account metadata query until replacement finishes."""
            if method == "Email/query" and args["accountId"] == "account-a":
                reached.set()
                assert release.wait(5)
            return respond(method, args)

        monkeypatch.setattr(state, "respond", blocked)
        with ThreadPoolExecutor(max_workers=1) as pool:
            poll = pool.submit(
                observe_online,
                context=context,
                sqlite_path=runtime.m_paths.queue_path,
                binding_id=old["binding_id"],
                mode="any_inbox",
            )
            assert reached.wait(5)
            state.accounts["account-b"] = state.accounts["account-a"]
            try:
                with runtime.m_lock:
                    assert admit_mail_reminder(
                        runtime.m_paths.queue_path,
                        scope_key="old-online-scope",
                        cycle_key="due-cycle",
                        origin=ReminderOrigin(
                            context.agent_id,
                            "online",
                            old["binding_id"],
                            old["revision"],
                            old["epoch_id"],
                            "account-a",
                        ),
                        request_id="old-pending-reminder",
                        payload_json=json.dumps({"prompt": "Old binding wake"}),
                        accepted_at_utc=datetime.now(UTC).isoformat(),
                        managed_agent_instance_epoch=runtime.m_current_epoch,
                    )
                    code, replacement = _attach(
                        request,
                        state,
                        source,
                        old["revision"],
                        account_id="account-b",
                        replace=True,
                    )
                    assert code == 200, replacement
                    assert replacement["binding_id"] != old["binding_id"]
                    with sqlite3.connect(runtime.m_paths.queue_path) as database:
                        assert database.execute(
                            "SELECT state FROM gateway_requests WHERE request_id='old-pending-reminder'"
                        ).fetchone() == ("failed",)
            finally:
                release.set()
            result = poll.result(timeout=5)
        assert result.sync_view.superseded and result.messages == []
        assert (
            request(
                "POST",
                "/v1/mail/online/send",
                {
                    "schema_version": 3,
                    "expected_binding_id": old["binding_id"],
                    "to": ["bob@example.test"],
                    "subject": "stale round",
                    "body_content": "Never send",
                },
            )[0]
            == 409
        )
        assert not any(method == "EmailSubmission/set" for method, _ in state.methods)
        with sqlite3.connect(runtime.m_paths.queue_path) as database:
            assert database.execute(
                "SELECT COUNT(*) FROM mail_sync_observations WHERE binding_id=?",
                (replacement["binding_id"],),
            ).fetchone() == (0,)
        _assert_body(process, marker, body)


def test_started_prompt_effect_prevents_false_replacement_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wire: tuple[_WireState, Path]
) -> None:
    """A real worker handoff drains before replacement, and old queued effects fail."""
    state, source = wire
    runtime = _authorized_runtime(tmp_path, monkeypatch)
    entered, release = threading.Event(), threading.Event()
    effects: list[str] = []

    def submit(**kwargs: Any) -> None:
        """Pause an admitted old prompt immediately before its external handoff."""
        entered.set()
        assert release.wait(5)
        effects.append(str(kwargs["prompt"]))

    monkeypatch.setattr(runtime, "_submit_prompt_via_adapter", submit)
    with _body(tmp_path) as (process, marker, body), _gateway(runtime) as request:
        revision = request("GET", "/v1/mail/online/binding")[1]["revision"]
        code, old = _attach(request, state, source, revision)
        assert code == 200
        context = _context(runtime)
        origin = ReminderOrigin(
            context.agent_id,
            "online",
            old["binding_id"],
            old["revision"],
            old["epoch_id"],
            "account-a",
        )
        with runtime.m_lock:
            assert admit_mail_reminder(
                runtime.m_paths.queue_path,
                scope_key="effect-scope",
                cycle_key="first",
                origin=origin,
                request_id="old-started-effect",
                payload_json=json.dumps({"prompt": "old admitted handoff"}),
                accepted_at_utc=datetime.now(UTC).isoformat(),
                managed_agent_instance_epoch=runtime.m_current_epoch,
            )
        try:
            assert entered.wait(5)
            state.accounts["account-b"] = state.accounts["account-a"]
            code, busy = _attach(
                request,
                state,
                source,
                old["revision"],
                account_id="account-b",
                replace=True,
                timeout_seconds=0.1,
            )
            assert code == 409 and busy["detail"]["uncertain"] is True
            still_old = request("GET", "/v1/mail/online/binding")[1]
            assert still_old["binding_id"] == old["binding_id"]
            assert still_old["revision"] == old["revision"]
        finally:
            release.set()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with sqlite3.connect(runtime.m_paths.queue_path) as database:
                completed = database.execute(
                    "SELECT state FROM gateway_requests WHERE request_id='old-started-effect'"
                ).fetchone()
            if completed == ("completed",):
                break
            time.sleep(0.01)
        assert completed == ("completed",)
        code, replacement = _attach(
            request, state, source, old["revision"], account_id="account-b", replace=True
        )
        assert code == 200 and replacement["binding_id"] != old["binding_id"]
        with runtime.m_lock:
            assert admit_mail_reminder(
                runtime.m_paths.queue_path,
                scope_key="effect-scope",
                cycle_key="late",
                origin=origin,
                request_id="late-old-effect",
                payload_json=json.dumps({"prompt": "must never start"}),
                accepted_at_utc=datetime.now(UTC).isoformat(),
                managed_agent_instance_epoch=runtime.m_current_epoch,
            )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with sqlite3.connect(runtime.m_paths.queue_path) as database:
                rejected = database.execute(
                    "SELECT state FROM gateway_requests WHERE request_id='late-old-effect'"
                ).fetchone()
            if rejected == ("failed",):
                break
            time.sleep(0.01)
        assert rejected == ("failed",)
        assert effects == ["old admitted handoff"]
        _assert_body(process, marker, body)


def test_replacement_between_origin_check_and_effect_cannot_dispatch_old_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wire: tuple[_WireState, Path]
) -> None:
    """Reproduce the origin-check TOCTOU exactly, then reject at effect admission."""
    state, source = wire
    runtime = _authorized_runtime(tmp_path, monkeypatch)
    checked, release = threading.Event(), threading.Event()
    submissions: list[str] = []
    check = runtime._mail_reminder_origin_is_current
    checks = 0

    def paused_check(request_id: str) -> bool:
        """Pause after the execution check has read the still-current old origin."""
        nonlocal checks
        result = check(request_id)
        if request_id == "check-race" and result:
            checks += 1
            if checks == 2:
                checked.set()
                assert release.wait(5)
        return result

    monkeypatch.setattr(runtime, "_mail_reminder_origin_is_current", paused_check)
    monkeypatch.setattr(
        runtime, "_submit_prompt_via_adapter", lambda **kwargs: submissions.append(kwargs["prompt"])
    )
    with _body(tmp_path) as (process, marker, body), _gateway(runtime) as request:
        revision = request("GET", "/v1/mail/online/binding")[1]["revision"]
        code, old = _attach(request, state, source, revision)
        assert code == 200
        context = _context(runtime)
        with runtime.m_lock:
            assert admit_mail_reminder(
                runtime.m_paths.queue_path,
                scope_key="race-scope",
                cycle_key="first",
                origin=ReminderOrigin(
                    context.agent_id,
                    "online",
                    old["binding_id"],
                    old["revision"],
                    old["epoch_id"],
                    "account-a",
                ),
                request_id="check-race",
                payload_json=json.dumps({"prompt": "old check must not authorize new effect"}),
                accepted_at_utc=datetime.now(UTC).isoformat(),
                managed_agent_instance_epoch=runtime.m_current_epoch,
            )
        try:
            assert checked.wait(5)
            state.accounts["account-b"] = state.accounts["account-a"]
            code, replacement = _attach(
                request, state, source, old["revision"], account_id="account-b", replace=True
            )
            assert code == 200 and replacement["binding_id"] != old["binding_id"]
        finally:
            release.set()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with sqlite3.connect(runtime.m_paths.queue_path) as database:
                row = database.execute(
                    "SELECT state FROM gateway_requests WHERE request_id='check-race'"
                ).fetchone()
            if row == ("failed",):
                break
            time.sleep(0.01)
        assert row == ("failed",)
        assert submissions == []
        _assert_body(process, marker, body)
