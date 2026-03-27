"""Unit tests for the headless mail ping-pong gateway demo pack."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import houmao.demo.mail_ping_pong_gateway_demo_pack.driver as demo_driver
import houmao.demo.mail_ping_pong_gateway_demo_pack.server as demo_server
from houmao.agents.brain_builder import BuildResult
from houmao.agents.realm_controller.gateway_storage import (
    GatewayNotifierAuditUnreadMessage,
    append_gateway_notifier_audit_record,
    gateway_paths_from_session_root,
)
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox
from houmao.mailbox.managed import (
    DeliveryRequest,
    StateUpdateRequest,
    deliver_message,
    update_mailbox_state,
)
from houmao.mailbox.protocol import MailboxMessage, serialize_message_document
from houmao.server.managed_agents import ManagedHeadlessStore, ManagedHeadlessTurnRecord
from houmao.server.config import HoumaoServerConfig
from houmao.demo.mail_ping_pong_gateway_demo_pack.agents import (
    build_demo_environment,
    build_participant_brain,
    expose_runtime_skills_in_project,
)
from houmao.demo.mail_ping_pong_gateway_demo_pack.models import (
    DEFAULT_DEMO_OUTPUT_DIR_RELATIVE,
    DEFAULT_PARAMETERS_RELATIVE,
    DemoState,
    KickoffRequestState,
    ParticipantState,
    ServerProcessState,
    build_demo_layout,
    load_demo_parameters,
    load_demo_state,
    resolve_repo_relative_path,
    save_demo_state,
    utc_now_iso,
)
from houmao.demo.mail_ping_pong_gateway_demo_pack.reporting import (
    sanitize_report,
    verify_sanitized_report,
)


PACK_DIR = (
    Path(__file__).resolve().parents[3] / "scripts" / "demo" / "mail-ping-pong-gateway-demo-pack"
)
ROLE_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "agents" / "roles"


class _Dumpable:
    """Simple object with a `model_dump` method for fake client responses."""

    def __init__(self, payload: dict[str, object]) -> None:
        self.m_payload = payload

    def model_dump(self, mode: str = "json") -> dict[str, object]:
        """Return the stored payload."""

        del mode
        return dict(self.m_payload)


class _InspectClientDouble:
    """Fake managed-agent client used by inspect/report tests."""

    def __init__(self, *, manifest_paths: dict[str, str] | None = None) -> None:
        self.m_put_calls: list[tuple[str, int]] = []
        self.m_delete_calls: list[str] = []
        self.m_manifest_paths = dict(manifest_paths or {})

    def get_managed_agent_state(self, tracked_agent_id: str) -> _Dumpable:
        """Return one coarse managed-agent state payload."""

        manifest_path = self.m_manifest_paths.get(tracked_agent_id, "/tmp/manifest.json")
        return _Dumpable(
            {
                "tracked_agent_id": tracked_agent_id,
                "identity": {
                    "tracked_agent_id": tracked_agent_id,
                    "transport": "headless",
                    "tool": "claude" if "initiator" in tracked_agent_id else "codex",
                    "session_name": None,
                    "terminal_id": None,
                    "runtime_session_id": tracked_agent_id,
                    "tmux_session_name": f"tmux-{tracked_agent_id}",
                    "tmux_window_name": "agent",
                    "manifest_path": manifest_path,
                    "session_root": "/tmp/session-root",
                    "agent_name": tracked_agent_id,
                    "agent_id": tracked_agent_id,
                },
                "availability": "available",
                "turn": {"phase": "ready", "active_turn_id": None},
                "last_turn": {
                    "result": "success",
                    "completed_at_utc": "2026-03-23T12:05:00+00:00",
                    "turn_id": "turn-last",
                },
                "diagnostics": [],
                "mailbox": {
                    "transport": "filesystem",
                    "principal_id": tracked_agent_id,
                    "address": f"{tracked_agent_id}@agents.localhost",
                    "bindings_version": "v1",
                    "unread_count": 0,
                    "latest_message_at_utc": "2026-03-23T12:05:00+00:00",
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

    def get_managed_agent_state_detail(self, tracked_agent_id: str) -> _Dumpable:
        """Return one detailed managed-agent payload."""

        return _Dumpable(
            {
                "tracked_agent_id": tracked_agent_id,
                "identity": self.get_managed_agent_state(tracked_agent_id).model_dump()["identity"],
                "summary_state": self.get_managed_agent_state(tracked_agent_id).model_dump(),
                "detail": {
                    "transport": "headless",
                    "runtime_resumable": True,
                    "tmux_session_live": True,
                    "can_accept_prompt_now": True,
                    "interruptible": False,
                    "turn": {"phase": "ready", "active_turn_id": None},
                    "last_turn": {
                        "result": "success",
                        "completed_at_utc": "2026-03-23T12:05:00+00:00",
                        "turn_id": "turn-last",
                    },
                    "last_turn_status": "completed",
                    "last_turn_started_at_utc": "2026-03-23T12:04:00+00:00",
                    "last_turn_completed_at_utc": "2026-03-23T12:05:00+00:00",
                    "mailbox": {
                        "transport": "filesystem",
                        "principal_id": tracked_agent_id,
                        "address": f"{tracked_agent_id}@agents.localhost",
                        "bindings_version": "v1",
                        "unread_count": 0,
                        "latest_message_at_utc": "2026-03-23T12:05:00+00:00",
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
                    "diagnostics": [],
                },
            }
        )

    def get_managed_agent_gateway_status(self, tracked_agent_id: str) -> _Dumpable:
        """Return one gateway status payload."""

        del tracked_agent_id
        return _Dumpable(
            {
                "schema_version": 1,
                "protocol_version": "v1",
                "attach_identity": "attach-id",
                "backend": "claude_headless",
                "tmux_session_name": "tmux-demo",
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
                "managed_agent_instance_id": "instance-1",
            }
        )

    def get_managed_agent_gateway_mail_notifier(self, tracked_agent_id: str) -> _Dumpable:
        """Return one gateway mail-notifier status payload."""

        del tracked_agent_id
        return _Dumpable(
            {
                "schema_version": 1,
                "enabled": True,
                "interval_seconds": 5,
                "supported": True,
                "support_error": None,
                "last_poll_at_utc": "2026-03-23T12:05:00+00:00",
                "last_notification_at_utc": "2026-03-23T12:05:00+00:00",
                "last_error": None,
            }
        )

    def delete_managed_agent_gateway_mail_notifier(self, tracked_agent_id: str) -> _Dumpable:
        """Record one notifier delete call."""

        self.m_delete_calls.append(tracked_agent_id)
        return _Dumpable({"enabled": False})

    def put_managed_agent_gateway_mail_notifier(
        self, tracked_agent_id: str, request_model
    ) -> _Dumpable:
        """Record one notifier put call."""

        self.m_put_calls.append((tracked_agent_id, request_model.interval_seconds))
        return _Dumpable({"enabled": True, "interval_seconds": request_model.interval_seconds})


def _repo_root() -> Path:
    """Return the repository root."""

    return Path(__file__).resolve().parents[3]


def _make_demo_state(tmp_path: Path, *, active: bool = True) -> tuple[Path, object, DemoState]:
    """Create one representative persisted demo state and layout."""

    output_root = tmp_path / "outputs"
    paths = build_demo_layout(demo_output_dir=output_root)
    for directory in (
        paths.control_dir,
        paths.server_runtime_root,
        paths.runtime_root,
        paths.registry_root,
        paths.mailbox_root,
        paths.jobs_root,
        paths.monitor_dir,
        paths.initiator_project_dir,
        paths.responder_project_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    state = DemoState(
        active=active,
        created_at_utc="2026-03-23T12:00:00+00:00",
        stopped_at_utc=None if active else "2026-03-23T12:06:00+00:00",
        repo_root=_repo_root(),
        output_root=paths.output_root,
        agent_def_dir=_repo_root() / "tests" / "fixtures" / "agents",
        api_base_url="http://127.0.0.1:19989",
        mailbox_root=paths.mailbox_root,
        project_fixture=_repo_root()
        / "tests"
        / "fixtures"
        / "dummy-projects"
        / "mailbox-demo-python",
        thread_key="mail-ping-pong-20260323T120000Z-abcdef",
        round_limit=5,
        wait_defaults={
            "poll_interval_seconds": 2.0,
            "timeout_seconds": 600.0,
            "history_limit": 32,
        },
        server=ServerProcessState(
            api_base_url="http://127.0.0.1:19989",
            port=19989,
            runtime_root=paths.server_runtime_root,
            home_dir=paths.server_home_dir,
            pid=4242,
            started_at_utc="2026-03-23T12:00:00+00:00",
            started_by_demo=True,
            stdout_log_path=paths.server_logs_dir / "houmao-server.stdout.log",
            stderr_log_path=paths.server_logs_dir / "houmao-server.stderr.log",
        ),
        initiator=ParticipantState(
            role="initiator",
            tool="claude",
            role_name="mail-ping-pong-initiator",
            mailbox_principal_id="AGENTSYS-mail-ping-pong-initiator",
            mailbox_address="AGENTSYS-mail-ping-pong-initiator@agents.localhost",
            working_directory=paths.initiator_project_dir,
            brain_recipe_path=_repo_root()
            / "tests"
            / "fixtures"
            / "agents"
            / "brains"
            / "brain-recipes"
            / "claude"
            / "mail-ping-pong-initiator-default.yaml",
            brain_home_path=paths.runtime_root / "homes" / "initiator",
            brain_manifest_path=paths.runtime_root / "manifests" / "initiator.yaml",
            launch_helper_path=paths.runtime_root / "homes" / "initiator" / "launch.sh",
            tracked_agent_id="tracked-initiator",
            agent_name="mail-ping-pong-initiator-claude",
            agent_id="AGENTSYS-mail-ping-pong-initiator-claude",
            session_root=paths.runtime_root / "sessions" / "claude_headless" / "initiator",
            tmux_session_name="tmux-initiator",
            gateway_host="127.0.0.1",
        ),
        responder=ParticipantState(
            role="responder",
            tool="codex",
            role_name="mail-ping-pong-responder",
            mailbox_principal_id="AGENTSYS-mail-ping-pong-responder",
            mailbox_address="AGENTSYS-mail-ping-pong-responder@agents.localhost",
            working_directory=paths.responder_project_dir,
            brain_recipe_path=_repo_root()
            / "tests"
            / "fixtures"
            / "agents"
            / "brains"
            / "brain-recipes"
            / "codex"
            / "mail-ping-pong-responder-default.yaml",
            brain_home_path=paths.runtime_root / "homes" / "responder",
            brain_manifest_path=paths.runtime_root / "manifests" / "responder.yaml",
            launch_helper_path=paths.runtime_root / "homes" / "responder" / "launch.sh",
            tracked_agent_id="tracked-responder",
            agent_name="mail-ping-pong-responder-codex",
            agent_id="AGENTSYS-mail-ping-pong-responder-codex",
            session_root=paths.runtime_root / "sessions" / "codex_headless" / "responder",
            tmux_session_name="tmux-responder",
            gateway_host="127.0.0.1",
        ),
        kickoff_request=KickoffRequestState(
            submitted_at_utc="2026-03-23T12:00:30+00:00",
            request_id="mreq-123",
            disposition="accepted",
            headless_turn_id="turn-initiator-1",
            headless_turn_index=1,
            prompt="kickoff",
        ),
    )
    _seed_launch_posture_manifests(state)
    save_demo_state(paths.state_path, state)
    return output_root, paths, state


def _seed_launch_posture_manifests(state: DemoState) -> None:
    """Seed built brain manifests and live session manifests with unattended posture."""

    for participant in (state.initiator, state.responder):
        participant.brain_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        participant.brain_manifest_path.write_text(
            "\n".join(
                [
                    "schema_version: 3",
                    "launch_policy:",
                    "  operator_prompt_mode: unattended",
                    "runtime: {}",
                    "credentials: {}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        participant.session_root.mkdir(parents=True, exist_ok=True)
        backend = "claude_headless" if participant.tool == "claude" else "codex_headless"
        session_manifest = {
            "schema_version": 3,
            "backend": backend,
            "tool": participant.tool,
            "role_name": participant.role_name,
            "created_at_utc": "2026-03-23T12:00:00+00:00",
            "working_directory": str(participant.working_directory),
            "brain_manifest_path": str(participant.brain_manifest_path),
            "agent_name": participant.agent_name,
            "agent_id": participant.agent_id,
            "tmux_session_name": participant.tmux_session_name,
            "job_dir": str(participant.session_root / "job"),
            "launch_plan": {
                "backend": backend,
                "tool": participant.tool,
                "executable": participant.tool,
                "args": [],
                "working_directory": str(participant.working_directory),
                "home_selector": {
                    "env_var": "CLAUDE_CONFIG_DIR"
                    if participant.tool == "claude"
                    else "CODEX_HOME",
                    "home_path": str(participant.brain_home_path),
                },
                "env_var_names": [],
                "role_injection": {
                    "method": (
                        "native_append_system_prompt"
                        if participant.tool == "claude"
                        else "native_developer_instructions"
                    ),
                    "role_name": participant.role_name,
                },
                "mailbox": None,
                "metadata": {
                    "launch_policy_request": {
                        "operator_prompt_mode": "unattended",
                    },
                    "launch_policy": {
                        "strategy": "test-launch-policy",
                    },
                },
                "launch_policy_provenance": {
                    "strategy": "test-launch-policy",
                },
            },
            "launch_policy_provenance": {
                "strategy": "test-launch-policy",
            },
            "backend_state": {
                "tmux_session_name": participant.tmux_session_name,
                "turn_index": 0,
                "working_directory": str(participant.working_directory),
            },
            "headless": {
                "session_id": None,
                "turn_index": 0,
                "role_bootstrap_applied": False,
                "working_directory": str(participant.working_directory),
            },
            "codex": None,
            "cao": None,
            "houmao_server": None,
            "registry_generation_id": "test-generation",
            "registry_launch_authority": "runtime",
        }
        (participant.session_root / "manifest.json").write_text(
            json.dumps(session_manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def _seed_successful_mailbox(state: DemoState) -> None:
    """Seed one complete ten-message mailbox conversation."""

    initiator = MailboxPrincipal(
        principal_id=state.initiator.mailbox_principal_id,
        address=state.initiator.mailbox_address,
    )
    responder = MailboxPrincipal(
        principal_id=state.responder.mailbox_principal_id,
        address=state.responder.mailbox_address,
    )
    bootstrap_filesystem_mailbox(state.mailbox_root, principal=initiator)
    bootstrap_filesystem_mailbox(state.mailbox_root, principal=responder)
    thread_id: str | None = None
    parent_message_id: str | None = None
    references: list[str] = []
    for round_index in range(1, 6):
        root_message_id = f"msg-20260323T1200{round_index:02d}Z-{round_index:032x}"[:53]
        parent_message_id = _deliver_message(
            state=state,
            message_id=root_message_id,
            thread_id=root_message_id if thread_id is None else thread_id,
            in_reply_to=parent_message_id,
            references=list(references),
            sender=initiator,
            recipient=responder,
            round_index=round_index,
            sender_role="initiator",
            next_role="responder",
        )
        if thread_id is None:
            thread_id = parent_message_id
        references.append(parent_message_id)
        update_mailbox_state(
            state.mailbox_root,
            StateUpdateRequest(
                address=responder.address,
                message_id=parent_message_id,
                read=True,
            ),
        )
        reply_message_id = _deliver_message(
            state=state,
            message_id=f"msg-20260323T1201{round_index:02d}Z-{(round_index + 16):032x}"[:53],
            thread_id=thread_id,
            in_reply_to=parent_message_id,
            references=list(references),
            sender=responder,
            recipient=initiator,
            round_index=round_index,
            sender_role="responder",
            next_role="initiator",
        )
        references.append(reply_message_id)
        parent_message_id = reply_message_id
        update_mailbox_state(
            state.mailbox_root,
            StateUpdateRequest(
                address=initiator.address,
                message_id=reply_message_id,
                read=True,
            ),
        )


def _deliver_message(
    *,
    state: DemoState,
    message_id: str,
    thread_id: str,
    in_reply_to: str | None,
    references: list[str],
    sender: MailboxPrincipal,
    recipient: MailboxPrincipal,
    round_index: int,
    sender_role: str,
    next_role: str,
) -> str:
    """Deliver one deterministic mailbox message."""

    subject = f"[{state.thread_key}] Round {round_index} ping-pong"
    created_at = f"2026-03-23T12:{round_index:02d}:00Z"
    body = "\n".join(
        [
            f"Thread-Key: {state.thread_key}",
            f"Round: {round_index}",
            f"Round-Limit: {state.round_limit}",
            f"Sender-Role: {sender_role}",
            f"Next-Role: {next_role}",
            "",
            "Ping-pong demo message.",
        ]
    )
    staged_message = state.mailbox_root / "staging" / f"{message_id}.md"
    request = DeliveryRequest.from_payload(
        {
            "staged_message_path": str(staged_message),
            "message_id": message_id,
            "thread_id": thread_id,
            "in_reply_to": in_reply_to,
            "references": references,
            "created_at_utc": created_at,
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
        message_id=message_id,
        thread_id=thread_id,
        in_reply_to=in_reply_to,
        references=references,
        created_at_utc=created_at,
        sender=sender,
        to=[recipient],
        cc=[],
        reply_to=[],
        subject=subject,
        body_markdown=body,
        attachments=[],
        headers={},
    )
    staged_message.parent.mkdir(parents=True, exist_ok=True)
    staged_message.write_text(serialize_message_document(message), encoding="utf-8")
    deliver_message(state.mailbox_root, request)
    return message_id


def _seed_turn_records(state: DemoState) -> None:
    """Seed one successful managed-turn history."""

    store = ManagedHeadlessStore(
        config=HoumaoServerConfig(
            api_base_url=state.api_base_url,
            runtime_root=state.server.runtime_root,
            startup_child=False,
        )
    )
    for turn_index in range(1, 7):
        turn_id = f"turn-initiator-{turn_index}"
        store.write_turn_record(
            ManagedHeadlessTurnRecord(
                tracked_agent_id=state.initiator.tracked_agent_id,
                turn_id=turn_id,
                turn_index=turn_index,
                status="completed",
                started_at_utc=f"2026-03-23T12:{turn_index:02d}:00+00:00",
                completed_at_utc=f"2026-03-23T12:{turn_index:02d}:10+00:00",
                turn_artifact_dir=str(state.server.runtime_root / "turns" / turn_id),
                tmux_session_name=state.initiator.tmux_session_name,
                history_summary="completed",
            )
        )
    for turn_index in range(1, 6):
        turn_id = f"turn-responder-{turn_index}"
        store.write_turn_record(
            ManagedHeadlessTurnRecord(
                tracked_agent_id=state.responder.tracked_agent_id,
                turn_id=turn_id,
                turn_index=turn_index,
                status="completed",
                started_at_utc=f"2026-03-23T12:{turn_index:02d}:20+00:00",
                completed_at_utc=f"2026-03-23T12:{turn_index:02d}:30+00:00",
                turn_artifact_dir=str(state.server.runtime_root / "turns" / turn_id),
                tmux_session_name=state.responder.tmux_session_name,
                history_summary="completed",
            )
        )


def _seed_gateway_audits(state: DemoState) -> None:
    """Seed one enqueued gateway notifier audit per role."""

    for role, participant in {
        "initiator": state.initiator,
        "responder": state.responder,
    }.items():
        queue_path = gateway_paths_from_session_root(
            session_root=participant.session_root
        ).queue_path
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        append_gateway_notifier_audit_record(
            queue_path,
            poll_time_utc="2026-03-23T12:02:00+00:00",
            unread_count=1,
            unread_digest=f"digest-{role}",
            unread_summary=(
                GatewayNotifierAuditUnreadMessage(
                    message_ref=f"msg-{role}",
                    thread_ref="thread-ref",
                    created_at_utc="2026-03-23T12:02:00+00:00",
                    subject=f"[{state.thread_key}] Round 1 ping-pong",
                ),
            ),
            request_admission="open",
            active_execution="idle",
            queue_depth=0,
            outcome="enqueued",
            enqueued_request_id=f"mreq-{role}",
            detail=f"{state.thread_key} observed",
        )


def test_parameters_and_layout_defaults_resolve_from_repo_root() -> None:
    """Tracked parameters and default output-root resolution should stay stable."""

    parameters = load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")
    default_output = resolve_repo_relative_path(
        DEFAULT_DEMO_OUTPUT_DIR_RELATIVE,
        repo_root=_repo_root(),
    )
    default_parameters = resolve_repo_relative_path(
        DEFAULT_PARAMETERS_RELATIVE,
        repo_root=_repo_root(),
    )
    layout = build_demo_layout(demo_output_dir=default_output)

    assert parameters.demo_id == "mail-ping-pong-gateway-demo-pack"
    assert parameters.initiator.tool == "claude"
    assert parameters.responder.role_name == "mail-ping-pong-responder"
    assert parameters.initiator.brain_recipe_path.name == "default.yaml"
    assert parameters.responder.brain_recipe_path.name == "default.yaml"
    assert parameters.wait_defaults.timeout_seconds == 600.0
    assert default_parameters == PACK_DIR / "inputs" / "demo_parameters.json"
    assert layout.output_root == PACK_DIR / "outputs"
    assert layout.registry_root == PACK_DIR / "outputs" / "registry"
    assert layout.mailbox_root == PACK_DIR / "outputs" / "mailbox"


def test_pack_local_autotest_assets_exist() -> None:
    """The pack should ship the owned autotest harness, case, guide, and helpers."""

    expected_paths = (
        PACK_DIR / "autotest" / "run-case.sh",
        PACK_DIR / "autotest" / "case-unattended-full-run.sh",
        PACK_DIR / "autotest" / "case-unattended-full-run.md",
        PACK_DIR / "autotest" / "helpers" / "common.sh",
        PACK_DIR / "autotest" / "helpers" / "check_demo_preflight.py",
        PACK_DIR / "autotest" / "helpers" / "check_launch_posture.py",
        PACK_DIR / "autotest" / "helpers" / "print_demo_state_summary.py",
        PACK_DIR / "autotest" / "helpers" / "print_tmux_role_snapshot.sh",
        PACK_DIR / "autotest" / "helpers" / "write_case_result.py",
    )

    for path in expected_paths:
        assert path.is_file()


def test_build_participant_brain_preserves_recipe_operator_prompt_mode(tmp_path: Path) -> None:
    """The demo builder should preserve unattended mode from the tracked recipe."""

    agent_def_dir = _repo_root() / "tests" / "fixtures" / "agents"
    parameters = load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")

    build_result = build_participant_brain(
        agent_def_dir=agent_def_dir,
        runtime_root=tmp_path / "runtime",
        participant=parameters.initiator,
        home_id="mail-ping-pong-initiator-test",
    )

    assert build_result.manifest["launch_policy"]["operator_prompt_mode"] == "unattended"


def test_build_participant_brain_defaults_to_interactive_when_recipe_omits_prompt_mode(
    tmp_path: Path,
) -> None:
    """Recipes without explicit operator prompt mode should still build successfully."""

    recipe_path = tmp_path / "recipe.yaml"
    recipe_path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "name: demo-no-prompt-mode",
                "tool: claude",
                "default_agent_name: demo-claude",
                "skills:",
                "  - openspec-apply-change",
                "config_profile: default",
                "credential_profile: personal-a-default",
                "",
            ]
        ),
        encoding="utf-8",
    )
    parameters = load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")
    participant = parameters.initiator.model_copy(update={"brain_recipe_path": recipe_path})

    build_result = build_participant_brain(
        agent_def_dir=_repo_root() / "tests" / "fixtures" / "agents",
        runtime_root=tmp_path / "runtime",
        participant=participant,
        home_id="mail-ping-pong-initiator-no-prompt-mode",
    )

    assert build_result.manifest["launch_policy"]["operator_prompt_mode"] == "interactive"


def test_build_demo_environment_redirects_all_owned_roots(tmp_path: Path) -> None:
    """The demo environment should redirect runtime, registry, mailbox, and jobs roots."""

    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    env = build_demo_environment(paths=paths, base_env={"HOME": "/tmp/home", "PATH": "/usr/bin"})

    assert env["AGENTSYS_GLOBAL_RUNTIME_DIR"] == str(paths.runtime_root)
    assert env["AGENTSYS_GLOBAL_REGISTRY_DIR"] == str(paths.registry_root)
    assert env["AGENTSYS_GLOBAL_MAILBOX_DIR"] == str(paths.mailbox_root)
    assert env["AGENTSYS_LOCAL_JOBS_DIR"] == str(paths.jobs_root)
    assert env["HOME"] == str(paths.server_home_dir)
    assert env["PATH"] == "/usr/bin"


def test_kickoff_prompt_stays_policy_thin_and_gateway_first(tmp_path: Path) -> None:
    """The kickoff prompt should name shared mailbox policy, not helper recipes."""

    _output_root, _paths, state = _make_demo_state(tmp_path)
    parameters = load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")

    prompt = demo_driver._build_kickoff_prompt(
        parameters=parameters,
        state=state,
        thread_key=state.thread_key or "mail-ping-pong-20260323T120000Z-abcdef",
    )

    assert "shared gateway mailbox operations" in prompt
    assert "email-via-filesystem" in prompt
    assert "skills/mailbox/email-via-filesystem/SKILL.md" in prompt
    assert "Do not inspect repo docs or OpenAPI" in prompt
    assert (
        '{"schema_version":1,"to":["recipient@agents.localhost"],"subject":"...","body_content":"...","attachments":[]}'
        in prompt
    )
    assert "message_ref" in prompt
    assert "POST /v1/mail/state" in prompt
    assert "deliver_message.py" not in prompt
    assert "update_mailbox_state.py" not in prompt


def test_role_overlays_stay_gateway_first_and_mark_read_after_success() -> None:
    """Tracked role overlays should carry ping-pong policy without helper recipes."""

    initiator_prompt = (
        ROLE_FIXTURES_DIR / "mail-ping-pong-initiator" / "system-prompt.md"
    ).read_text(encoding="utf-8")
    responder_prompt = (
        ROLE_FIXTURES_DIR / "mail-ping-pong-responder" / "system-prompt.md"
    ).read_text(encoding="utf-8")

    assert "shared mailbox state update" in initiator_prompt
    assert "shared mailbox state update" in responder_prompt
    assert "email-via-filesystem" in initiator_prompt
    assert "email-via-filesystem" in responder_prompt
    assert "skills/mailbox/email-via-filesystem/SKILL.md" in initiator_prompt
    assert "skills/mailbox/email-via-filesystem/SKILL.md" in responder_prompt
    assert "Do not inspect repo docs, OpenAPI, or broad source files" in initiator_prompt
    assert "Do not inspect repo docs, OpenAPI, or broad source files" in responder_prompt
    assert '{"schema_version":1,"unread_only":true,"limit":10}' in initiator_prompt
    assert '{"schema_version":1,"unread_only":true,"limit":10}' in responder_prompt
    assert "message_ref" in initiator_prompt
    assert "message_ref" in responder_prompt
    assert "deliver_message.py" not in initiator_prompt
    assert "deliver_message.py" not in responder_prompt
    assert "update_mailbox_state.py" not in initiator_prompt
    assert "update_mailbox_state.py" not in responder_prompt


def test_demo_state_round_trip_preserves_minimum_contract(tmp_path: Path) -> None:
    """Persisted demo state should round-trip with the required fields intact."""

    _output_root, paths, state = _make_demo_state(tmp_path)

    loaded = load_demo_state(paths.state_path)

    assert loaded.output_root == state.output_root
    assert loaded.api_base_url == "http://127.0.0.1:19989"
    assert loaded.thread_key == "mail-ping-pong-20260323T120000Z-abcdef"
    assert loaded.initiator.role_name == "mail-ping-pong-initiator"
    assert loaded.responder.tracked_agent_id == "tracked-responder"


def test_start_command_uses_tracked_defaults_and_persists_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup should use the tracked fixtures and persist a resumable state file."""

    created_projects: list[Path] = []

    def fake_start_demo_server(
        *, api_base_url: str, paths, env, timeout_seconds: float
    ) -> ServerProcessState:
        del env, timeout_seconds
        return ServerProcessState(
            api_base_url=api_base_url,
            port=int(api_base_url.rsplit(":", 1)[-1]),
            runtime_root=paths.server_runtime_root,
            home_dir=paths.server_home_dir,
            pid=9999,
            started_at_utc=utc_now_iso(),
            started_by_demo=True,
            stdout_log_path=paths.server_logs_dir / "stdout.log",
            stderr_log_path=paths.server_logs_dir / "stderr.log",
        )

    def fake_build_participant_brain(
        *, agent_def_dir: Path, runtime_root: Path, participant, home_id: str
    ) -> BuildResult:
        del agent_def_dir, participant
        home_path = runtime_root / "homes" / home_id
        manifest_path = runtime_root / "manifests" / f"{home_id}.yaml"
        launch_helper_path = home_path / "launch.sh"
        home_path.mkdir(parents=True, exist_ok=True)
        (home_path / "skills/mailbox/email-via-filesystem").mkdir(parents=True, exist_ok=True)
        (home_path / "skills/mailbox/email-via-filesystem/SKILL.md").write_text(
            "# mailbox skill\n",
            encoding="utf-8",
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("schema_version: 1\n", encoding="utf-8")
        launch_helper_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        return BuildResult(
            home_id=home_id,
            home_path=home_path,
            manifest_path=manifest_path,
            launch_helper_path=launch_helper_path,
            launch_preview="launch",
            manifest={},
        )

    def fake_launch_participant(
        *,
        client,
        agent_def_dir: Path,
        layout,
        participant,
        build_result: BuildResult,
        working_directory: Path,
        role: str,
    ) -> ParticipantState:
        del client, agent_def_dir, participant
        return ParticipantState(
            role=role,
            tool="claude" if role == "initiator" else "codex",
            role_name=f"mail-ping-pong-{role}",
            mailbox_principal_id=f"AGENTSYS-{role}",
            mailbox_address=f"AGENTSYS-{role}@agents.localhost",
            working_directory=working_directory,
            brain_recipe_path=Path("/repo/recipe.yaml"),
            brain_home_path=build_result.home_path,
            brain_manifest_path=build_result.manifest_path,
            launch_helper_path=build_result.launch_helper_path,
            tracked_agent_id=f"tracked-{role}",
            agent_name=f"agent-{role}",
            agent_id=f"AGENTSYS-agent-{role}",
            session_root=layout.runtime_root / "sessions" / role,
            tmux_session_name=f"tmux-{role}",
            gateway_host=None,
        )

    def fake_attach_gateway_and_enable_notifier(
        *, client, participant: ParticipantState, notifier_interval_seconds: int
    ) -> ParticipantState:
        del client, notifier_interval_seconds
        return participant.model_copy(update={"gateway_host": "127.0.0.1"})

    def fake_ensure_project_workdir_from_fixture(
        *, project_fixture: Path, project_workdir: Path, allow_reprovision: bool
    ) -> Path:
        del project_fixture, allow_reprovision
        created_projects.append(project_workdir)
        project_workdir.mkdir(parents=True, exist_ok=True)
        return project_workdir.resolve()

    monkeypatch.setattr(demo_driver, "choose_free_loopback_port", lambda: 19989)
    monkeypatch.setattr(demo_driver, "start_demo_server", fake_start_demo_server)
    monkeypatch.setattr(demo_driver, "build_participant_brain", fake_build_participant_brain)
    monkeypatch.setattr(demo_driver, "launch_participant", fake_launch_participant)
    monkeypatch.setattr(
        demo_driver,
        "attach_gateway_and_enable_notifier",
        fake_attach_gateway_and_enable_notifier,
    )
    monkeypatch.setattr(
        demo_driver,
        "ensure_project_workdir_from_fixture",
        fake_ensure_project_workdir_from_fixture,
    )
    monkeypatch.setattr(
        demo_driver, "HoumaoServerClient", lambda base_url: SimpleNamespace(base_url=base_url)
    )

    result = demo_driver.main(["start", "--demo-output-dir", str(tmp_path / "outputs")])

    state = load_demo_state(tmp_path / "outputs" / "control" / "demo_state.json")
    assert result == 0
    assert created_projects == [
        tmp_path / "outputs" / "projects" / "initiator",
        tmp_path / "outputs" / "projects" / "responder",
    ]
    assert (created_projects[0] / "skills/mailbox/email-via-filesystem/SKILL.md").is_file()
    assert (created_projects[1] / "skills/mailbox/email-via-filesystem/SKILL.md").is_file()
    assert state.output_root == (tmp_path / "outputs").resolve()
    assert state.agent_def_dir == (_repo_root() / "tests" / "fixtures" / "agents")
    assert state.mailbox_root == (tmp_path / "outputs" / "mailbox").resolve()
    assert state.initiator.brain_manifest_path.name.startswith("mail-ping-pong-initiator-")
    assert state.wait_defaults.timeout_seconds == 600.0


def test_sanitize_report_normalizes_thread_subjects_and_thread_key_variants() -> None:
    """Subject evidence should not depend on exact live reply formatting."""

    payload = {
        "mailbox_evidence": {
            "subjects": [
                "[mail-ping-pong-20260323T120000Z-abcdef] Round 1 ping-pong",
                "Re: [mail-ping-pong-20260323T185049+0000-941192] Round 1 ping-pong",
            ]
        }
    }

    sanitized = sanitize_report(payload)

    assert sanitized["mailbox_evidence"]["subjects"] == [
        "<THREAD_SUBJECT>",
        "<THREAD_SUBJECT>",
    ]


def test_start_command_honors_agent_def_dir_env_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup should respect the `AGENT_DEF_DIR` environment override."""

    override_agent_def_dir = tmp_path / "custom-agent-defs"
    override_agent_def_dir.mkdir(parents=True)

    def fake_start_demo_server(
        *, api_base_url: str, paths, env, timeout_seconds: float
    ) -> ServerProcessState:
        del env, timeout_seconds
        return ServerProcessState(
            api_base_url=api_base_url,
            port=int(api_base_url.rsplit(":", 1)[-1]),
            runtime_root=paths.server_runtime_root,
            home_dir=paths.server_home_dir,
            pid=9999,
            started_at_utc=utc_now_iso(),
            started_by_demo=True,
            stdout_log_path=paths.server_logs_dir / "stdout.log",
            stderr_log_path=paths.server_logs_dir / "stderr.log",
        )

    def fake_build_participant_brain(
        *, agent_def_dir: Path, runtime_root: Path, participant, home_id: str
    ) -> BuildResult:
        del participant
        home_path = runtime_root / "homes" / home_id
        manifest_path = runtime_root / "manifests" / f"{home_id}.yaml"
        launch_helper_path = home_path / "launch.sh"
        home_path.mkdir(parents=True, exist_ok=True)
        (home_path / "skills/mailbox/email-via-filesystem").mkdir(parents=True, exist_ok=True)
        (home_path / "skills/mailbox/email-via-filesystem/SKILL.md").write_text(
            "# mailbox skill\n",
            encoding="utf-8",
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("schema_version: 1\n", encoding="utf-8")
        launch_helper_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        assert agent_def_dir == override_agent_def_dir.resolve()
        return BuildResult(
            home_id=home_id,
            home_path=home_path,
            manifest_path=manifest_path,
            launch_helper_path=launch_helper_path,
            launch_preview="launch",
            manifest={},
        )

    def fake_launch_participant(
        *,
        client,
        agent_def_dir: Path,
        layout,
        participant,
        build_result: BuildResult,
        working_directory: Path,
        role: str,
    ) -> ParticipantState:
        del client, layout, participant
        assert agent_def_dir == override_agent_def_dir.resolve()
        return ParticipantState(
            role=role,
            tool="claude" if role == "initiator" else "codex",
            role_name=f"mail-ping-pong-{role}",
            mailbox_principal_id=f"AGENTSYS-{role}",
            mailbox_address=f"AGENTSYS-{role}@agents.localhost",
            working_directory=working_directory,
            brain_recipe_path=Path("/repo/recipe.yaml"),
            brain_home_path=build_result.home_path,
            brain_manifest_path=build_result.manifest_path,
            launch_helper_path=build_result.launch_helper_path,
            tracked_agent_id=f"tracked-{role}",
            agent_name=f"agent-{role}",
            agent_id=f"AGENTSYS-agent-{role}",
            session_root=tmp_path / "sessions" / role,
            tmux_session_name=f"tmux-{role}",
            gateway_host=None,
        )

    monkeypatch.setenv("AGENT_DEF_DIR", str(override_agent_def_dir))
    monkeypatch.setattr(demo_driver, "choose_free_loopback_port", lambda: 19989)
    monkeypatch.setattr(demo_driver, "start_demo_server", fake_start_demo_server)
    monkeypatch.setattr(demo_driver, "build_participant_brain", fake_build_participant_brain)
    monkeypatch.setattr(demo_driver, "launch_participant", fake_launch_participant)
    monkeypatch.setattr(
        demo_driver,
        "attach_gateway_and_enable_notifier",
        lambda *, client, participant, notifier_interval_seconds: participant.model_copy(
            update={"gateway_host": "127.0.0.1"}
        ),
    )
    monkeypatch.setattr(
        demo_driver,
        "ensure_project_workdir_from_fixture",
        lambda *, project_fixture, project_workdir, allow_reprovision: project_workdir,
    )
    monkeypatch.setattr(
        demo_driver, "HoumaoServerClient", lambda base_url: SimpleNamespace(base_url=base_url)
    )

    result = demo_driver.main(["start", "--demo-output-dir", str(tmp_path / "outputs")])
    state = load_demo_state(tmp_path / "outputs" / "control" / "demo_state.json")

    assert result == 0
    assert state.agent_def_dir == override_agent_def_dir.resolve()


def test_expose_runtime_skills_in_project_copies_mailbox_skill_docs(tmp_path: Path) -> None:
    """Demo projects should keep a stable project-local mailbox skill path."""

    project_workdir = tmp_path / "project"
    project_workdir.mkdir()
    home_path = tmp_path / "home"
    (home_path / "skills/mailbox/email-via-filesystem").mkdir(parents=True)
    (home_path / "skills/mailbox/email-via-filesystem/SKILL.md").write_text(
        "# mailbox skill\n", encoding="utf-8"
    )
    build_result = BuildResult(
        home_id="demo-home",
        home_path=home_path,
        manifest_path=tmp_path / "manifest.yaml",
        launch_helper_path=tmp_path / "launch.sh",
        launch_preview="launch",
        manifest={},
    )

    expose_runtime_skills_in_project(
        project_workdir=project_workdir,
        build_result=build_result,
    )

    assert (project_workdir / "skills/mailbox/email-via-filesystem/SKILL.md").is_file()
    assert not (project_workdir / "skills/.system/mailbox/email-via-filesystem/SKILL.md").exists()
    assert not (project_workdir / "skills").is_symlink()


def test_expose_runtime_skills_in_project_falls_back_to_packaged_mailbox_docs(
    tmp_path: Path,
) -> None:
    """Demo projects should still expose mailbox docs when the runtime home lost them."""

    project_workdir = tmp_path / "project"
    project_workdir.mkdir()
    home_path = tmp_path / "home"
    (home_path / "skills").mkdir(parents=True)
    build_result = BuildResult(
        home_id="demo-home",
        home_path=home_path,
        manifest_path=tmp_path / "manifest.yaml",
        launch_helper_path=tmp_path / "launch.sh",
        launch_preview="launch",
        manifest={},
    )

    expose_runtime_skills_in_project(
        project_workdir=project_workdir,
        build_result=build_result,
    )

    assert (project_workdir / "skills/mailbox/email-via-filesystem/SKILL.md").is_file()
    assert not (project_workdir / "skills/.system/mailbox/email-via-filesystem/SKILL.md").exists()


def test_wait_for_server_health_ignores_child_cao_status_for_native_headless_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The no-child native-headless waiter should only require Houmao root health."""

    class _HealthDouble:
        status = "ok"
        houmao_service = "houmao-server"
        child_cao = SimpleNamespace(healthy=False)

        def model_dump_json(self) -> str:
            return '{"status":"ok"}'

    class _ClientDouble:
        def __init__(self, base_url: str, timeout_seconds: float = 1.0) -> None:
            del base_url, timeout_seconds

        def health_extended(self) -> _HealthDouble:
            return _HealthDouble()

    monkeypatch.setattr(demo_server, "HoumaoServerClient", _ClientDouble)

    demo_server.wait_for_server_health(
        api_base_url="http://127.0.0.1:19989",
        timeout_seconds=0.01,
    )


def test_inspect_reuses_persisted_state_and_writes_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inspect should reload persisted state and write `inspect.json`."""

    _output_root, paths, state = _make_demo_state(tmp_path)
    _seed_successful_mailbox(state)
    _seed_turn_records(state)
    _seed_gateway_audits(state)
    fake_client = _InspectClientDouble(
        manifest_paths={
            state.initiator.tracked_agent_id: str(state.initiator.session_root / "manifest.json"),
            state.responder.tracked_agent_id: str(state.responder.session_root / "manifest.json"),
        }
    )
    monkeypatch.setattr(demo_driver, "HoumaoServerClient", lambda base_url: fake_client)

    result = demo_driver.main(["inspect", "--demo-output-dir", str(paths.output_root)])
    inspect_payload = json.loads(paths.inspect_path.read_text(encoding="utf-8"))

    assert result == 0
    assert inspect_payload["progress"]["success"] is True
    assert (
        inspect_payload["participants"]["initiator"]["state"]["tracked_agent_id"]
        == "tracked-initiator"
    )
    assert (
        inspect_payload["participants"]["initiator"]["launch_posture"][
            "live_launch_request_operator_prompt_mode"
        ]
        == "unattended"
    )
    assert (
        inspect_payload["participants"]["responder"]["launch_posture"]["launch_policy_applied"]
        is True
    )
    assert inspect_payload["participants"]["responder"]["gateway_mail_notifier"]["enabled"] is True


def test_refresh_artifacts_builds_complete_report_and_matches_snapshot(tmp_path: Path) -> None:
    """Successful evidence should produce the tracked sanitized report snapshot."""

    _output_root, paths, state = _make_demo_state(tmp_path)
    _seed_successful_mailbox(state)
    _seed_turn_records(state)
    _seed_gateway_audits(state)
    fake_client = _InspectClientDouble(
        manifest_paths={
            state.initiator.tracked_agent_id: str(state.initiator.session_root / "manifest.json"),
            state.responder.tracked_agent_id: str(state.responder.session_root / "manifest.json"),
        }
    )

    progress, _inspect_snapshot, _report_payload = demo_driver._refresh_artifacts(
        paths=paths,
        state=state,
        client=fake_client,
    )

    sanitized = json.loads(paths.sanitized_report_path.read_text(encoding="utf-8"))
    expected = json.loads(
        (PACK_DIR / "expected_report" / "report.json").read_text(encoding="utf-8")
    )

    assert progress.success is True
    assert (
        _report_payload["per_role"]["initiator"]["launch_posture"][
            "tracked_recipe_operator_prompt_mode"
        ]
        == "unattended"
    )
    verify_sanitized_report(sanitized, expected)


def test_pause_and_continue_toggle_gateway_notifiers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pause and continue should disable and re-enable both participant notifiers."""

    _output_root, paths, _state = _make_demo_state(tmp_path)
    fake_client = _InspectClientDouble()
    monkeypatch.setattr(demo_driver, "HoumaoServerClient", lambda base_url: fake_client)

    pause_result = demo_driver.main(["pause", "--demo-output-dir", str(paths.output_root)])
    continue_result = demo_driver.main(["continue", "--demo-output-dir", str(paths.output_root)])

    assert pause_result == 0
    assert continue_result == 0
    assert fake_client.m_delete_calls == ["tracked-initiator", "tracked-responder"]
    assert fake_client.m_put_calls == [
        ("tracked-initiator", 5),
        ("tracked-responder", 5),
    ]


def test_wait_timeout_writes_incomplete_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Timeout waits should preserve artifacts and explain the incomplete reason."""

    _output_root, paths, state = _make_demo_state(tmp_path, active=False)
    save_demo_state(paths.state_path, state)
    monkeypatch.setattr(demo_driver.time, "sleep", lambda seconds: None)

    result = demo_driver.main(
        [
            "wait",
            "--demo-output-dir",
            str(paths.output_root),
            "--timeout-seconds",
            "0.01",
            "--poll-interval-seconds",
            "0.01",
        ]
    )
    report_payload = json.loads(paths.report_path.read_text(encoding="utf-8"))
    stderr = capsys.readouterr().err

    assert result == 1
    assert report_payload["status"] == "incomplete"
    assert "expected 10 messages" in report_payload["failures"][0]
    assert "expected 10 messages" in stderr
