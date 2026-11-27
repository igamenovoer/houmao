"""Execution application boundaries retain identity and avoid replay after uncertain mutation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import BytesIO
import json
import os
from pathlib import Path
import pwd
from types import SimpleNamespace
from unittest.mock import Mock

import click
from click.testing import CliRunner
from pydantic import ValidationError
import pytest

from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.native_surface import WebNativeSurfaceV1
from houmao.agents.realm_controller.registry_models import (
    ManagedAgentRegistryRecordV3,
    RegistryIdentityV1,
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryMailboxSlotV1,
    RegistryMailboxesV1,
    RegistryRuntimeV1,
    RegistryTerminalV2,
)
from houmao.execution import application, owner, router
from houmao.execution.context import current_execution_deadline, execution_is_read_only
from houmao.execution.locators import ExecutorAgentLocatorV1
from houmao.execution.locators import load_executor_locator, publish_executor_locator
from houmao.execution.models import (
    ControllerScopeV1,
    ExecutionBindingV1,
    ExecutionProfileV1,
    ExecutionRequestV1,
    ExecutionResponseV1,
    route_fingerprint,
)
from houmao.execution.owner import OwnerAdmissionError, OwnerPolicyV1, handle_request
from houmao.execution.protocol import decode_response, encode_request
from houmao.execution.profiles import ExecutionProfileError
from houmao.execution.tmux import tmux_server_scope
from houmao.passive_server.models import PassiveHeadlessLaunchRequest
from houmao.project.launch_request import ProjectLaunchRequest
from houmao.srv_ctrl.commands import managed_agents as managed
from houmao.srv_ctrl.commands import project_easy
from houmao.srv_ctrl.commands.main import cli
from houmao.srv_ctrl.commands.output import collect_output_payloads


@pytest.fixture
def boundary(tmp_path: Path) -> SimpleNamespace:
    """Provide strict owner, controller, and lifecycle contracts without a harness process."""

    project = tmp_path / "target-project"
    project.mkdir()
    profile = ExecutionProfileV1(
        name="worker",
        transport="local",
        account=pwd.getpwuid(os.geteuid()).pw_name,
        entrypoint="/usr/local/bin/houmao-mgr",
        policy_path=str(tmp_path / "policy.yaml"),
        project_root=str(project),
    )
    scope = ControllerScopeV1(
        controller_id="operator",
        authority="local_uid",
        operations=("describe", "state", "launch", "relaunch", "gateway_attach", "refresh", "stop"),
        project_roots=(str(project),),
    )
    policy = OwnerPolicyV1(
        profile=profile,
        controller=scope,
        uid=os.geteuid(),
        gid=os.getegid(),
        registry_root=str(tmp_path / "registry"),
        runtime_root=str(tmp_path / "runtime"),
    )
    binding = ExecutionBindingV1(
        context_id="owner-context",
        host_id="owner-host",
        account=profile.account,
        uid=policy.uid,
        gid=policy.gid,
        groups=tuple(os.getgroups()),
        registry_root=policy.registry_root,
        runtime_root=policy.runtime_root,
        project_root=profile.project_root,
        profile_name=profile.name,
        transport=profile.transport,
        controller=scope,
        route_fingerprint=route_fingerprint(profile),
        tmux_socket=str(tmp_path / "server.sock"),
    )
    now = datetime.now(UTC)
    record = ManagedAgentRegistryRecordV3(
        agent_id="agent-1",
        agent_name="reviewer",
        generation_id="generation-1",
        mode="headless",
        lifecycle=RegistryLifecycleV1(
            state="active", relaunchable=True, state_updated_at=now.isoformat()
        ),
        identity=RegistryIdentityV1(backend="codex_headless", tool="codex"),
        runtime=RegistryRuntimeV1(
            manifest_path=str(tmp_path / "runtime/session/manifest.json"),
            session_root=str(tmp_path / "runtime/session"),
            agent_def_dir=str(project / ".houmao/agents"),
        ),
        terminal=RegistryTerminalV2(
            current_session_name="owner-session",
            last_session_name="owner-session",
            socket_path=binding.tmux_socket,
        ),
        liveness=RegistryLivenessV1(
            published_at=now.isoformat(), lease_expires_at=(now + timedelta(days=1)).isoformat()
        ),
        mailboxes=RegistryMailboxesV1(
            offline=RegistryMailboxSlotV1(revision="offline-empty", binding=None),
            online=RegistryMailboxSlotV1(revision="online-empty", binding=None),
        ),
        canonical_mail_identity=None,
        execution_binding=binding,
    )
    locator = ExecutorAgentLocatorV1(
        agent_id=record.agent_id,
        agent_name=record.agent_name,
        tool=record.identity.tool,
        mode=record.mode,
        backend=record.identity.backend,
        profile_name=profile.name,
        binding=binding,
    )
    return SimpleNamespace(
        profile=profile, policy=policy, binding=binding, record=record, locator=locator
    )


def _response(
    request: ExecutionRequestV1, boundary: SimpleNamespace, **result: object
) -> ExecutionResponseV1:
    """Return the exact correlated owner result expected from a qualified transport."""

    if request.operation == "describe" and isinstance(result.get("identity"), dict):
        result["identity"] = {
            "tool": boundary.record.identity.tool,
            "mode": boundary.record.mode,
            "backend": boundary.record.identity.backend,
            **result["identity"],
        }
    return ExecutionResponseV1.model_validate(
        {
            "request_id": request.request_id,
            "outcome": "completed",
            "admitted": True,
            "binding": boundary.binding,
            "result": result,
        }
    )


def _registry(monkeypatch: pytest.MonkeyPatch, value: object) -> Mock:
    """Replace only owner registry I/O while retaining public dispatcher behavior."""

    loader = Mock(return_value=value)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.registry_storage.load_managed_agent_record_by_agent_id",
        loader,
    )
    return loader


@pytest.fixture
def owner_manifest(boundary: SimpleNamespace, tmp_path: Path) -> Path:
    """Persist the runtime authority behind one routed registry fixture."""

    record = boundary.record
    path = Path(record.runtime.manifest_path)
    path.parent.mkdir(parents=True)
    with tmux_server_scope(boundary.binding.tmux_socket):
        payload = build_session_manifest_payload(
            SessionManifestRequest(
                launch_plan=LaunchPlan(
                    tool="codex",
                    backend="codex_headless",
                    executable="codex",
                    args=["exec", "--json"],
                    working_directory=tmp_path,
                    home_env_var="CODEX_HOME",
                    home_path=tmp_path / "home",
                    env={},
                    env_var_names=[],
                    role_injection=RoleInjectionPlan(
                        method="native_developer_instructions",
                        role_name="reviewer",
                        prompt="Review the requested change.",
                    ),
                    execution_binding=boundary.binding,
                ),
                role_name="reviewer",
                agent_name=record.agent_name,
                agent_id=record.agent_id,
                registry_generation_id=record.generation_id,
                tmux_session_name=record.terminal.session_name,
                brain_manifest_path=tmp_path / "brain.yaml",
                backend_state={},
                agent_def_dir=Path(record.runtime.agent_def_dir),
            )
        )
    write_session_manifest(path, payload)
    return path


def test_owner_describes_the_manifest_backed_run_mode(
    boundary: SimpleNamespace, owner_manifest: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner discovery publishes the trio used by the operator locator."""

    _registry(monkeypatch, boundary.record)
    request = ExecutionRequestV1(operation="describe", agent_id=boundary.record.agent_id)
    result = application.dispatch_operation(request, boundary.binding, boundary.policy)
    assert result["identity"]["tool"] == "codex"
    assert result["identity"]["mode"] == "headless"
    assert result["identity"]["backend"] == "codex_headless"
    assert result["identity"]["manifest_path"] == str(owner_manifest)


@pytest.mark.parametrize("legacy_manifest", [False, True])
def test_owner_refuses_describe_for_unverified_run_mode(
    boundary: SimpleNamespace,
    owner_manifest: Path,
    monkeypatch: pytest.MonkeyPatch,
    legacy_manifest: bool,
) -> None:
    """A mismatched record or legacy ACP manifest cannot establish routed authority."""

    record = boundary.record
    if legacy_manifest:
        owner_manifest.write_text(
            json.dumps({"schema_version": 5, "backend": "dsh_acp"}), encoding="utf-8"
        )
    else:
        record = record.model_copy(
            update={
                "mode": "tui",
                "identity": RegistryIdentityV1(backend="local_interactive", tool="codex"),
            }
        )
    _registry(monkeypatch, record)
    request = ExecutionRequestV1(operation="describe", agent_id=record.agent_id)
    with pytest.raises(OwnerAdmissionError, match="start a fresh runtime session") as error:
        application.dispatch_operation(request, boundary.binding, boundary.policy)
    assert error.value.code == "unusable_mode_authority"


@pytest.mark.parametrize(
    "change,code",
    [
        ({"generation_id": "replacement"}, "generation_conflict"),
        ({"execution_binding": None}, "context_mismatch"),
        ({"agent_id": "another-agent"}, "identity_mismatch"),
    ],
)
def test_owner_control_checks_exact_authority_before_reconstruction(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, change: dict[str, object], code: str
) -> None:
    """A matching owner alone cannot authorize a different logical ID or generation."""

    _registry(monkeypatch, boundary.record.model_copy(update=change))
    resolve = Mock(side_effect=AssertionError("invalid target must not be reconstructed"))
    monkeypatch.setattr(managed, "resolve_managed_agent_target", resolve)
    request = ExecutionRequestV1(
        operation="state", agent_id="agent-1", generation_id="generation-1"
    )
    with pytest.raises(OwnerAdmissionError) as error:
        application.dispatch_operation(request, boundary.binding, boundary.policy)
    assert error.value.code == code
    resolve.assert_not_called()


@pytest.mark.parametrize(
    "change,code",
    [
        ({"generation_id": "replacement"}, "generation_conflict"),
        ({"execution_binding": None}, "context_mismatch"),
        ({"agent_id": "another-agent"}, "identity_mismatch"),
    ],
)
def test_owner_control_rechecks_authority_after_resolution(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, change: dict[str, object], code: str
) -> None:
    """Concurrent owner-record replacement cannot reach a native control operation."""

    loader = _registry(monkeypatch, boundary.record)
    loader.side_effect = [boundary.record, boundary.record.model_copy(update=change)]
    monkeypatch.setattr(managed, "resolve_managed_agent_target", lambda **kwargs: object())
    state = Mock(side_effect=AssertionError("replacement must not be inspected"))
    monkeypatch.setattr(managed, "managed_agent_state_payload", state)
    request = ExecutionRequestV1(
        operation="state", agent_id="agent-1", generation_id="generation-1"
    )
    with pytest.raises(OwnerAdmissionError) as error:
        application.dispatch_operation(request, boundary.binding, boundary.policy)
    assert error.value.code == code
    state.assert_not_called()


@pytest.mark.parametrize(
    "operation,arguments",
    [
        ("state", {"unexpected": "value"}),
        ("prompt", {"prompt": 42}),
        ("refresh", {"timeout_seconds": True}),
        ("relaunch", {"chat_session": {"mode": "exact"}}),
        ("gateway_attach", {"background": "yes"}),
        ("gateway_attach", {"tui_tracking_timing_overrides": {"watch_poll_interval_seconds": -1}}),
    ],
)
def test_invalid_operation_parameters_fail_before_runtime_resolution(
    boundary: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    arguments: dict[str, object],
) -> None:
    """Closed argument validation happens before preparation can mutate runtime material."""

    _registry(monkeypatch, boundary.record)
    resolve = Mock(side_effect=AssertionError("invalid input must not reconstruct runtime"))
    monkeypatch.setattr(managed, "resolve_managed_agent_target", resolve)
    monkeypatch.setattr(managed, "resolve_relaunch_managed_agent_target", resolve)
    request = ExecutionRequestV1.model_validate(
        {
            "operation": operation,
            "arguments": arguments,
            "agent_id": "agent-1",
            "generation_id": "generation-1",
        }
    )
    with pytest.raises(OwnerAdmissionError):
        application.dispatch_operation(request, boundary.binding, boundary.policy)
    resolve.assert_not_called()


def test_owner_launch_serializes_shared_completion_without_rendering(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dispatch validated launch inputs and serialize the typed launch completion."""

    seen = []

    def launch(request: ProjectLaunchRequest, *, project_dir: Path) -> SimpleNamespace:
        """Act as the maintained application boundary without starting a harness."""

        assert managed._OWNER_LOCAL_TARGET_SCOPE.get()
        assert project_dir == Path(boundary.profile.project_root)
        seen.append(request.model_dump())
        return SimpleNamespace(
            payload={
                "agent_id": "agent-1",
                "agent_name": "reviewer",
                "manifest_path": "/owner/manifest.json",
            }
        )

    monkeypatch.setattr(project_easy, "launch_project_agent", launch)
    result = application.dispatch_operation(
        ExecutionRequestV1(
            operation="launch",
            arguments={
                "profile": "reviewer",
                "mode": "headless",
                "headless_display_style": "json",
                "headless_display_detail": "detail",
                "tmux_server": "socket",
                "tmux_socket_path": "/owner/worker.sock",
            },
        ),
        boundary.binding,
        boundary.policy,
    )
    assert result["agent_id"] == "agent-1"
    assert len(seen) == 1 and seen[0]["profile"] == "reviewer"
    assert seen[0]["mode"] == "headless"
    assert seen[0]["headless_display_style"] == "json"
    assert seen[0]["headless_display_detail"] == "detail"
    assert seen[0]["tmux_server"] == "socket"
    assert seen[0]["tmux_socket_path"] == "/owner/worker.sock"
    assert seen[0]["workdir"] == Path(boundary.profile.project_root)
    assert "executor" not in seen[0]


@pytest.mark.parametrize("delegated", (False, True))
def test_project_launch_reports_optional_gateway_failure_after_admission(
    boundary: SimpleNamespace,
    owner_manifest: Path,
    monkeypatch: pytest.MonkeyPatch,
    delegated: bool,
) -> None:
    """Both CLI adapters report the live identity and exit two after one launch."""

    from houmao.agents.agent_workspace import AgentMemoryPaths
    from houmao.execution import owner
    from houmao.srv_ctrl.commands.agents.core import (
        LocalManagedAgentLaunchResult,
        build_local_launch_completion,
    )

    runtime = owner_manifest.parent
    start = LocalManagedAgentLaunchResult(
        controller=SimpleNamespace(
            agent_identity="reviewer",
            agent_id="agent-1",
            tmux_session_name="owner-session",
            manifest_path=owner_manifest,
            gateway_auto_attach_error="loopback listener unavailable",
        ),
        memory=AgentMemoryPaths(runtime / "memory", runtime / "memo.md", runtime / "pages"),
        runtime_root=runtime,
        mailbox_root=runtime / "mail",
        runtime_root_detail="owner runtime",
        mailbox_root_detail="owner mailbox",
        overlay_root=runtime / ".houmao",
        overlay_root_detail="owner overlay",
        project_overlay_bootstrapped=False,
        overlay_bootstrap_detail="existing overlay",
    )
    completion = build_local_launch_completion(
        launch_result=start, agent_name=None, session_name=None
    )
    launch = Mock(return_value=completion)
    monkeypatch.setattr(project_easy, "launch_project_agent", launch)
    monkeypatch.setattr(router, "load_execution_profile", lambda _: boundary.profile)
    monkeypatch.setattr(owner, "load_owner_policy", lambda _: boundary.policy)
    monkeypatch.setattr(owner, "observe_binding", lambda *_, **__: boundary.binding)
    publish = Mock()
    monkeypatch.setattr(router, "publish_executor_locator", publish)

    def send_to_stdio(_profile: object, request: ExecutionRequestV1) -> ExecutionResponseV1:
        """Exercise owner framing and dispatch through the fixed stdio service."""

        output = BytesIO()
        status = owner.serve_stdio(
            Path(boundary.profile.policy_path),
            input_stream=BytesIO(encode_request(request)),
            output_stream=output,
        )
        response = decode_response(output.getvalue())
        assert status == 0
        assert response.request_id == request.request_id
        assert response.outcome == "completed" and response.admitted
        assert response.result == completion.payload
        return response

    transport = Mock(side_effect=send_to_stdio)
    monkeypatch.setattr(router, "execute_request", transport)
    args = ["--print-json", "project", "agents", "launch", "--profile", "reviewer"]
    if delegated:
        args.extend(("--executor", "worker"))
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 2, (result.output, result.exception)
    report = json.loads(result.output)
    if delegated:
        transport.assert_called_once()
        publish.assert_called_once_with(boundary.locator)
        assert report.pop("execution_context") == boundary.binding.model_dump(mode="json")
    else:
        transport.assert_not_called()
        publish.assert_not_called()
    assert report == completion.payload
    launch.assert_called_once()


def test_owner_resolves_launch_inputs_in_the_target_context(
    boundary: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Resolve relative parameter files and bare env names on the execution owner."""

    target = Path(boundary.profile.project_root)
    runner = CliRunner()
    project = ["project", "--project-dir", str(target)]
    init = runner.invoke(cli, [*project, "init"])
    assert init.exit_code == 0, init.output
    result = runner.invoke(
        cli,
        [
            *project,
            "specialist",
            "create",
            "--name",
            "reviewer",
            "--tool",
            "claude",
            "--claude-oauth-token",
            "synthetic-oauth-token",
        ],
    )
    assert result.exit_code == 0, result.output
    (target / "params.yaml").write_text("include_partial_messages: true\n", encoding="utf-8")
    (tmp_path / "params.yaml").write_text("include_partial_messages: false\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OWNER_SETTING", "operator-value")
    owner_profile = boundary.profile.model_copy(
        update={"environment": {"OWNER_SETTING": "target-value"}}
    )
    owner_policy = boundary.policy.model_copy(update={"profile": owner_profile})

    def launch(**parameters: object) -> dict[str, str]:
        """Observe the private application call without starting a harness."""

        assert parameters["mode"] == "headless"
        assert parameters["direct_tool_params"] == {"include_partial_messages": True}
        assert parameters["launch_env_overrides"] == {
            "OWNER_SETTING": "target-value",
            "EXPLICIT_SETTING": "literal-value",
        }
        return {"agent_id": "agent-1", "agent_name": "reviewer"}

    monkeypatch.setattr(project_easy, "launch_managed_agent_locally", launch)
    monkeypatch.setattr(
        project_easy,
        "build_local_launch_completion",
        lambda launch_result, **_: SimpleNamespace(payload=launch_result),
    )
    response = handle_request(
        ExecutionRequestV1(
            operation="launch",
            arguments={
                "specialist": "reviewer",
                "name": "reviewer",
                "mode": "headless",
                "tool_params": "@params.yaml",
                "env_set": ["OWNER_SETTING", "EXPLICIT_SETTING=literal-value"],
            },
        ),
        owner_policy,
        application.dispatch_operation,
    )
    assert response.outcome == "completed"
    assert response.result is not None and response.result["agent_id"] == "agent-1"
    assert os.environ["OWNER_SETTING"] == "operator-value"


def test_owner_rejects_relative_tmux_socket_before_initializing(
    boundary: SimpleNamespace,
) -> None:
    """Reject malformed one-shot selectors at the owner request boundary."""

    dispatch = Mock()
    response = handle_request(
        ExecutionRequestV1(
            operation="launch",
            arguments={
                "specialist": "reviewer",
                "name": "reviewer",
                "tmux_server": "socket",
                "tmux_socket_path": "worker.sock",
            },
        ),
        boundary.policy,
        dispatch,
    )
    assert response.outcome == "rejected"
    assert response.error_code == "invalid_tmux_server"
    assert not Path(boundary.policy.runtime_root).exists()
    dispatch.assert_not_called()


@pytest.mark.parametrize(
    ("mode", "display_settings", "message"),
    [
        ("tui", {}, r"dsh.*tui.*web"),
        ("web", {"headless_display_detail": "detail"}, r"--headless-display-detail.*'web'"),
    ],
)
def test_owner_rejects_invalid_launch_posture_before_force_launch(
    boundary: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    display_settings: dict[str, str],
    message: str,
) -> None:
    """An unsupported owner-side selection leaves the launch target untouched."""

    project = Path(boundary.profile.project_root)
    monkeypatch.setattr(
        project_easy, "_ensure_project_overlay", lambda **_: SimpleNamespace(project_root=project)
    )
    monkeypatch.setattr(
        project_easy,
        "_load_specialist_or_click",
        lambda **kwargs: SimpleNamespace(tool="dsh", provider="dsh", launch_payload={}),
    )
    project_projection = Mock(side_effect=AssertionError("unexpected catalog materialization"))
    start = Mock(side_effect=AssertionError("unexpected launch attempt"))
    monkeypatch.setattr(
        project_easy, "materialize_project_agent_catalog_projection", project_projection
    )
    monkeypatch.setattr(project_easy, "launch_managed_agent_locally", start)
    request = ExecutionRequestV1(
        operation="launch",
        arguments={
            "specialist": "reviewer",
            "name": "reviewer",
            "agent_id": "agent-1",
            "force_mode": "clean",
            "mode": mode,
            **display_settings,
        },
    )

    with pytest.raises(OwnerAdmissionError, match=message) as error:
        application.dispatch_operation(request, boundary.binding, boundary.policy)
    assert error.value.code == "invalid_run_mode"
    with pytest.raises(click.ClickException, match=message):
        router.require_execution_result(
            ExecutionResponseV1(
                request_id=request.request_id,
                admitted=False,
                outcome="rejected",
                error_code=error.value.code,
                error_message=str(error.value),
            )
        )
    project_projection.assert_not_called()
    start.assert_not_called()


def test_bound_route_rejects_a_different_described_identity(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fresh generation value is insufficient when the owner describes another agent."""

    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)
    calls = []

    def execute(profile: ExecutionProfileV1, request: ExecutionRequestV1) -> ExecutionResponseV1:
        """Capture any accidental second mutation after a mismatched describe response."""

        calls.append(request.operation)
        return _response(
            request, boundary, identity={"agent_id": "another-agent"}, generation_id="generation-1"
        )

    monkeypatch.setattr(router, "execute_request", execute)
    with pytest.raises(click.ClickException, match="identity"):
        router.execute_bound_operation(boundary.locator, "stop")
    assert calls == ["describe"]


def test_bound_describe_verifies_execution_binding(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read-only callers receive the same owner verification as mutation callers."""

    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)
    monkeypatch.setattr(
        router,
        "execute_request",
        lambda profile, request: _response(
            request, boundary, identity={"agent_id": "agent-1"}, generation_id="generation-1"
        ).model_copy(
            update={
                "binding": boundary.binding.model_copy(update={"context_id": "another-context"})
            }
        ),
    )
    with pytest.raises(click.ClickException, match="binding"):
        router.execute_bound_operation(boundary.locator, "describe")


def test_bound_route_refuses_a_stale_run_mode_before_mutation(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same owner and agent can have a replacement generation in another mode."""

    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)
    transport = Mock(
        side_effect=lambda profile, request: _response(
            request,
            boundary,
            identity={
                "agent_id": "agent-1",
                "mode": "tui",
                "backend": "local_interactive",
            },
            generation_id="generation-2",
        )
    )
    monkeypatch.setattr(router, "execute_request", transport)
    with pytest.raises(click.ClickException, match="run mode differs from the locator"):
        router.execute_bound_operation(boundary.locator, "stop")
    assert transport.call_count == 1
    assert transport.call_args.args[1].operation == "describe"


@pytest.mark.parametrize("unsafe_origin", [False, True])
def test_routed_web_launch_emits_only_the_verified_owner_relative_origin(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, unsafe_origin: bool
) -> None:
    """Only the typed, token-free loopback origin may reach the operator output."""

    origin = "http://127.0.0.1:45123"
    session_id = "native-dsh-session"
    private_origin = f"{origin}/#token=owner-native-secret"
    surface = WebNativeSurfaceV1(origin=origin, native_session_id=session_id).model_dump(
        mode="json"
    )
    if unsafe_origin:
        surface["origin"] = private_origin
    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)
    transport = Mock(
        side_effect=lambda profile, request: _response(
            request,
            boundary,
            agent_id="web-agent",
            agent_name="reviewer",
            tool="dsh",
            mode="web",
            backend="dsh_web",
            browser_origin=private_origin,
            native_surface=surface,
        )
    )
    monkeypatch.setattr(router, "execute_request", transport)
    publish = Mock()
    monkeypatch.setattr(router, "publish_executor_locator", publish)

    with collect_output_payloads() as output:
        if unsafe_origin:
            with pytest.raises(click.ClickException, match="locator publication failed"):
                router.launch_with_executor(
                    "worker", ProjectLaunchRequest(profile="reviewer", mode="web")
                )
            publish.assert_not_called()
            assert output[0]["locator_published"] is False
            assert "browser_origin" not in output[0]
        else:
            router.launch_with_executor(
                "worker", ProjectLaunchRequest(profile="reviewer", mode="web")
            )
            assert publish.call_args.args[0].mode == "web"
            assert output[0]["browser_origin"] == origin
            assert output[0]["native_session_id"] == session_id
            assert output[0]["browser_handoff"] == "owner_context_required"
            assert output[0]["execution_context"]["account"] == boundary.binding.account
            assert "attach_command" not in output[0]

    assert transport.call_args.args[1].arguments["mode"] == "web"
    assert "owner-native-secret" not in json.dumps(output)


def test_lost_launch_response_never_publishes_or_replays(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An indeterminate birth is not an invitation to create another logical agent."""

    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)
    transport = Mock(
        return_value=ExecutionResponseV1(
            request_id="request-1",
            outcome="indeterminate",
            admitted=None,
            error_code="transport_timeout",
        )
    )
    publish = Mock(
        side_effect=AssertionError("uncertain launch cannot publish a confirmed locator")
    )
    monkeypatch.setattr(router, "execute_request", transport)
    monkeypatch.setattr(router, "publish_executor_locator", publish)
    with pytest.raises(click.ClickException, match="request=request-1"):
        router.launch_with_executor("worker", ProjectLaunchRequest(profile="reviewer"))
    assert transport.call_count == 1
    publish.assert_not_called()


def test_failed_operator_publication_reports_admitted_identity_without_second_birth(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed operator write leaves the already-launched owner as the recovery target."""

    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)
    transport = Mock(
        side_effect=lambda profile, request: _response(
            request,
            boundary,
            agent_id="agent-1",
            agent_name="reviewer",
            tool="codex",
            mode="headless",
            backend="codex_headless",
        )
    )
    monkeypatch.setattr(router, "execute_request", transport)
    monkeypatch.setattr(
        router,
        "publish_executor_locator",
        Mock(side_effect=OSError("operator registry unavailable")),
    )
    with collect_output_payloads() as output:
        with pytest.raises(click.ClickException, match="Do not launch again"):
            router.launch_with_executor("worker", ProjectLaunchRequest(profile="reviewer"))
    assert transport.call_count == 1
    assert output[0]["outcome"] == "partial_success"
    assert output[0]["agent_id"] == "agent-1"
    assert "reconcile" in output[0]["recovery"]


def test_describe_consumes_mutation_transport_budget(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner discovery cannot grant a second full transport deadline to the mutation."""

    clock = [0.0]
    requests = []
    monkeypatch.setattr(router, "monotonic", lambda: clock[0], raising=False)
    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)

    def execute(profile: ExecutionProfileV1, request: ExecutionRequestV1) -> ExecutionResponseV1:
        """Spend twelve seconds in describe without a wall-clock wait."""

        requests.append(request)
        if request.operation == "describe":
            clock[0] = 12.0
        return _response(
            request, boundary, identity={"agent_id": "agent-1"}, generation_id="generation-1"
        )

    monkeypatch.setattr(router, "execute_request", execute)
    router.execute_bound_operation(boundary.locator, "stop")
    assert [request.operation for request in requests] == ["describe", "stop"]
    assert requests[1].deadline_seconds == pytest.approx(18.0)


def test_expired_describe_budget_prevents_mutation_dispatch(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A completed read does not permit a mutation after the caller's deadline expires."""

    clock = [0.0]
    operations = []
    monkeypatch.setattr(router, "monotonic", lambda: clock[0], raising=False)
    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)

    def execute(profile: ExecutionProfileV1, request: ExecutionRequestV1) -> ExecutionResponseV1:
        """Finish describe after the original finite budget has expired."""

        operations.append(request.operation)
        clock[0] = 31.0
        return _response(
            request, boundary, identity={"agent_id": "agent-1"}, generation_id="generation-1"
        )

    monkeypatch.setattr(router, "execute_request", execute)
    try:
        result = router.execute_bound_operation(boundary.locator, "stop")
    except click.ClickException:
        pass
    else:
        assert result.outcome == "rejected" and result.admitted is False
    assert operations == ["describe"]


def test_native_refresh_timeout_cannot_exceed_request_budget(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner-side refresh honors the remaining operation deadline over a longer explicit value."""

    _registry(monkeypatch, boundary.record)
    monkeypatch.setattr(managed, "resolve_managed_agent_target", lambda **kwargs: object())
    observed = []

    def refresh(target: object, *, timeout_seconds: float) -> dict[str, object]:
        """Capture the budget handed to the native refresh boundary."""

        observed.append(timeout_seconds)
        return {"method": "none", "outcome": "unsupported"}

    monkeypatch.setattr(managed, "refresh_managed_agent", refresh)
    request = ExecutionRequestV1(
        operation="refresh",
        agent_id="agent-1",
        generation_id="generation-1",
        deadline_seconds=3.0,
        arguments={"timeout_seconds": 10.0},
    )
    application.dispatch_operation(request, boundary.binding, boundary.policy)
    assert len(observed) == 1 and 0 < observed[0] <= 3.0


def test_owner_prompt_budget_includes_work_before_application_dispatch(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bound native prompt waits by the request received at the owner."""

    _registry(monkeypatch, boundary.record)
    monkeypatch.setattr(managed, "resolve_managed_agent_target", lambda **_: object())
    clock = [100.0]
    monkeypatch.setattr(owner, "monotonic", lambda: clock[0])
    monkeypatch.setattr(application, "monotonic", lambda: clock[0])

    def observe(*args: object, **kwargs: object):
        """Account for owner observation before the application starts."""

        clock[0] += 0.75
        return boundary.binding

    monkeypatch.setattr(owner, "observe_binding", observe)
    monkeypatch.setattr(
        managed,
        "prompt_managed_agent",
        lambda *args, **kwargs: {"observed_deadline": current_execution_deadline()},
    )
    policy = boundary.policy.model_copy(
        update={
            "controller": boundary.policy.controller.model_copy(update={"operations": ("prompt",)})
        }
    )
    request = ExecutionRequestV1(
        operation="prompt",
        agent_id="agent-1",
        generation_id="generation-1",
        deadline_seconds=2.0,
        arguments={"prompt": "one request"},
    )
    response = handle_request(request, policy, application.dispatch_operation)
    assert response.outcome == "completed"
    assert response.result == {"observed_deadline": 101.75}
    assert current_execution_deadline() is None


@pytest.mark.parametrize("operation,read_only", [("state", True), ("stop", False)])
def test_reconstruction_is_read_only_and_explicit_operation_retains_its_scope(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, operation: str, read_only: bool
) -> None:
    """Admission validation cannot repair files, while explicit mutation retains its authority."""

    _registry(monkeypatch, boundary.record)

    def resolve(**kwargs: object) -> object:
        """Observe the reconstruction-only scope at the actual resolver boundary."""

        assert execution_is_read_only()
        return object()

    def act(target: object) -> dict[str, object]:
        """Observe the declared read/mutation scope after reconstruction completes."""

        assert execution_is_read_only() is read_only
        return {"success": True}

    monkeypatch.setattr(managed, "resolve_managed_agent_target", resolve)
    monkeypatch.setattr(
        managed,
        "managed_agent_state_payload" if operation == "state" else "stop_managed_agent",
        act,
    )
    request = ExecutionRequestV1.model_validate(
        {"operation": operation, "agent_id": "agent-1", "generation_id": "generation-1"}
    )
    application.dispatch_operation(request, boundary.binding, boundary.policy)
    assert not execution_is_read_only()


def test_reconciliation_publishes_only_existing_owner_locator(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Recovery performs one owner describe and a lexical operator write without a new birth."""

    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)
    operations = []

    def execute(profile: ExecutionProfileV1, request: ExecutionRequestV1) -> ExecutionResponseV1:
        """Allow only read-only recovery of an already admitted identity."""

        operations.append(request.operation)
        return _response(
            request,
            boundary,
            identity={
                "agent_id": "agent-1",
                "agent_name": "reviewer",
                "tool": "codex",
                "mode": "headless",
                "backend": "codex_headless",
            },
        )

    monkeypatch.setattr(router, "execute_request", execute)
    root = tmp_path / "operator-registry"
    monkeypatch.setattr(
        router,
        "publish_executor_locator",
        lambda record: publish_executor_locator(record, root=root),
    )
    record = router.reconcile_executor_agent("worker", "agent-1")
    assert operations == ["describe"]
    assert load_executor_locator("agent-1", root=root) == record
    assert not (root / "live_agents").exists()


def test_unconfigured_execution_target_cannot_spawn_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing operator route fails before any privileged helper or runtime setup."""

    monkeypatch.setattr(
        router,
        "load_execution_profile",
        Mock(side_effect=ExecutionProfileError("missing configured profile")),
    )
    transport = Mock(side_effect=AssertionError("unconfigured target must not spawn"))
    monkeypatch.setattr(router, "execute_request", transport)
    with pytest.raises(ExecutionProfileError):
        router.launch_with_executor("unconfigured", ProjectLaunchRequest(profile="reviewer"))
    transport.assert_not_called()


def test_public_http_launch_contract_cannot_supply_execution_authority() -> None:
    """The maintained HTTP body accepts no execution profile or controller grant."""

    payload = {
        "tool": "codex",
        "working_directory": "/owner/project",
        "agent_def_dir": "/owner/project/.houmao/agents",
        "brain_manifest_path": "/owner/runtime/brain.json",
    }
    assert PassiveHeadlessLaunchRequest.model_validate(payload).tool == "codex"
    for field in ("executor", "controller"):
        with pytest.raises(ValidationError) as error:
            PassiveHeadlessLaunchRequest.model_validate({**payload, field: "claimed-authority"})
        assert any(
            item["loc"] == (field,) and item["type"] == "extra_forbidden"
            for item in error.value.errors()
        )
