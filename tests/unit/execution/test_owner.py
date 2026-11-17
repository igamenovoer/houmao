"""Owner admission tests for observed identity, state initialization, and stdio."""

from __future__ import annotations

from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import pwd
import shutil
import threading
from typing import Any

import pytest

from houmao.execution.models import ControllerScopeV1, ExecutionProfileV1, ExecutionRequestV1
from houmao.execution.context import current_execution_binding
from houmao.execution.owner import (
    OwnerAdmissionError,
    OwnerPolicyV1,
    handle_request,
    load_owner_policy,
    observe_binding,
    serve_stdio,
    validate_observed_binding,
)
from houmao.execution.protocol import decode_response, encode_request
from houmao.execution.tmux import current_tmux_socket_path


@pytest.fixture
def policy(tmp_path: Path) -> OwnerPolicyV1:
    """Select the current account without provisioning an OS user."""

    project = tmp_path / "project"
    project.mkdir()
    profile = ExecutionProfileV1(
        name="unit-owner",
        transport="local",
        account=pwd.getpwuid(os.geteuid()).pw_name,
        entrypoint="/usr/local/bin/houmao-mgr",
        policy_path=str(tmp_path / "policy.json"),
        project_root=str(project),
        expected_uid=os.geteuid(),
        expected_gid=os.getegid(),
        environment={"OWNER_SELECTED": "yes"},
    )
    return OwnerPolicyV1(
        profile=profile,
        controller=ControllerScopeV1(
            controller_id="test-operator",
            authority="local_uid",
            operations=("describe", "launch", "state", "home", "refresh_check", "stop"),
            project_roots=(str(project),),
        ),
        uid=os.geteuid(),
        gid=os.getegid(),
        registry_root=str(tmp_path / "registry"),
        runtime_root=str(tmp_path / "runtime"),
    )


def test_readonly_observation_does_not_initialize_owner_state(policy: OwnerPolicyV1) -> None:
    """A fresh describe is useful without creating state or invoking runtime code."""

    def unexpected(*_: Any) -> dict[str, Any]:
        """Fail if uninitialized inspection enters runtime dispatch."""

        raise AssertionError("dispatch must not run")

    assert observe_binding(policy) is None
    response = handle_request(ExecutionRequestV1(operation="describe"), policy, unexpected)
    assert response.outcome == "completed"
    assert response.binding is None
    assert response.result == {"initialized": False, "uid": policy.uid, "gid": policy.gid}
    assert not Path(policy.runtime_root).exists()
    assert not Path(policy.registry_root).exists()


def test_context_initialization_records_actual_owner_and_stays_stable(
    policy: OwnerPolicyV1,
) -> None:
    """Independent observations retain the one atomically published identity."""

    binding = observe_binding(policy, initialize=True)
    assert binding is not None
    assert binding.uid == os.geteuid() and binding.gid == os.getegid()
    assert binding.account == pwd.getpwuid(os.geteuid()).pw_name
    assert binding == observe_binding(policy, initialize=True)
    assert policy.context_file.stat().st_uid == os.geteuid()
    assert policy.context_file.stat().st_mode & 0o777 == 0o600
    assert not list(Path(policy.runtime_root).glob(".execution-context-*"))


def test_direct_runtime_validation_is_readonly_and_rejects_copied_roots(
    policy: OwnerPolicyV1,
    tmp_path: Path,
) -> None:
    """Copied runtime metadata does not acquire ownership at another state root."""

    binding = observe_binding(policy, initialize=True)
    assert binding is not None
    before = policy.context_file.read_bytes()
    validate_observed_binding(binding)
    assert policy.context_file.read_bytes() == before
    copied_root = tmp_path / "copied-runtime"
    copied_root.mkdir()
    shutil.copy2(policy.context_file, copied_root / policy.context_file.name)
    relocated = binding.model_copy(update={"runtime_root": str(copied_root)})
    with pytest.raises(OwnerAdmissionError, match="differs"):
        validate_observed_binding(relocated)
    changed_groups = binding.model_copy(update={"groups": (*binding.groups, 987654)})
    with pytest.raises(OwnerAdmissionError, match="groups"):
        validate_observed_binding(changed_groups)
    policy.context_file.unlink()
    with pytest.raises(OwnerAdmissionError, match="unavailable"):
        validate_observed_binding(binding)
    assert not policy.context_file.exists()


def test_wrong_actual_identity_is_rejected_before_initialization(policy: OwnerPolicyV1) -> None:
    """A claimed owner label cannot override the effective account."""

    changed = policy.model_copy(update={"uid": policy.uid + 1})
    with pytest.raises(OwnerAdmissionError, match="UID/GID"):
        observe_binding(changed, initialize=True)
    assert not Path(policy.runtime_root).exists()


def test_simultaneous_owner_context_initialization_keeps_one_identity(
    policy: OwnerPolicyV1,
) -> None:
    """Concurrent agent births under one user cannot publish competing contexts."""

    barrier = threading.Barrier(4)

    def initialize() -> str:
        """Race four independent initializations against the same owner state."""

        barrier.wait()
        binding = observe_binding(policy, initialize=True)
        assert binding is not None
        return binding.context_id

    with ThreadPoolExecutor(max_workers=4) as pool:
        identities = list(pool.map(lambda _: initialize(), range(4)))
    assert len(set(identities)) == 1
    assert not list(Path(policy.runtime_root).glob(".execution-context-*"))


def test_scope_expansion_uses_observed_owner_home(
    policy: OwnerPolicyV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An inherited caller HOME cannot make an out-of-scope owner path look admitted."""

    monkeypatch.setenv("HOME", str(Path(policy.profile.project_root).parent))
    response = handle_request(
        ExecutionRequestV1(
            operation="launch", arguments={"profile": "selected", "workdir": "~/project"}
        ),
        policy,
        lambda *_: {},
    )
    assert response.outcome == "rejected"
    assert response.error_code == "project_scope_denied"
    assert not Path(policy.runtime_root).exists()


def test_first_birth_route_mismatch_is_rejected_before_context_creation(
    policy: OwnerPolicyV1,
) -> None:
    """A stale operator profile cannot initialize or launch through changed owner policy."""

    response = handle_request(
        ExecutionRequestV1(
            operation="launch",
            arguments={"profile": "selected"},
            expected_route_fingerprint="0" * 64,
        ),
        policy,
        lambda *_: pytest.fail("mismatched route reached runtime dispatch"),
    )
    assert response.outcome == "rejected" and response.admitted is False
    assert response.error_code == "context_mismatch"
    assert not Path(policy.runtime_root).exists()


def test_operation_and_project_scope_are_checked_before_initialization(
    policy: OwnerPolicyV1,
) -> None:
    """Deny unknown scopes without publishing a context or touching runtime code."""

    def unexpected(*_: Any) -> dict[str, Any]:
        """Fail if denied requests reach application dispatch."""

        raise AssertionError("denied dispatch")

    response = handle_request(ExecutionRequestV1(operation="relaunch"), policy, unexpected)
    assert response.error_code == "operation_denied"
    response = handle_request(
        ExecutionRequestV1(
            operation="launch",
            arguments={
                "profile": "selected",
                "project_dir": str(Path(policy.profile.project_root).parent),
            },
        ),
        policy,
        unexpected,
    )
    assert response.error_code == "project_scope_denied"
    assert not Path(policy.runtime_root).exists()


def test_expected_binding_never_repairs_lost_context(policy: OwnerPolicyV1) -> None:
    """Missing preserved context is a mismatch, even for a mutating request."""

    binding = observe_binding(policy, initialize=True)
    assert binding is not None
    policy.context_file.unlink()
    Path(policy.runtime_root).rmdir()
    response = handle_request(
        ExecutionRequestV1(
            operation="stop",
            agent_id="agent-a",
            expected_binding=binding,
        ),
        policy,
        lambda *_: {},
    )
    assert response.outcome == "rejected"
    assert response.error_code == "context_mismatch"
    assert not Path(policy.runtime_root).exists()


@pytest.mark.parametrize(
    "operation,arguments",
    [
        ("launch", {"unknown_launch_parameter": True}),
        ("launch", {"headless": "yes"}),
        ("launch", {"reasoning_level": True}),
        ("launch", {"gateway_port": []}),
        ("launch", {"env_set": "NAME=value"}),
        ("launch", {"workdir": []}),
        ("prompt", {"prompt": 42}),
        ("prompt", {"prompt": ""}),
        ("prompt", {"prompt": "hello", "reasoning_level": True}),
        ("refresh", {"timeout_seconds": "30"}),
        ("refresh", {"timeout_seconds": True}),
        ("refresh", {"timeout_seconds": -1.0}),
        ("gateway_attach", {"background": "yes"}),
        ("relaunch", {"chat_session": {"mode": "unsupported"}}),
        ("cleanup", {"kind": "session", "dry_run": "false"}),
        ("cleanup", {"kind": []}),
        ("stop", {"unknown_control_parameter": "value"}),
    ],
)
def test_invalid_operation_arguments_do_not_initialize_state(
    policy: OwnerPolicyV1,
    operation: str,
    arguments: dict[str, Any],
) -> None:
    """Shape refusals precede context, registry, and runtime creation even for mutations."""

    controller = policy.controller.model_copy(
        update={
            "operations": (*policy.controller.operations, operation),
        }
    )
    permitted = policy.model_copy(update={"controller": controller})
    if operation == "launch":
        arguments = {"profile": "selected", **arguments}
    response = handle_request(
        ExecutionRequestV1(
            operation=operation,
            arguments=arguments,
            agent_id=None if operation == "launch" else "agent-a",
        ),
        permitted,
        lambda *_: pytest.fail("invalid arguments reached runtime dispatch"),
    )
    assert response.outcome == "rejected" and response.admitted is False
    assert response.error_code == "invalid_arguments"
    assert response.binding is None
    assert not policy.context_file.exists()
    assert not Path(policy.runtime_root).exists()
    assert not Path(policy.registry_root).exists()


def test_valid_launch_value_shapes_reach_dispatch(policy: OwnerPolicyV1) -> None:
    """Preflight accepts genuine CLI value shapes while leaving preparation to dispatch."""

    request = ExecutionRequestV1(
        operation="launch",
        arguments={
            "specialist": "selected-source",
            "headless": True,
            "reasoning_level": 1,
            "gateway_port": 1234,
            "env_set": ["NAME=value"],
            "workdir": policy.profile.project_root,
            "gateway_tui_watch_poll_interval_seconds": 0.25,
        },
    )
    response = handle_request(request, policy, lambda *_: {"accepted": True})
    assert response.outcome == "completed"
    assert response.result == {"accepted": True}


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"profile": ""},
        {"specialist": "  "},
        {"profile": "selected", "specialist": "also-selected"},
    ],
)
def test_invalid_launch_source_selection_leaves_owner_uninitialized(
    policy: OwnerPolicyV1,
    arguments: dict[str, Any],
) -> None:
    """Missing, empty, or conflicting source selectors cannot initialize execution state."""

    response = handle_request(
        ExecutionRequestV1(operation="launch", arguments=arguments),
        policy,
        lambda *_: pytest.fail("invalid source selection reached dispatch"),
    )
    assert response.outcome == "rejected" and response.admitted is False
    assert response.error_code == "invalid_arguments"
    assert not Path(policy.runtime_root).exists()


def test_missing_control_identity_does_not_initialize_context(policy: OwnerPolicyV1) -> None:
    """An owner policy grant cannot replace the required exact target selector."""

    response = handle_request(
        ExecutionRequestV1(operation="stop"),
        policy,
        lambda *_: pytest.fail("missing agent identity reached dispatch"),
    )
    assert response.error_code == "agent_required"
    assert response.admitted is False
    assert not Path(policy.runtime_root).exists()


@pytest.mark.parametrize(
    "operation,arguments",
    [
        ("resume", {}),
        ("cleanup", {"kind": "session", "dry_run": True}),
    ],
)
def test_readonly_control_never_initializes_missing_context(
    policy: OwnerPolicyV1,
    operation: str,
    arguments: dict[str, Any],
) -> None:
    """Resume inspection and cleanup dry runs preserve missing owner authority."""

    permitted = policy.model_copy(
        update={
            "controller": policy.controller.model_copy(
                update={
                    "operations": (*policy.controller.operations, operation),
                }
            )
        }
    )
    response = handle_request(
        ExecutionRequestV1(operation=operation, agent_id="agent-a", arguments=arguments),
        permitted,
        lambda *_: pytest.fail("missing owner context reached dispatch"),
    )
    assert response.error_code == "context_uninitialized"
    assert response.admitted is False
    assert not Path(policy.runtime_root).exists()


def test_dispatch_uses_target_environment_and_explicit_tmux_scope(
    policy: OwnerPolicyV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exclude ambient credentials, caller roots, and inherited tmux authority."""

    for name in ("TMUX", "TMUX_PANE", "SSH_AUTH_SOCK", "SUDO_USER", "PROVIDER_API_KEY"):
        monkeypatch.setenv(name, "synthetic-operator-material")
    monkeypatch.setenv("HOME", "/wrong/operator/home")
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", "/wrong/operator/registry")

    def inspect_environment(*_: Any) -> dict[str, Any]:
        """Observe only non-secret ownership and selector values."""

        assert os.environ["HOME"] == pwd.getpwuid(os.geteuid()).pw_dir
        assert os.environ["USER"] == pwd.getpwuid(os.geteuid()).pw_name
        assert os.environ["OWNER_SELECTED"] == "yes"
        assert os.environ["HOUMAO_GLOBAL_REGISTRY_DIR"] == policy.registry_root
        for name in ("TMUX", "TMUX_PANE", "SSH_AUTH_SOCK", "SUDO_USER", "PROVIDER_API_KEY"):
            assert name not in os.environ
        assert current_tmux_socket_path() == policy.socket_path
        binding = current_execution_binding()
        assert binding is not None and binding.uid == policy.uid
        return {"observed": True}

    response = handle_request(
        ExecutionRequestV1(operation="launch", arguments={"profile": "selected"}),
        policy,
        inspect_environment,
    )
    assert response.outcome == "completed"
    assert response.result == {"observed": True}
    assert os.environ["HOME"] == "/wrong/operator/home"
    assert os.environ["PROVIDER_API_KEY"] == "synthetic-operator-material"
    assert current_tmux_socket_path() is None
    assert current_execution_binding() is None


def test_trusted_policy_load_rejects_symlinks_and_writable_files(
    policy: OwnerPolicyV1,
    tmp_path: Path,
) -> None:
    """Reject untrusted policy files without echoing their contents."""

    path = tmp_path / "policy.json"
    path.write_text(policy.model_dump_json())
    path.chmod(0o600)
    assert load_owner_policy(path) == policy
    link = tmp_path / "policy-link.json"
    link.symlink_to(path)
    with pytest.raises(OwnerAdmissionError, match="untrusted"):
        load_owner_policy(link)
    path.chmod(0o666)
    with pytest.raises(OwnerAdmissionError, match="untrusted"):
        load_owner_policy(path)
    path.write_text('{"secret":"synthetic-private-material"}')
    path.chmod(0o600)
    with pytest.raises(OwnerAdmissionError) as error:
        load_owner_policy(path)
    assert "synthetic-private-material" not in str(error.value)


def test_changed_saved_context_is_rejected_without_rewriting_it(policy: OwnerPolicyV1) -> None:
    """A context record from another observed owner does not become local authority."""

    observe_binding(policy, initialize=True)
    body = json.loads(policy.context_file.read_text())
    body["uid"] += 1
    policy.context_file.write_text(json.dumps(body))
    before = policy.context_file.read_bytes()
    with pytest.raises(OwnerAdmissionError, match="changed"):
        observe_binding(policy, initialize=True)
    assert policy.context_file.read_bytes() == before


def test_stdio_is_framed_and_admitted_failure_is_indeterminate(
    policy: OwnerPolicyV1,
    tmp_path: Path,
) -> None:
    """The helper returns protocol JSON and never exposes application exceptions."""

    path = tmp_path / "policy.json"
    path.write_text(policy.model_dump_json())
    path.chmod(0o600)

    def failing_dispatch(*_: Any) -> dict[str, Any]:
        """Simulate a failure after an operation may have changed runtime state."""

        raise RuntimeError("synthetic-private-material")

    request = ExecutionRequestV1(operation="launch", arguments={"profile": "selected"})
    output = BytesIO()
    assert (
        serve_stdio(
            path,
            input_stream=BytesIO(encode_request(request)),
            output_stream=output,
            dispatch=failing_dispatch,
        )
        == 1
    )
    response = decode_response(output.getvalue())
    assert response.request_id == request.request_id
    assert response.outcome == "indeterminate" and response.admitted is True
    assert b"synthetic-private-material" not in output.getvalue()


def test_stdio_rejects_malformed_request_without_initializing_owner(
    policy: OwnerPolicyV1,
    tmp_path: Path,
) -> None:
    """Bad request framing does not load runtime state or echo request values."""

    path = tmp_path / "policy.json"
    path.write_text(policy.model_dump_json())
    path.chmod(0o600)
    output = BytesIO()
    assert (
        serve_stdio(
            path,
            input_stream=BytesIO(b'{"secret":"synthetic-private-material"}'),
            output_stream=output,
            dispatch=lambda *_: {},
        )
        == 1
    )
    response = decode_response(output.getvalue())
    assert response.outcome == "rejected" and response.admitted is False
    assert b"synthetic-private-material" not in output.getvalue()
    assert not Path(policy.runtime_root).exists()
