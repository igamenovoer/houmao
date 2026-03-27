"""Unit tests for the Stalwart and Cypht interactive gateway demo-pack helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from houmao.agents.realm_controller.gateway_storage import (
    GatewayNotifierAuditUnreadMessage,
    append_gateway_notifier_audit_record,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayMailCheckResponseV1,
    GatewayMailboxMessageV1,
    GatewayMailboxParticipantV1,
)


def _repo_root() -> Path:
    """Return the repository root for this test module."""

    return Path(__file__).resolve().parents[3]


def _helper_module() -> ModuleType:
    """Load the pack-local helper module from disk."""

    helper_path = (
        _repo_root()
        / "scripts"
        / "demo"
        / "gateway-stalwart-cypht-interactive-demo-pack"
        / "scripts"
        / "stalwart_demo_helpers.py"
    )
    module_name = "gateway_stalwart_cypht_interactive_demo_pack_helpers"
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


HELPERS = _helper_module()
PACK_DIR = _repo_root() / "scripts" / "demo" / "gateway-stalwart-cypht-interactive-demo-pack"


def test_tracked_demo_parameters_expose_stalwart_only_accounts() -> None:
    """The tracked parameter file should expose the documented Alice and Bob setup."""

    parameters = HELPERS.load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")

    assert parameters.backend == "local_interactive"
    assert parameters.gateway.host == "127.0.0.1"
    assert parameters.participants["alice"].mailbox_address == "alice@example.test"
    assert parameters.participants["alice"].login_identity == "alice"
    assert parameters.participants["bob"].mailbox_address == "bob@example.test"
    assert parameters.participants["bob"].cypht_password == "admin"


def test_prepare_workspace_from_fixture_copies_dummy_project(tmp_path: Path) -> None:
    """The demo workspace should be copied from the tracked fixture."""

    parameters = HELPERS.load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")
    layout = HELPERS.build_demo_layout(demo_output_dir=tmp_path / "demo-output")

    fixture_dir = HELPERS.prepare_workspace_from_fixture(
        repo_root=_repo_root(),
        parameters=parameters,
        layout=layout,
    )

    marker = json.loads((layout.workspace_dir / ".houmao-demo-workspace.json").read_text())

    assert (
        fixture_dir
        == (_repo_root() / "tests/fixtures/dummy-projects/mailbox-demo-python").resolve()
    )
    assert (layout.workspace_dir / "README.md").is_file()
    assert marker["managed_by"] == "gateway-stalwart-cypht-interactive-demo-pack"


def test_seed_runtime_mailbox_credentials_writes_known_cypht_passwords(tmp_path: Path) -> None:
    """Runtime credential seeding should preserve known Cypht passwords."""

    parameters = HELPERS.load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")

    written = HELPERS.seed_runtime_mailbox_credentials(
        runtime_root=tmp_path / "runtime",
        participants=parameters.participants,
        jmap_url="http://127.0.0.1:10080/jmap",
    )

    alice_path = Path(written["alice"])
    payload = json.loads(alice_path.read_text(encoding="utf-8"))

    assert payload["login_identity"] == "alice"
    assert payload["password"] == "admin"
    assert oct(alice_path.stat().st_mode & 0o777) == "0o600"


def test_start_demo_assembles_stalwart_session_and_gateway_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Start orchestration should use Stalwart transport and loopback gateways."""

    calls: list[list[str]] = []

    def fake_start_demo_cao(
        *, repo_root: Path, demo_output_dir: Path, cao_base_url: str
    ) -> dict[str, object]:
        del repo_root, demo_output_dir, cao_base_url
        return {
            "managed": True,
            "base_url": "http://127.0.0.1:9889",
            "profile_store": str(tmp_path / "cao-profile-store"),
        }

    def fake_start_stack_and_ensure_accounts(
        *,
        repo_root: Path,
        parameters: object,
        layout: object,
    ) -> dict[str, object]:
        del repo_root, parameters, layout
        return {
            "base_url": "http://127.0.0.1:10080",
            "jmap_url": "http://127.0.0.1:10080/jmap",
            "management_url": "http://127.0.0.1:10080/api",
            "cypht_url": "http://127.0.0.1:10081",
        }

    def fake_run_realm_controller_json(
        *,
        repo_root: Path,
        args: list[str],
        stdout_path: Path,
        env: dict[str, str] | None = None,
    ) -> dict[str, object]:
        del repo_root, stdout_path, env
        calls.append(list(args))
        if args[0] == "build-brain":
            return {"manifest_path": str(tmp_path / "runtime" / "brain.yaml")}
        if args[0] == "start-session":
            return {
                "session_manifest": str(
                    tmp_path / "runtime" / f"{args[args.index('--agent-identity') + 1]}.json"
                ),
                "agent_identity": args[args.index("--agent-identity") + 1],
            }
        if args[0] == "attach-gateway":
            identity = Path(args[args.index("--agent-identity") + 1]).stem
            port = 43001 if "alice" in identity else 43002
            return {
                "gateway_host": "127.0.0.1",
                "gateway_port": port,
                "gateway_root": str(tmp_path / f"gateway-{identity}"),
            }
        raise AssertionError(f"unexpected command: {args}")

    def fake_wait_for_gateway_mail_status(
        endpoint: object, *, timeout_seconds: float = 10.0
    ) -> dict[str, object]:
        del endpoint, timeout_seconds
        return {
            "transport": "stalwart",
            "address": "demo@example.test",
            "principal_id": "demo",
            "bindings_version": "2026-03-20T00:00:00Z",
            "schema_version": 1,
        }

    def fake_put_notifier(
        participant_state: dict[str, object], *, interval_seconds: int
    ) -> dict[str, object]:
        del participant_state
        return {"enabled": True, "interval_seconds": interval_seconds}

    monkeypatch.setattr(HELPERS, "start_demo_cao", fake_start_demo_cao)
    monkeypatch.setattr(
        HELPERS, "_start_stack_and_ensure_accounts", fake_start_stack_and_ensure_accounts
    )
    monkeypatch.setattr(HELPERS, "_run_realm_controller_json", fake_run_realm_controller_json)
    monkeypatch.setattr(HELPERS, "_wait_for_gateway_mail_status", fake_wait_for_gateway_mail_status)
    monkeypatch.setattr(HELPERS, "_put_notifier", fake_put_notifier)
    monkeypatch.setattr(
        HELPERS,
        "load_stack_config",
        lambda *, repo_root, parameters: HELPERS.StalwartStackConfig(
            env_file=_repo_root() / "dockers/email-system/.env",
            http_port=10080,
            cypht_http_port=10081,
            bootstrap_user="bootstrap",
            bootstrap_password="bootstrap",
            mail_domain="example.test",
        ),
    )

    state = HELPERS.start_demo(
        repo_root=_repo_root(),
        pack_dir=PACK_DIR,
        demo_output_dir=tmp_path / "demo-output",
        parameters_path=PACK_DIR / "inputs/demo_parameters.json",
    )

    start_calls = [call for call in calls if call[0] == "start-session"]
    attach_calls = [call for call in calls if call[0] == "attach-gateway"]

    assert len(start_calls) == 2
    assert len(attach_calls) == 2
    assert all(
        "--mailbox-transport" in call and call[call.index("--mailbox-transport") + 1] == "stalwart"
        for call in start_calls
    )
    assert all("--mailbox-stalwart-base-url" in call for call in start_calls)
    assert all("--mailbox-stalwart-login-identity" in call for call in start_calls)
    assert all(
        "--gateway-host" in call and call[call.index("--gateway-host") + 1] == "127.0.0.1"
        for call in attach_calls
    )
    assert sorted(state["participants"]) == ["alice", "bob"]


def test_summarize_notifier_audit_records_captures_dedup_and_enqueued() -> None:
    """Notifier audit reduction should surface unread-only outcomes cleanly."""

    queue_path = PACK_DIR / ".." / ".." / ".." / "tmp" / "test-gateway-stalwart-demo-queue.sqlite"
    if queue_path.exists():
        queue_path.unlink()
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        append_gateway_notifier_audit_record(
            queue_path,
            poll_time_utc="2026-03-20T10:00:00+00:00",
            unread_count=1,
            unread_digest="digest-1",
            unread_summary=(
                GatewayNotifierAuditUnreadMessage(
                    message_ref="stalwart:mail-1",
                    thread_ref="stalwart-thread:thread-1",
                    created_at_utc="2026-03-20T10:00:00Z",
                    subject="Unread hello",
                ),
            ),
            request_admission="open",
            active_execution="idle",
            queue_depth=0,
            outcome="enqueued",
            enqueued_request_id="gwreq-1",
        )
        append_gateway_notifier_audit_record(
            queue_path,
            poll_time_utc="2026-03-20T10:00:02+00:00",
            unread_count=1,
            unread_digest="digest-1",
            unread_summary=(
                GatewayNotifierAuditUnreadMessage(
                    message_ref="stalwart:mail-1",
                    thread_ref="stalwart-thread:thread-1",
                    created_at_utc="2026-03-20T10:00:00Z",
                    subject="Unread hello",
                ),
            ),
            request_admission="open",
            active_execution="idle",
            queue_depth=0,
            outcome="dedup_skip",
            detail="unchanged unread set",
        )

        summary = HELPERS.summarize_notifier_audit_records(
            HELPERS.read_gateway_notifier_audit_records(queue_path)
        )
    finally:
        if queue_path.exists():
            queue_path.unlink()

    assert summary["has_enqueued"] is True
    assert summary["has_dedup_skip"] is True
    assert summary["has_poll_error"] is False
    assert summary["unread_subjects"] == ["Unread hello"]
    assert summary["unread_message_refs"] == ["stalwart:mail-1"]


def test_format_check_response_prints_normalized_body_content() -> None:
    """Rendered check output should include sender, message ref, and body text."""

    response = GatewayMailCheckResponseV1(
        transport="stalwart",
        principal_id="bob",
        address="bob@example.test",
        unread_only=True,
        message_count=1,
        unread_count=1,
        messages=[
            GatewayMailboxMessageV1(
                message_ref="stalwart:mail-1",
                thread_ref="stalwart-thread:thread-1",
                created_at_utc="2026-03-20T10:00:00Z",
                subject="Hello Bob",
                unread=True,
                body_text="Hello from Alice",
                sender=GatewayMailboxParticipantV1(address="alice@example.test"),
                to=[GatewayMailboxParticipantV1(address="bob@example.test")],
            )
        ],
    )

    rendered = HELPERS.format_check_response(who="bob", response=response)

    assert "Mailbox: bob (bob@example.test)" in rendered
    assert "From: alice@example.test" in rendered
    assert "Message-Ref: stalwart:mail-1" in rendered
    assert "Hello from Alice" in rendered
