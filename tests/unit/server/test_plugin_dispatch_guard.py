"""Managed immediate-dispatch grants fence native launch and sanitize failures."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import time
from types import SimpleNamespace

from fastapi import HTTPException
import pytest

from houmao.agents.realm_controller.backends.dispatch_control import HeadlessDispatchControl
from houmao.agents.realm_controller.backends.headless_base import HeadlessInteractiveSession
from houmao.server.config import HoumaoServerConfig
from houmao.server.managed_agents import ManagedHeadlessAuthorityRecord
from houmao.server.models import HoumaoManagedAgentGatewayInternalHeadlessPromptRequest
from houmao.server.service import HoumaoServerService, _ManagedHeadlessAgentHandle


class _Backend(HeadlessInteractiveSession):
    """Expose the production dispatch port without starting a native process."""

    def __init__(self) -> None:
        """Initialize only the request-scoped launch control."""

        self.m_dispatch_control: HeadlessDispatchControl | None = None

    def configure_request_dispatch(self, control: HeadlessDispatchControl | None) -> None:
        """Bind the selected control for this deterministic native launch seam."""

        self.m_dispatch_control = control


class _Controller:
    """Model synchronous direct execution with a separately confirmed launch."""

    def __init__(self) -> None:
        """Initialize optional deterministic race callbacks."""

        self.backend_session = _Backend()
        self.m_before_launch: Callable[[], None] = lambda: None
        self.m_after_launch: Callable[[], None] = lambda: None
        self.m_confirm: bool = True
        self.m_native_launches: int = 0

    def send_prompt(self, prompt: str, **kwargs: object) -> list[object]:
        """Require the live grant immediately before modeled native execution."""

        del prompt, kwargs
        self.m_before_launch()
        control = self.backend_session.m_dispatch_control
        assert control is not None
        control.require_allowed()
        if self.m_confirm:
            control.confirm_handoff()
            self.m_native_launches += 1
        self.m_after_launch()
        return []


@pytest.fixture
def harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Construct a selected owner and an actual payload-free dispatch grant."""

    manifest = tmp_path / "session" / "manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"registry_generation_id":"generation-one"}', encoding="utf-8")
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "turn-plugin-example"
    turn_dir.mkdir(parents=True)
    caller = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: True,
        confirmed=lambda: None,
        deadline=time.monotonic() + 30.0,
        manifest_path=manifest,
        generation_id="generation-one",
    )
    grant = caller.prepare_bridge_permission(turn_dir)
    authority = ManagedHeadlessAuthorityRecord(
        tracked_agent_id="owner-alpha",
        tool="claude",
        backend="claude_headless",
        session_root=str(manifest.parent),
        manifest_path=str(manifest),
        tmux_session_name="HOUMAO-example",
        agent_def_dir=str(tmp_path / "agent-defs"),
        agent_name="example",
        agent_id="owner-alpha",
        created_at_utc="2026-01-01T00:00:00Z",
        updated_at_utc="2026-01-01T00:00:00Z",
    )
    controller = _Controller()
    handle = _ManagedHeadlessAgentHandle(authority=authority, controller=controller)
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path)
    )
    monkeypatch.setattr(service, "_require_headless_agent_ref", lambda _: "owner-alpha")
    monkeypatch.setattr(service, "_reconcile_headless_active_turn", lambda **_: None)
    monkeypatch.setattr(service, "_require_headless_handle", lambda _: handle)
    request = HoumaoManagedAgentGatewayInternalHeadlessPromptRequest(
        prompt="ordinary notification",
        turn_id=turn_dir.name,
        dispatch_guard_file=str(grant),
    )
    return SimpleNamespace(
        service=service,
        controller=controller,
        request=request,
        grant=grant,
        caller=caller,
        manifest=manifest,
        turn_dir=turn_dir,
    )


def test_guarded_managed_dispatch_requires_confirmed_native_handoff(
    harness: SimpleNamespace,
) -> None:
    """A real selected grant confirms synchronous execution and resets the port."""

    before = harness.grant.read_bytes()
    result = harness.service.submit_managed_agent_gateway_internal_headless_prompt(
        "owner-alpha", harness.request
    )
    assert result.success is True
    assert harness.controller.m_native_launches == 1
    assert harness.controller.backend_session.m_dispatch_control is None
    assert harness.grant.read_bytes() == before


def test_unconfirmed_managed_call_cannot_return_success(harness: SimpleNamespace) -> None:
    """Completing a handler without native handoff is an immediate failure."""

    harness.controller.m_confirm = False
    with pytest.raises(HTTPException) as error:
        harness.service.submit_managed_agent_gateway_internal_headless_prompt(
            "owner-alpha", harness.request
        )
    assert error.value.status_code == 503
    assert json.loads(harness.grant.read_text())["active"] is False
    assert harness.controller.backend_session.m_dispatch_control is None


@pytest.mark.parametrize("race", ["revoked", "replaced", "expired"])
def test_late_managed_launch_is_rejected(harness: SimpleNamespace, race: str) -> None:
    """Revocation, generation replacement, and expiry fence delayed native launches."""

    def change() -> None:
        """Change current launch permission after request validation."""

        if race == "revoked":
            harness.caller.cancel()
        elif race == "replaced":
            harness.manifest.write_text(
                '{"registry_generation_id":"generation-two"}', encoding="utf-8"
            )
        else:
            payload = json.loads(harness.grant.read_text())
            payload["expires_at"] = 0
            harness.grant.write_text(json.dumps(payload), encoding="utf-8")

    harness.controller.m_before_launch = change
    with pytest.raises(HTTPException) as error:
        harness.service.submit_managed_agent_gateway_internal_headless_prompt(
            "owner-alpha", harness.request
        )
    assert error.value.status_code == 503
    assert harness.controller.m_native_launches == 0
    assert json.loads(harness.grant.read_text())["active"] is False
    assert harness.controller.backend_session.m_dispatch_control is None


def test_body_replacement_after_handoff_fails_original_call(harness: SimpleNamespace) -> None:
    """An original sender cannot receive success for execution whose body changed."""

    harness.controller.m_after_launch = lambda: harness.manifest.write_text(
        '{"registry_generation_id":"replacement"}', encoding="utf-8"
    )
    with pytest.raises(HTTPException) as error:
        harness.service.submit_managed_agent_gateway_internal_headless_prompt(
            "owner-alpha", harness.request
        )
    assert error.value.status_code == 503
    assert harness.controller.m_native_launches == 1


def test_managed_provider_exception_does_not_leak(harness: SimpleNamespace) -> None:
    """The new guarded path never echoes arbitrary provider or event content."""

    def fail() -> None:
        """Simulate an untrusted backend failure."""

        raise RuntimeError("private-provider-sentinel")

    harness.controller.m_before_launch = fail
    with pytest.raises(HTTPException) as error:
        harness.service.submit_managed_agent_gateway_internal_headless_prompt(
            "owner-alpha", harness.request
        )
    assert error.value.status_code == 503
    assert "private-provider-sentinel" not in str(error.value.detail)
    assert harness.controller.backend_session.m_dispatch_control is None


@pytest.mark.parametrize("change", ["other-owner", "traversal", "missing-turn", "symlink"])
def test_dispatch_guard_cannot_select_another_source(harness: SimpleNamespace, change: str) -> None:
    """The selected grant is bound to one manifest-owned turn directory."""

    updates: dict[str, object] = {}
    if change == "other-owner":
        updates["dispatch_guard_file"] = str(harness.manifest.parent / "another-grant.json")
    elif change == "traversal":
        updates["turn_id"] = "../other"
    elif change == "missing-turn":
        updates["turn_id"] = None
    else:
        saved = harness.grant.with_suffix(".saved")
        harness.grant.rename(saved)
        harness.grant.symlink_to(saved)
    request = harness.request.model_copy(update=updates)
    with pytest.raises(HTTPException) as error:
        harness.service.submit_managed_agent_gateway_internal_headless_prompt(
            "owner-alpha", request
        )
    assert error.value.status_code == 422
    assert harness.controller.m_native_launches == 0


def test_managed_bridge_does_not_reactivate_revoked_caller_grant(harness: SimpleNamespace) -> None:
    """A delayed bridge receives the same source and cannot overwrite cancellation."""

    def inspect() -> None:
        """Read bridge permission without refreshing the caller's original fence."""

        control = harness.controller.backend_session.m_dispatch_control
        before = harness.grant.read_bytes()
        assert control.prepare_bridge_permission(harness.turn_dir) == harness.grant
        assert harness.grant.read_bytes() == before
        harness.caller.cancel()
        with pytest.raises(Exception, match="permission is no longer active"):
            control.prepare_bridge_permission(harness.turn_dir)
        assert json.loads(harness.grant.read_text())["active"] is False

    harness.controller.m_before_launch = inspect
    with pytest.raises(HTTPException):
        harness.service.submit_managed_agent_gateway_internal_headless_prompt(
            "owner-alpha", harness.request
        )
    assert harness.controller.m_native_launches == 0
