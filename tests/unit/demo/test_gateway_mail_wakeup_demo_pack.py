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


class _Dumpable:
    """Minimal stand-in for Pydantic models that expose `model_dump()`."""

    def __init__(self, payload: dict[str, object]) -> None:
        self.m_payload = payload

    def model_dump(self, mode: str = "json") -> dict[str, object]:
        del mode
        return dict(self.m_payload)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON payload to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_runtime_mailbox_skill_tree(home_path: Path) -> None:
    """Create one runtime mailbox skill tree for project-local staging tests."""

    source = home_path / "skills" / ".system" / "mailbox"
    source.mkdir(parents=True, exist_ok=True)
    (source / "README.md").write_text("Runtime mailbox instructions\n", encoding="utf-8")


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

    assert parameters.backend == "houmao_server_rest"
    assert parameters.houmao_base_url == "http://127.0.0.1:9889"
    assert parameters.project_fixture == "tests/fixtures/dummy-projects/mailbox-demo-python"
    assert parameters.agent.blueprint == "blueprints/mailbox-demo-codex.yaml"
    assert parameters.delivery.body_file == "inputs/wake_up_message.md"
    assert HELPERS.render_mailbox_root(
        parameters,
        demo_output_dir=Path("/tmp/gateway-demo"),
    ) == Path("/tmp/gateway-demo/shared-mailbox")
    assert HELPERS.render_output_file_path(
        parameters,
        demo_output_dir=Path("/tmp/gateway-demo"),
    ) == Path("/tmp/gateway-demo/outputs/wakeup-time.txt")


def test_ensure_project_workdir_from_fixture_creates_managed_repo(tmp_path: Path) -> None:
    """Dummy-project provisioning should create a managed standalone git repo."""

    parameters = HELPERS.load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")
    fixture_dir = HELPERS.resolve_repo_relative_path(
        parameters.project_fixture,
        repo_root=_repo_root(),
    )
    project_workdir = tmp_path / "demo-output" / "project"

    result = HELPERS.ensure_project_workdir_from_fixture(
        repo_root=_repo_root(),
        project_fixture=fixture_dir,
        project_workdir=project_workdir,
        allow_reprovision=False,
    )

    metadata_path = project_workdir / ".houmao-demo-project.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert result == project_workdir.resolve()
    assert metadata["managed_by"] == "gateway-mail-wakeup-demo-pack"
    assert metadata["fixture_dir"] == str(fixture_dir.resolve())
    assert HELPERS.is_standalone_git_repo(project_workdir=project_workdir) is True


def test_ensure_project_workdir_from_fixture_reprovisions_managed_repo(tmp_path: Path) -> None:
    """Managed dummy-project repos should be safely reprovisioned on rerun."""

    parameters = HELPERS.load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")
    fixture_dir = HELPERS.resolve_repo_relative_path(
        parameters.project_fixture,
        repo_root=_repo_root(),
    )
    project_workdir = tmp_path / "demo-output" / "project"

    HELPERS.ensure_project_workdir_from_fixture(
        repo_root=_repo_root(),
        project_fixture=fixture_dir,
        project_workdir=project_workdir,
        allow_reprovision=False,
    )
    scratch_path = project_workdir / "scratch.txt"
    scratch_path.write_text("ad hoc change\n", encoding="utf-8")

    HELPERS.ensure_project_workdir_from_fixture(
        repo_root=_repo_root(),
        project_fixture=fixture_dir,
        project_workdir=project_workdir,
        allow_reprovision=True,
    )

    assert not scratch_path.exists()
    assert HELPERS.is_standalone_git_repo(project_workdir=project_workdir) is True


def test_ensure_project_workdir_from_fixture_rejects_stale_unmanaged_directory(
    tmp_path: Path,
) -> None:
    """Stale unmanaged project directories should fail clearly."""

    parameters = HELPERS.load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")
    fixture_dir = HELPERS.resolve_repo_relative_path(
        parameters.project_fixture,
        repo_root=_repo_root(),
    )
    project_workdir = tmp_path / "demo-output" / "project"
    project_workdir.mkdir(parents=True)
    (project_workdir / "notes.txt").write_text("stale directory\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not a demo-managed dummy-project repo"):
        HELPERS.ensure_project_workdir_from_fixture(
            repo_root=_repo_root(),
            project_fixture=fixture_dir,
            project_workdir=project_workdir,
            allow_reprovision=True,
        )


def test_stage_project_mailbox_skills_exposes_visible_project_surface(tmp_path: Path) -> None:
    """Mailbox skill staging should project visible docs into the copied project."""

    project_workdir = tmp_path / "project"
    project_workdir.mkdir(parents=True)
    home_path = tmp_path / "runtime-home"
    _write_runtime_mailbox_skill_tree(home_path)

    payload = HELPERS.stage_project_mailbox_skills(
        project_workdir=project_workdir,
        brain_build_payload={"home_path": str(home_path)},
    )

    assert Path(payload["hidden_mailbox_dir"]).is_dir()
    assert Path(payload["visible_mailbox_dir"]).is_dir()
    assert (project_workdir / "skills" / ".system" / "mailbox" / "README.md").is_file()
    assert (project_workdir / "skills" / "mailbox" / "README.md").is_file()


def test_start_demo_uses_dummy_project_and_mailbox_demo_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Start orchestration should use the copied dummy-project and mailbox-demo defaults."""

    calls: list[list[str]] = []

    home_path = tmp_path / "demo-output" / "runtime" / "homes" / "codex" / "home-gateway-demo"
    session_root = tmp_path / "demo-output" / "runtime" / "sessions" / "houmao_server_rest" / "gateway-demo"

    def fake_resolve_server_context(
        *,
        repo_root: Path,
        demo_output_dir: Path,
        houmao_base_url: str,
    ) -> dict[str, object]:
        del repo_root, demo_output_dir
        return {
            "managed": True,
            "api_base_url": houmao_base_url,
            "runtime_root": str(tmp_path / "demo-output" / "server" / "runtime"),
            "server_root": str(
                tmp_path
                / "demo-output"
                / "server"
                / "runtime"
                / "houmao_servers"
                / "127.0.0.1-9889"
            ),
            "current_instance_path": str(
                tmp_path
                / "demo-output"
                / "server"
                / "runtime"
                / "houmao_servers"
                / "127.0.0.1-9889"
                / "run"
                / "current-instance.json"
            ),
            "stdout_log_path": str(tmp_path / "demo-output" / "server" / "logs" / "stdout.log"),
            "stderr_log_path": str(tmp_path / "demo-output" / "server" / "logs" / "stderr.log"),
            "pid": 4242,
        }

    def fake_run_realm_controller_json(
        *,
        repo_root: Path,
        args: list[str],
        stdout_path: Path,
        env: dict[str, str] | None = None,
        accepted_exit_codes: set[int] | None = None,
    ) -> dict[str, object]:
        del repo_root, stdout_path, env, accepted_exit_codes
        calls.append(list(args))
        command = args[0]
        if command == "build-brain":
            _write_runtime_mailbox_skill_tree(home_path)
            return {
                "home_id": "home-gateway-demo",
                "home_path": str(home_path),
                "manifest_path": str(tmp_path / "demo-output" / "runtime" / "manifests" / "agent.yaml"),
                "launch_helper_path": str(home_path / "launch.sh"),
            }
        if command == "start-session":
            return {
                "session_manifest": str(session_root / "manifest.json"),
                "agent_identity": "AGENTSYS-gateway-mailbox-agent",
                "agent_name": "AGENTSYS-gateway-mailbox-agent",
                "backend": "houmao_server_rest",
                "tool": "codex",
                "mailbox": {
                    "transport": "filesystem",
                    "principal_id": "AGENTSYS-gateway-mailbox-agent",
                    "address": "AGENTSYS-gateway-mailbox-agent@agents.localhost",
                    "filesystem_root": str(tmp_path / "demo-output" / "shared-mailbox"),
                    "bindings_version": "2026-03-18T00:00:00Z",
                },
            }
        raise AssertionError(f"unexpected realm-controller command: {args}")

    def fake_resolve_managed_agent_identity(
        *,
        api_base_url: str,
        session_manifest_path: Path,
        timeout_seconds: float = 15.0,
    ) -> dict[str, object]:
        del timeout_seconds
        assert api_base_url == "http://127.0.0.1:9889"
        assert session_manifest_path == session_root / "manifest.json"
        return {
            "tracked_agent_id": "tracked-gateway-mailbox-agent",
            "transport": "tui",
            "tool": "codex",
            "session_name": "gateway-demo",
            "terminal_id": "abcd1234",
            "tmux_session_name": "gateway-demo",
            "manifest_path": str(session_root / "manifest.json"),
            "session_root": str(session_root),
            "agent_name": "AGENTSYS-gateway-mailbox-agent",
            "agent_id": "agent-gateway-mailbox-agent",
            "session_manifest": str(session_root / "manifest.json"),
        }

    class FakeServerClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            del timeout_seconds
            assert base_url == "http://127.0.0.1:9889"

        def attach_managed_agent_gateway(self, agent_ref: str) -> _Dumpable:
            assert agent_ref == "tracked-gateway-mailbox-agent"
            return _Dumpable(
                {
                    "schema_version": 1,
                    "protocol_version": "v1",
                    "attach_identity": "gateway-demo",
                    "backend": "houmao_server_rest",
                    "tmux_session_name": "gateway-demo",
                    "gateway_health": "healthy",
                    "managed_agent_connectivity": "connected",
                    "managed_agent_recovery": "idle",
                    "request_admission": "open",
                    "terminal_surface_eligibility": "ready",
                    "active_execution": "idle",
                    "queue_depth": 0,
                    "gateway_host": "127.0.0.1",
                    "gateway_port": 43123,
                    "managed_agent_instance_epoch": 1,
                    "managed_agent_instance_id": "tracked-gateway-mailbox-agent",
                }
            )

    def fake_notifier_status_payload(
        *,
        state: dict[str, object],
        interval_seconds: int | None = None,
        enable: bool | None = None,
        disable: bool = False,
    ) -> dict[str, object]:
        del state, interval_seconds, enable, disable
        return {
            "enabled": True,
            "interval_seconds": 1,
            "supported": True,
            "support_error": None,
            "last_poll_at_utc": None,
            "last_notification_at_utc": None,
            "last_error": None,
            "state_source": "server_managed_agent",
        }

    monkeypatch.setattr(HELPERS, "_resolve_server_context", fake_resolve_server_context)
    monkeypatch.setattr(HELPERS, "_run_realm_controller_json", fake_run_realm_controller_json)
    monkeypatch.setattr(HELPERS, "_resolve_managed_agent_identity", fake_resolve_managed_agent_identity)
    monkeypatch.setattr(HELPERS, "HoumaoServerClient", FakeServerClient)
    monkeypatch.setattr(HELPERS, "_notifier_status_payload", fake_notifier_status_payload)

    demo_output_dir = tmp_path / "demo-output"
    state = HELPERS.start_demo(
        repo_root=_repo_root(),
        pack_dir=PACK_DIR,
        demo_output_dir=demo_output_dir,
        parameters_path=PACK_DIR / "inputs" / "demo_parameters.json",
        jobs_dir=None,
    )

    build_args, start_args = calls
    project_workdir = demo_output_dir / "project"

    assert state["project_fixture"] == str(
        (_repo_root() / "tests/fixtures/dummy-projects/mailbox-demo-python").resolve()
    )
    assert (project_workdir / ".houmao-demo-project.json").is_file()
    assert HELPERS.is_standalone_git_repo(project_workdir=project_workdir) is True
    assert (project_workdir / "skills" / "mailbox" / "README.md").is_file()
    assert "--blueprint" in build_args
    assert build_args[build_args.index("--blueprint") + 1] == "blueprints/mailbox-demo-codex.yaml"
    assert start_args[start_args.index("--blueprint") + 1] == "blueprints/mailbox-demo-codex.yaml"
    assert start_args[start_args.index("--backend") + 1] == "houmao_server_rest"
    assert start_args[start_args.index("--houmao-base-url") + 1] == "http://127.0.0.1:9889"
    assert start_args[start_args.index("--workdir") + 1] == str(project_workdir)
    assert state["server"]["api_base_url"] == "http://127.0.0.1:9889"
    assert state["managed_agent"]["tracked_agent_id"] == "tracked-gateway-mailbox-agent"
    assert state["gateway"]["managed_agent_ref"] == "tracked-gateway-mailbox-agent"
    assert state["gateway"]["gateway_root"] == str(session_root / "gateway")


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
                message_ref="msg-20260316T100000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                thread_ref="msg-20260316T100000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
                message_ref="msg-20260316T100000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                thread_ref="msg-20260316T100000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
    (demo_output_dir / "project" / "skills" / "mailbox").mkdir(parents=True, exist_ok=True)
    (demo_output_dir / "project" / "skills" / "mailbox" / "README.md").write_text(
        "Project mailbox instructions\n",
        encoding="utf-8",
    )
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
                message_ref=message_id,
                thread_ref=message_id,
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
        layout.server_start_path,
        {
            "managed": True,
            "api_base_url": "http://127.0.0.1:9889",
            "runtime_root": str(demo_output_dir / "server" / "runtime"),
            "server_root": str(
                demo_output_dir / "server" / "runtime" / "houmao_servers" / "127.0.0.1-9889"
            ),
            "current_instance_path": str(
                demo_output_dir
                / "server"
                / "runtime"
                / "houmao_servers"
                / "127.0.0.1-9889"
                / "run"
                / "current-instance.json"
            ),
            "stdout_log_path": str(demo_output_dir / "server" / "logs" / "stdout.log"),
            "stderr_log_path": str(demo_output_dir / "server" / "logs" / "stderr.log"),
            "pid": 4242,
            "healthy": True,
            "started_current_run": True,
            "reused_existing_process": False,
            "message": "started demo-owned houmao-server",
        },
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
            "backend": "houmao_server_rest",
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
            "detail": "attached via demo-owned houmao-server managed-agent control",
            "gateway_root": str(gateway_root),
            "managed_agent_ref": "tracked-gateway-mailbox-agent",
            "schema_version": 1,
            "protocol_version": "v1",
            "attach_identity": "gateway-demo",
            "backend": "houmao_server_rest",
            "tmux_session_name": "gateway-demo",
            "gateway_health": "healthy",
            "managed_agent_connectivity": "connected",
            "managed_agent_recovery": "idle",
            "request_admission": "open",
            "terminal_surface_eligibility": "ready",
            "active_execution": "idle",
            "queue_depth": 0,
            "gateway_host": "127.0.0.1",
            "gateway_port": 43123,
            "managed_agent_instance_epoch": 1,
            "managed_agent_instance_id": "tracked-gateway-mailbox-agent",
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
            "state_source": "server_managed_agent",
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
        "server": json.loads(layout.server_start_path.read_text(encoding="utf-8")),
        "brain_build": {},
        "project_mailbox_skills": {
            "skills_target": str(demo_output_dir / "project" / "skills"),
            "hidden_mailbox_dir": str(demo_output_dir / "project" / "skills" / ".system" / "mailbox"),
            "visible_mailbox_dir": str(demo_output_dir / "project" / "skills" / "mailbox"),
        },
        "session": {},
        "managed_agent": {
            "tracked_agent_id": "tracked-gateway-mailbox-agent",
            "transport": "tui",
            "tool": "codex",
            "session_name": "gateway-demo",
            "terminal_id": "abcd1234",
            "tmux_session_name": "gateway-demo",
            "manifest_path": str(session_manifest_path),
            "session_root": str(demo_output_dir / "runtime" / "sessions" / "houmao_server_rest" / "gateway-demo"),
            "agent_name": "AGENTSYS-gateway-mailbox-agent",
            "agent_id": "agent-gateway-mailbox-agent",
        },
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

    class FakeServerClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            del timeout_seconds
            assert base_url == "http://127.0.0.1:9889"

        def get_managed_agent_state(self, agent_ref: str) -> _Dumpable:
            assert agent_ref == "tracked-gateway-mailbox-agent"
            return _Dumpable(
                {
                    "tracked_agent_id": "tracked-gateway-mailbox-agent",
                    "identity": dict(state["managed_agent"]),
                    "availability": "available",
                    "turn": {"phase": "ready", "active_turn_id": None},
                    "last_turn": {
                        "result": "success",
                        "turn_id": None,
                        "turn_index": None,
                        "updated_at_utc": "2026-03-16T10:00:04Z",
                    },
                    "diagnostics": [],
                    "mailbox": {
                        "transport": "filesystem",
                        "principal_id": "AGENTSYS-gateway-mailbox-agent",
                        "address": "AGENTSYS-gateway-mailbox-agent@agents.localhost",
                    },
                    "gateway": {
                        "gateway_health": "healthy",
                        "managed_agent_connectivity": "connected",
                        "managed_agent_recovery": "idle",
                        "request_admission": "open",
                        "active_execution": "idle",
                        "queue_depth": 0,
                        "gateway_host": "127.0.0.1",
                        "gateway_port": 43123,
                    },
                }
            )

        def get_managed_agent_gateway_status(self, agent_ref: str) -> _Dumpable:
            assert agent_ref == "tracked-gateway-mailbox-agent"
            return _Dumpable(json.loads(layout.gateway_attach_path.read_text(encoding="utf-8")))

        def get_managed_agent_gateway_mail_notifier(self, agent_ref: str) -> _Dumpable:
            assert agent_ref == "tracked-gateway-mailbox-agent"
            return _Dumpable(json.loads(layout.notifier_enable_path.read_text(encoding="utf-8")))

    from unittest.mock import patch

    with patch.object(HELPERS, "HoumaoServerClient", FakeServerClient):
        report = HELPERS.build_report(
            output_path=layout.report_path,
            parameters_path=parameters_path,
            state_path=layout.state_path,
        )

    assert (
        report["parameters"]["project_fixture"]
        == "tests/fixtures/dummy-projects/mailbox-demo-python"
    )
    assert report["parameters"]["agent"]["blueprint"] == "blueprints/mailbox-demo-codex.yaml"
    assert report["checks"]["server_managed"] is True
    assert report["checks"]["managed_agent_resolved"] is True
    assert report["checks"]["gateway_attached"] is True
    assert report["checks"]["notifier_enabled"] is True
    assert report["checks"]["notifier_enqueued_wakeup"] is True
    assert report["checks"]["notifier_poll_error_free"] is True
    assert report["checks"]["project_mailbox_skill_surface_present"] is True
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
    assert sanitized["server"]["server_root"] == "<SERVER_ROOT>"
    assert sanitized["server"]["current_instance_path"] == "<SERVER_CURRENT_INSTANCE_PATH>"
    assert sanitized["managed_agent"]["tracked_agent_id"] == "<TRACKED_AGENT_ID>"
    assert sanitized["project_mailbox_skills"]["visible_mailbox_dir"] == "<PROJECT_VISIBLE_MAILBOX_SKILLS_DIR>"
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
    assert sanitized["steps"]["server_start"]["server_root"] == "<SERVER_ROOT>"
    assert sanitized["steps"]["brain_build"]["manifest_path"] == "<BRAIN_MANIFEST_PATH>"
    assert sanitized["steps"]["brain_build"]["home_id"] == "<BRAIN_HOME_ID>"
    assert sanitized["steps"]["session_start"]["session_manifest"] == "<SESSION_MANIFEST_PATH>"
    assert sanitized["steps"]["session_start"]["backend"] == "houmao_server_rest"
    assert sanitized["steps"]["gateway_attach"]["gateway_root"] == "<GATEWAY_ROOT>"
    assert sanitized["steps"]["gateway_attach"]["gateway_port"] == "<GATEWAY_PORT>"
    assert sanitized["steps"]["gateway_attach"]["managed_agent_ref"] == "<TRACKED_AGENT_ID>"
    assert sanitized["steps"]["last_delivery"]["message_id"] == "<MESSAGE_ID>"

    expected_snapshot = json.loads(
        (PACK_DIR / "expected_report" / "report.json").read_text(encoding="utf-8")
    )
    assert sanitized == expected_snapshot


def test_verify_sanitized_report_detects_mismatch() -> None:
    """Sanitized verification should pass on equality and fail on drift."""

    actual = {"demo": "gateway-mail-wakeup-demo-pack", "checks": {"notifier_enabled": True}}
    HELPERS.verify_sanitized_report(actual, dict(actual))

    with pytest.raises(ValueError, match="sanitized report mismatch"):
        HELPERS.verify_sanitized_report(
            actual,
            {"demo": "gateway-mail-wakeup-demo-pack"},
        )
