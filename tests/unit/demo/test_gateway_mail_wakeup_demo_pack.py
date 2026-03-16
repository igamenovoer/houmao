"""Unit tests for the gateway mail wake-up demo-pack helpers."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from types import ModuleType

import pytest

from houmao.agents.realm_controller.gateway_storage import (
    GatewayNotifierAuditUnreadMessage,
    append_gateway_notifier_audit_record,
    write_gateway_mail_notifier_record,
)
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox
from houmao.mailbox.managed import DeliveryRequest, deliver_message
from houmao.mailbox.protocol import MailboxMessage, serialize_message_document


def _repo_root() -> Path:
    """Return the repository root for this test module."""

    return Path(__file__).resolve().parents[3]


def _helper_module() -> ModuleType:
    """Load the pack-local helper module from disk."""

    helper_path = (
        _repo_root()
        / "scripts"
        / "demo"
        / "gateway-mail-wakeup-demo-pack"
        / "scripts"
        / "tutorial_pack_helpers.py"
    )
    module_name = "gateway_mail_wakeup_demo_pack_helpers"
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


HELPERS = _helper_module()
PACK_DIR = _repo_root() / "scripts" / "demo" / "gateway-mail-wakeup-demo-pack"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON payload to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _deliver_unread_mailbox_message(mailbox_root: Path, *, message_id: str, subject: str) -> None:
    """Deliver one unread message into the filesystem mailbox root."""

    sender = MailboxPrincipal(
        principal_id="AGENTSYS-mail-injector",
        address="AGENTSYS-mail-injector@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="AGENTSYS-gateway-mailbox-agent",
        address="AGENTSYS-gateway-mailbox-agent@agents.localhost",
    )
    bootstrap_filesystem_mailbox(mailbox_root, principal=sender)
    bootstrap_filesystem_mailbox(mailbox_root, principal=recipient)

    staged_message = mailbox_root / "staging" / f"{message_id}.md"
    request = DeliveryRequest.from_payload(
        {
            "staged_message_path": str(staged_message),
            "message_id": message_id,
            "thread_id": message_id,
            "in_reply_to": None,
            "references": [],
            "created_at_utc": "2026-03-16T10:00:00Z",
            "sender": {
                "principal_id": sender.principal_id,
                "address": sender.address,
            },
            "to": [
                {
                    "principal_id": recipient.principal_id,
                    "address": recipient.address,
                }
            ],
            "cc": [],
            "reply_to": [],
            "subject": subject,
            "attachments": [],
            "headers": {},
        }
    )
    message = MailboxMessage(
        message_id=request.message_id,
        thread_id=request.thread_id,
        in_reply_to=request.in_reply_to,
        references=list(request.references),
        created_at_utc=request.created_at_utc,
        sender=request.sender.to_mailbox_principal(),
        to=[principal.to_mailbox_principal() for principal in request.to],
        cc=[principal.to_mailbox_principal() for principal in request.cc],
        reply_to=[principal.to_mailbox_principal() for principal in request.reply_to],
        subject=request.subject,
        body_markdown="Wake the agent and write a timestamp.\n",
        attachments=[attachment.to_mailbox_attachment() for attachment in request.attachments],
        headers=dict(request.headers),
    )
    staged_message.parent.mkdir(parents=True, exist_ok=True)
    staged_message.write_text(serialize_message_document(message), encoding="utf-8")
    deliver_message(mailbox_root, request)


def test_tracked_demo_parameters_parse_and_render_paths() -> None:
    """The tracked parameter file should expose the documented schema."""

    parameters = HELPERS.load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")

    assert parameters.backend == "cao_rest"
    assert parameters.agent.blueprint == "blueprints/gpu-kernel-coder-codex.yaml"
    assert parameters.delivery.body_file == "inputs/wake_up_message.md"
    assert HELPERS.render_mailbox_root(
        parameters,
        demo_output_dir=Path("/tmp/gateway-demo"),
    ) == Path("/tmp/gateway-demo/shared-mailbox")
    assert HELPERS.render_output_file_path(
        parameters,
        demo_output_dir=Path("/tmp/gateway-demo"),
    ) == Path("/tmp/gateway-demo/outputs/wakeup-time.txt")


def test_summarize_notifier_audit_records_captures_stable_outcome_summary(tmp_path: Path) -> None:
    """Audit summary reduction should keep stable outcome evidence."""

    queue_path = tmp_path / "queue.sqlite"
    write_gateway_mail_notifier_record(
        queue_path,
        enabled=True,
        interval_seconds=1,
        last_poll_at_utc="2026-03-16T10:00:00+00:00",
        last_notification_at_utc="2026-03-16T10:00:00+00:00",
        last_notified_digest="digest-1",
        last_error=None,
    )
    append_gateway_notifier_audit_record(
        queue_path,
        poll_time_utc="2026-03-16T10:00:00+00:00",
        unread_count=1,
        unread_digest="digest-1",
        unread_summary=(
            GatewayNotifierAuditUnreadMessage(
                message_id="msg-20260316T100000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                thread_id="msg-20260316T100000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                created_at_utc="2026-03-16T10:00:00Z",
                subject="Gateway wake-up demo",
            ),
        ),
        request_admission="open",
        active_execution="running",
        queue_depth=1,
        outcome="busy_skip",
        detail="busy",
    )
    append_gateway_notifier_audit_record(
        queue_path,
        poll_time_utc="2026-03-16T10:00:03+00:00",
        unread_count=1,
        unread_digest="digest-1",
        unread_summary=(
            GatewayNotifierAuditUnreadMessage(
                message_id="msg-20260316T100000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                thread_id="msg-20260316T100000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                created_at_utc="2026-03-16T10:00:00Z",
                subject="Gateway wake-up demo",
            ),
        ),
        request_admission="open",
        active_execution="idle",
        queue_depth=0,
        outcome="enqueued",
        enqueued_request_id="gwreq-20260316-100003Z-a1b2c3d4",
    )

    rows = HELPERS.read_gateway_notifier_audit_records(queue_path)
    summary = HELPERS.summarize_notifier_audit_records(rows)

    assert summary["has_enqueued"] is True
    assert summary["has_busy_skip"] is True
    assert summary["has_poll_error"] is False
    assert summary["observed_outcomes"] == ["busy_skip", "enqueued"]
    assert summary["max_unread_count"] == 1
    assert summary["unread_subjects"] == ["Gateway wake-up demo"]
    assert summary["enqueued_request_id_present"] is True


def test_build_report_and_sanitize_report_mask_nondeterministic_fields(tmp_path: Path) -> None:
    """The raw report should capture stable checks and sanitize unstable values."""

    demo_output_dir = tmp_path / "demo-output"
    layout = HELPERS.build_demo_layout(demo_output_dir=demo_output_dir)
    parameters_path = PACK_DIR / "inputs" / "demo_parameters.json"
    mailbox_root = demo_output_dir / "shared-mailbox"
    gateway_root = demo_output_dir / "gateway-root"
    queue_path = gateway_root / "queue.sqlite"
    events_path = gateway_root / "events.jsonl"
    output_file_path = demo_output_dir / "outputs" / "wakeup-time.txt"
    session_manifest_path = demo_output_dir / "runtime" / "sessions" / "agent.json"
    message_id = "msg-20260316T100000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    request_id = "gwreq-20260316-100003Z-a1b2c3d4"

    layout.demo_output_dir.mkdir(parents=True, exist_ok=True)
    layout.deliveries_dir.mkdir(parents=True, exist_ok=True)
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    gateway_root.mkdir(parents=True, exist_ok=True)
    _deliver_unread_mailbox_message(
        mailbox_root,
        message_id=message_id,
        subject="Gateway wake-up demo",
    )
    output_file_path.write_text("2026-03-16T10:00:05Z\n", encoding="utf-8")

    write_gateway_mail_notifier_record(
        queue_path,
        enabled=True,
        interval_seconds=1,
        last_poll_at_utc="2026-03-16T10:00:03+00:00",
        last_notification_at_utc="2026-03-16T10:00:03+00:00",
        last_notified_digest="digest-1",
        last_error=None,
    )
    append_gateway_notifier_audit_record(
        queue_path,
        poll_time_utc="2026-03-16T10:00:03+00:00",
        unread_count=1,
        unread_digest="digest-1",
        unread_summary=(
            GatewayNotifierAuditUnreadMessage(
                message_id=message_id,
                thread_id=message_id,
                created_at_utc="2026-03-16T10:00:00Z",
                subject="Gateway wake-up demo",
            ),
        ),
        request_admission="open",
        active_execution="idle",
        queue_depth=0,
        outcome="enqueued",
        enqueued_request_id=request_id,
    )
    with sqlite3.connect(queue_path) as connection:
        connection.execute(
            """
            INSERT INTO gateway_requests (
                request_id,
                request_kind,
                payload_json,
                state,
                accepted_at_utc,
                started_at_utc,
                finished_at_utc,
                managed_agent_instance_epoch
            )
            VALUES (?, 'mail_notifier_prompt', ?, 'completed', ?, ?, ?, 1)
            """,
            (
                request_id,
                json.dumps({"prompt": "wake up"}),
                "2026-03-16T10:00:03+00:00",
                "2026-03-16T10:00:03+00:00",
                "2026-03-16T10:00:04+00:00",
            ),
        )
        connection.commit()
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "kind": "accepted_internal",
                        "request_id": request_id,
                        "request_kind": "mail_notifier_prompt",
                        "accepted_at_utc": "2026-03-16T10:00:03+00:00",
                    },
                    sort_keys=True,
                ),
                json.dumps(
                    {
                        "kind": "completed",
                        "request_id": request_id,
                        "result_json": {
                            "completed_at_utc": "2026-03-16T10:00:04+00:00",
                            "request_kind": "mail_notifier_prompt",
                        },
                    },
                    sort_keys=True,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        layout.brain_build_path,
        {
            "home_id": "home-gateway-demo",
            "home_path": str(demo_output_dir / "runtime" / "homes" / "codex" / "home-gateway-demo"),
            "manifest_path": str(demo_output_dir / "runtime" / "manifests" / "agent.yaml"),
            "launch_helper_path": str(
                demo_output_dir / "runtime" / "homes" / "codex" / "home-gateway-demo" / "launch.sh"
            ),
        },
    )
    _write_json(
        layout.session_start_path,
        {
            "session_manifest": str(session_manifest_path),
            "backend": "cao_rest",
            "tool": "codex",
            "agent_identity": "AGENTSYS-gateway-mailbox-agent",
            "agent_name": "AGENTSYS-gateway-mailbox-agent",
            "job_dir": str(
                demo_output_dir / "project" / ".houmao" / "jobs" / "AGENTSYS-gateway-mailbox-agent"
            ),
            "mailbox": {
                "transport": "filesystem",
                "principal_id": "AGENTSYS-gateway-mailbox-agent",
                "address": "AGENTSYS-gateway-mailbox-agent@agents.localhost",
                "filesystem_root": str(mailbox_root),
                "bindings_version": "2026-03-16T10:00:00Z",
            },
        },
    )
    _write_json(
        layout.gateway_attach_path,
        {
            "status": "ok",
            "action": "gateway_attach",
            "detail": "attached",
            "gateway_root": str(gateway_root),
            "gateway_host": "127.0.0.1",
            "gateway_port": 43123,
        },
    )
    _write_json(
        layout.notifier_enable_path,
        {
            "enabled": True,
            "interval_seconds": 1,
            "supported": True,
            "support_error": None,
            "last_poll_at_utc": "2026-03-16T10:00:03+00:00",
            "last_notification_at_utc": "2026-03-16T10:00:03+00:00",
            "last_error": None,
            "state_source": "sqlite_fallback",
        },
    )

    state = {
        "schema_version": 1,
        "demo_id": "gateway-mail-wakeup-demo-pack",
        "parameters_path": str(parameters_path),
        "demo_output_dir": str(demo_output_dir),
        "project_workdir": str(demo_output_dir / "project"),
        "runtime_root": str(demo_output_dir / "runtime"),
        "mailbox_root": str(mailbox_root),
        "agent_def_dir": str(tmp_path / "repo" / "tests" / "fixtures" / "agents"),
        "jobs_dir": None,
        "cao": {
            "managed": True,
            "base_url": "http://localhost:9889",
            "launcher_config_path": str(demo_output_dir / "cao" / "launcher.toml"),
            "runtime_root": str(demo_output_dir / "cao" / "runtime"),
            "home_dir": str(
                demo_output_dir / "cao" / "runtime" / "cao_servers" / "localhost-9889" / "home"
            ),
            "profile_store": str(
                demo_output_dir
                / "cao"
                / "runtime"
                / "cao_servers"
                / "localhost-9889"
                / "home"
                / ".aws"
                / "cli-agent-orchestrator"
                / "agent-store"
            ),
            "artifact_dir": str(
                demo_output_dir / "cao" / "runtime" / "cao_servers" / "localhost-9889" / "launcher"
            ),
            "log_file": str(
                demo_output_dir
                / "cao"
                / "runtime"
                / "cao_servers"
                / "localhost-9889"
                / "launcher"
                / "cao-server.log"
            ),
            "launcher_result_file": str(
                demo_output_dir
                / "cao"
                / "runtime"
                / "cao_servers"
                / "localhost-9889"
                / "launcher"
                / "launcher_result.json"
            ),
            "ownership_file": str(
                demo_output_dir
                / "cao"
                / "runtime"
                / "cao_servers"
                / "localhost-9889"
                / "launcher"
                / "ownership.json"
            ),
            "healthy": True,
            "started_current_run": True,
            "reused_existing_process": False,
            "ownership_verified": True,
            "recovery_attempted": False,
            "message": "started",
        },
        "brain_build": {},
        "session": {},
        "gateway": {},
        "output_file_path": str(output_file_path),
        "message_counter": 1,
        "last_delivery_metadata": {
            "index": 1,
            "message_id": message_id,
            "created_at_utc": "2026-03-16T10:00:00Z",
        },
    }
    state["brain_build"] = json.loads(layout.brain_build_path.read_text(encoding="utf-8"))
    state["session"] = json.loads(layout.session_start_path.read_text(encoding="utf-8"))
    state["gateway"] = json.loads(layout.gateway_attach_path.read_text(encoding="utf-8"))
    _write_json(layout.state_path, state)

    report = HELPERS.build_report(
        output_path=layout.report_path,
        parameters_path=parameters_path,
        state_path=layout.state_path,
    )

    assert report["checks"]["cao_managed"] is True
    assert report["checks"]["gateway_attached"] is True
    assert report["checks"]["notifier_enabled"] is True
    assert report["checks"]["notifier_enqueued_wakeup"] is True
    assert report["checks"]["notifier_poll_error_free"] is True
    assert report["checks"]["queue_has_notifier_request"] is True
    assert report["checks"]["queue_completed_notifier_request"] is True
    assert report["checks"]["output_file_exists"] is True
    assert report["checks"]["output_file_contains_timestamp"] is True
    assert report["checks"]["mailbox_unread_present"] is True
    assert report["checks"]["output_file_newer_than_delivery"] is True

    sanitized = HELPERS.sanitize_report(report)

    assert sanitized["generated_at_utc"] == "<TIMESTAMP>"
    assert sanitized["demo_output_dir"] == "<DEMO_OUTPUT_DIR>"
    assert sanitized["project_workdir"] == "<PROJECT_WORKDIR>"
    assert sanitized["runtime_root"] == "<RUNTIME_ROOT>"
    assert sanitized["mailbox_root"] == "<MAILBOX_ROOT>"
    assert sanitized["agent_def_dir"] == "<AGENT_DEF_DIR>"
    assert sanitized["cao"]["launcher_config_path"] == "<CAO_LAUNCHER_CONFIG_PATH>"
    assert sanitized["cao"]["profile_store"] == "<CAO_PROFILE_STORE>"
    assert sanitized["notifier_status"]["state_source"] == "<STATE_SOURCE>"
    assert sanitized["mailbox_state"]["local_sqlite_path"] == "<MAILBOX_LOCAL_SQLITE_PATH>"
    assert (
        sanitized["mailbox_state"]["shared_index_sqlite_path"]
        == "<MAILBOX_SHARED_INDEX_SQLITE_PATH>"
    )
    assert sanitized["output_file"]["output_file_path"] == "<OUTPUT_FILE_PATH>"
    assert sanitized["output_file"]["content"] == "<OUTPUT_FILE_CONTENT>"
    assert sanitized["notifier_audit"]["rows"] == "<RAW_NOTIFIER_AUDIT_ROWS>"
    assert sanitized["notifier_audit"]["summary"]["total_rows"] == "<ROW_COUNT>"
    assert sanitized["notifier_audit"]["summary"]["observed_outcomes"] == "<OUTCOME_SET>"
    assert sanitized["steps"]["brain_build"]["manifest_path"] == "<BRAIN_MANIFEST_PATH>"
    assert sanitized["steps"]["brain_build"]["home_id"] == "<BRAIN_HOME_ID>"
    assert sanitized["steps"]["session_start"]["session_manifest"] == "<SESSION_MANIFEST_PATH>"
    assert sanitized["steps"]["gateway_attach"]["gateway_root"] == "<GATEWAY_ROOT>"
    assert sanitized["steps"]["gateway_attach"]["gateway_port"] == "<GATEWAY_PORT>"
    assert sanitized["steps"]["last_delivery"]["message_id"] == "<MESSAGE_ID>"


def test_verify_sanitized_report_detects_mismatch() -> None:
    """Sanitized verification should pass on equality and fail on drift."""

    actual = {"demo": "gateway-mail-wakeup-demo-pack", "checks": {"notifier_enabled": True}}
    HELPERS.verify_sanitized_report(actual, dict(actual))

    with pytest.raises(ValueError, match="sanitized report mismatch"):
        HELPERS.verify_sanitized_report(
            actual,
            {"demo": "gateway-mail-wakeup-demo-pack"},
        )
