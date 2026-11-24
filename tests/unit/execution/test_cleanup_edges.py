"""Selected-owner cleanup cannot fall back to caller paths or change captured authority."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from click.testing import CliRunner
import click
import pytest

from houmao.agents.realm_controller.native_refresh_models import NativeHomeV1
from houmao.execution import application, router
from houmao.execution.context import execution_is_read_only
from houmao.execution.locators import (
    ExecutorLocatorError,
    load_executor_locator,
    publish_executor_locator,
)
from houmao.execution.models import ExecutionRequestV1, ExecutionResponseV1
from houmao.execution.owner import OwnerAdmissionError, owner_environment
from houmao.srv_ctrl.commands import managed_agents as managed
from houmao.srv_ctrl.commands import runtime_cleanup
from houmao.srv_ctrl.commands.agents import cleanup as cleanup_commands
from houmao.srv_ctrl.commands.agents import core
from houmao.srv_ctrl.commands.main import cli
from tests.unit.execution.test_application_router import boundary
from tests.unit.srv_ctrl.test_execution_routing import _target

__all__ = ["boundary"]


def _forbid_caller_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail if the public delegated command reaches a local artifact-cleanup producer."""

    for name in (
        "cleanup_managed_session",
        "cleanup_managed_session_logs",
        "cleanup_managed_session_mailbox",
    ):
        monkeypatch.setattr(
            cleanup_commands, name, Mock(side_effect=AssertionError("caller cleanup must not run"))
        )


@pytest.mark.parametrize("kind", ["session", "logs", "mailbox"])
def test_selected_cleanup_delegates_only_identity_and_safe_options(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Inherited single-agent selectors reach owner routing before any caller path resolution."""

    _forbid_caller_cleanup(monkeypatch)
    target = _target()
    resolver = Mock(return_value=target)
    monkeypatch.setattr(managed, "_resolve_executor_target_for_selector", resolver)
    execute = Mock(
        return_value=ExecutionResponseV1(
            request_id="cleanup-request",
            outcome="completed",
            admitted=True,
            binding=target.executor_locator.binding,
            result={"dry_run": True, "owner_only": True},
        )
    )
    monkeypatch.setattr(router, "execute_bound_operation", execute)
    result = CliRunner().invoke(
        cli,
        ["--print-json", "agents", "single", "--agent-id", "agent-1", "cleanup", kind, "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert resolver.call_args.kwargs == {"agent_id": "agent-1", "agent_name": None}
    assert execute.call_args.args[1:] == (
        "cleanup",
        {"kind": kind, "dry_run": True, "purge_registry": False},
    )
    payload = json.loads(result.output)
    assert payload["owner_only"] and payload["execution_context"]["context_id"] == "owner-context"


@pytest.mark.parametrize("option", ["--manifest-path", "--session-root"])
def test_selected_executor_cleanup_rejects_caller_path_overrides(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, option: str
) -> None:
    """A lexical override cannot replace an admitted executor's selected authority."""

    _forbid_caller_cleanup(monkeypatch)
    marker = tmp_path / "caller-marker"
    marker.mkdir()
    (marker / "keep").write_text("caller-owned material")
    monkeypatch.setattr(
        managed, "_resolve_executor_target_for_selector", lambda **kwargs: _target()
    )
    execute = Mock(side_effect=AssertionError("path override must not reach owner mutation"))
    monkeypatch.setattr(router, "execute_bound_operation", execute)
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-id",
            "agent-1",
            "cleanup",
            "session",
            option,
            str(marker if option == "--session-root" else marker / "keep"),
        ],
    )
    assert result.exit_code != 0 and "omit path overrides" in result.output
    assert (marker / "keep").read_text() == "caller-owned material"
    execute.assert_not_called()


def test_unavailable_executor_cleanup_has_no_local_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing owner access is a terminal routing error for the known selected agent."""

    _forbid_caller_cleanup(monkeypatch)
    monkeypatch.setattr(
        managed,
        "_resolve_executor_target_for_selector",
        Mock(side_effect=click.ClickException("recorded owner unavailable")),
    )
    result = CliRunner().invoke(
        cli, ["agents", "single", "--agent-id", "agent-1", "cleanup", "session"]
    )
    assert result.exit_code != 0 and "recorded owner unavailable" in result.output


@pytest.mark.parametrize(
    "arguments",
    [
        ["agents", "single", "cleanup", "session"],
        ["admin", "executors", "reconcile", "--agent-id", "agent-1"],
        ["admin", "executors", "reconcile", "--executor", "worker"],
        ["admin", "executors", "forget"],
    ],
)
def test_missing_public_selectors_never_enter_cleanup_or_execution(
    monkeypatch: pytest.MonkeyPatch, arguments: list[str]
) -> None:
    """Public cardinality/required-option checks cannot infer caller-session authority."""

    _forbid_caller_cleanup(monkeypatch)
    monkeypatch.setattr(
        managed,
        "_resolve_executor_target_for_selector",
        Mock(side_effect=AssertionError("missing selector must not resolve")),
    )
    monkeypatch.setattr(
        router,
        "reconcile_executor_agent",
        Mock(side_effect=AssertionError("missing route must not reconcile")),
    )
    result = CliRunner().invoke(cli, arguments)
    assert result.exit_code != 0
    assert not isinstance(result.exception, AssertionError)


@pytest.mark.parametrize("kind", ["session", "logs", "mailbox"])
def test_owner_cleanup_uses_owner_roots_and_never_accepts_operator_paths(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """The admitted owner invokes maintained cleanup using only the exact logical identity."""

    monkeypatch.setattr(
        "houmao.agents.realm_controller.registry_storage.load_managed_agent_record_by_agent_id",
        lambda agent_id: boundary.record,
    )
    seen = []

    def cleanup(**kwargs: object) -> dict[str, object]:
        """Observe owner scope at the actual filesystem service handoff."""

        assert managed._OWNER_LOCAL_TARGET_SCOPE.get()
        assert execution_is_read_only()
        assert os.environ["HOUMAO_GLOBAL_REGISTRY_DIR"] == boundary.policy.registry_root
        assert os.environ["HOUMAO_GLOBAL_RUNTIME_DIR"] == boundary.policy.runtime_root
        assert kwargs["agent_id"] == "agent-1" and kwargs["agent_name"] is None
        assert kwargs["manifest_path"] is None and kwargs["session_root"] is None
        if kind == "session":
            assert kwargs["expected_record"] is boundary.record
        seen.append(kwargs)
        return {"dry_run": True}

    selected = {
        "session": "cleanup_managed_session",
        "logs": "cleanup_managed_session_logs",
        "mailbox": "cleanup_managed_session_mailbox",
    }[kind]
    monkeypatch.setattr(runtime_cleanup, selected, cleanup)
    request = ExecutionRequestV1(
        operation="cleanup",
        agent_id="agent-1",
        generation_id="generation-1",
        arguments={"kind": kind, "dry_run": True, "purge_registry": False},
    )
    with owner_environment(boundary.policy):
        assert application.dispatch_operation(request, boundary.binding, boundary.policy) == {
            "dry_run": True
        }
    assert len(seen) == 1


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"kind": "session", "manifest_path": "/operator/override"},
        {"kind": "logs", "dry_run": "yes"},
    ],
)
def test_owner_cleanup_rejects_missing_or_override_parameters_before_filesystem_service(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, arguments: dict[str, object]
) -> None:
    """Internal protocol validation cannot widen cleanup authority through extra fields."""

    monkeypatch.setattr(
        "houmao.agents.realm_controller.registry_storage.load_managed_agent_record_by_agent_id",
        lambda agent_id: boundary.record,
    )
    for name in (
        "cleanup_managed_session",
        "cleanup_managed_session_logs",
        "cleanup_managed_session_mailbox",
    ):
        monkeypatch.setattr(
            runtime_cleanup,
            name,
            Mock(side_effect=AssertionError("invalid cleanup must not mutate")),
        )
    request = ExecutionRequestV1.model_validate(
        {
            "operation": "cleanup",
            "agent_id": "agent-1",
            "generation_id": "generation-1",
            "arguments": arguments,
        }
    )
    with pytest.raises(OwnerAdmissionError):
        application.dispatch_operation(request, boundary.binding, boundary.policy)


def test_reconciliation_cannot_replace_existing_owner_binding(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A replaced context with the same agent ID cannot retarget a saved operator locator."""

    root = tmp_path / "operator-registry"
    original = publish_executor_locator(boundary.locator, root=root)
    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)
    replacement = boundary.binding.model_copy(update={"context_id": "replacement-owner-context"})
    monkeypatch.setattr(
        router,
        "execute_request",
        lambda profile, request: ExecutionResponseV1(
            request_id=request.request_id,
            outcome="completed",
            admitted=True,
            binding=replacement,
            result={
                "identity": {
                    "agent_id": "agent-1",
                    "agent_name": "reviewer",
                    "tool": "codex",
                    "mode": "headless",
                    "backend": "codex_headless",
                }
            },
        ),
    )
    monkeypatch.setattr(
        router,
        "publish_executor_locator",
        lambda record: publish_executor_locator(record, root=root),
    )
    with pytest.raises(ExecutorLocatorError, match="different execution binding"):
        router.reconcile_executor_agent("worker", "agent-1")
    assert load_executor_locator("agent-1", root=root) == original


def test_native_home_plain_output_qualifies_owner_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plain paths remain unambiguous when the native home belongs to another owner."""

    monkeypatch.setattr(core, "resolve_managed_agent_target", lambda **kwargs: _target())
    monkeypatch.setattr(
        core,
        "managed_agent_native_home",
        lambda target: NativeHomeV1(
            agent_id="agent-1",
            backend="codex_headless",
            tool="codex",
            home_dir="/owner-only/native",
            identity={"execution_context_id": "owner-context"},
        ),
    )
    result = CliRunner().invoke(
        cli, ["--print-plain", "agents", "single", "--agent-id", "agent-1", "home"]
    )
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "owner-context:/owner-only/native"
