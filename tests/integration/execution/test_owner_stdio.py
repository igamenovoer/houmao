"""Actual fixed-helper admission over restricted sudo and isolated SSH."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import sys
from typing import Any

import pytest

from houmao.execution.models import ControllerScopeV1, ExecutionProfileV1, ExecutionRequestV1
from houmao.execution.owner import OwnerPolicyV1
from houmao.execution.protocol import decode_response, encode_request


@pytest.fixture
def execution_entrypoint() -> Path:
    """Require a deliberately selected installed owner entrypoint."""

    configured = os.environ.get("HOUMAO_EXECUTION_ENTRYPOINT")
    if configured is None:
        pytest.skip("Set HOUMAO_EXECUTION_ENTRYPOINT to the installed target houmao-mgr")
    path = Path(configured)
    if not path.is_absolute() or not path.is_file():
        pytest.fail("HOUMAO_EXECUTION_ENTRYPOINT must identify an installed absolute executable")
    return path


@pytest.mark.parametrize("transport", ["sudo", "ssh"])
def test_real_owner_helper_admission_uses_actual_account_without_initializing(
    execution_accounts: Any,
    execution_entrypoint: Path,
    request: pytest.FixtureRequest,
    transport: str,
) -> None:
    """Run the actual product transport and stdio helper as a restricted operator."""

    sandbox = execution_accounts
    endpoint = request.getfixturevalue("execution_ssh") if transport == "ssh" else None
    project = sandbox.owner.home / "project"
    sandbox.run_as(sandbox.owner, ["/usr/bin/mkdir", str(project)])
    policy_path = sandbox.root / "owner-policy.json"
    sandbox.install_helper(f'#!/bin/sh\nexec {shlex.quote(str(execution_entrypoint))} "$@"\n')
    sandbox.authorize_helper_arguments(
        [
            "internals",
            "executor",
            "serve-stdio",
            "--policy",
            str(policy_path),
        ]
    )
    profile = ExecutionProfileV1(
        name="restricted-fixture",
        transport=transport,
        account=sandbox.owner.name,
        entrypoint=str(sandbox.helper),
        policy_path=str(policy_path),
        project_root=str(project),
        expected_uid=sandbox.owner.uid,
        expected_gid=sandbox.owner.gid,
        ssh_host="127.0.0.1" if endpoint is not None else None,
        ssh_port=endpoint.port if endpoint is not None else 22,
        identity_file=str(endpoint.identity_file) if endpoint is not None else None,
        known_hosts_file=str(endpoint.known_hosts_file) if endpoint is not None else None,
    )
    policy = OwnerPolicyV1(
        profile=profile,
        controller=ControllerScopeV1(
            controller_id="restricted-fixture-operator",
            authority="sudo_policy" if transport == "sudo" else "ssh_account",
            operations=("describe",),
            project_roots=(str(project),),
        ),
        uid=sandbox.owner.uid,
        gid=sandbox.owner.gid,
        registry_root=str(sandbox.owner.home / "registry"),
        runtime_root=str(sandbox.owner.home / "runtime"),
    )
    sandbox.write_root_file(policy_path, policy.model_dump_json())
    client = sandbox.root / "client-probe.py"
    sandbox.write_root_file(
        client,
        "\n".join(
            [
                "from houmao.execution.models import ExecutionProfileV1, ExecutionRequestV1",
                "from houmao.execution.transports import execute_request",
                "import sys",
                "profile = ExecutionProfileV1.model_validate_json(sys.argv[1])",
                "request = ExecutionRequestV1.model_validate_json(sys.stdin.buffer.read())",
                "print(execute_request(profile, request).model_dump_json())",
                "",
            ]
        ),
    )
    describe = ExecutionRequestV1(operation="describe")
    invocation = [sys.executable, str(client), profile.model_dump_json()]
    result = sandbox.run_as(sandbox.operator, invocation, input=encode_request(describe).decode())
    response = decode_response(result.stdout.encode())
    assert response.request_id == describe.request_id
    assert response.outcome == "completed", response.model_dump()
    assert response.result == {
        "initialized": False,
        "uid": sandbox.owner.uid,
        "gid": sandbox.owner.gid,
    }
    denied = ExecutionRequestV1(operation="launch")
    result = sandbox.run_as(sandbox.operator, invocation, input=encode_request(denied).decode())
    response = decode_response(result.stdout.encode())
    assert response.outcome == "rejected" and response.admitted is False
    assert response.error_code == "operation_denied"
    drifted = profile.model_copy(update={"environment": {"DIFFERENT_OWNER_ENVIRONMENT": "yes"}})
    result = sandbox.run_as(
        sandbox.operator,
        [sys.executable, str(client), drifted.model_dump_json()],
        input=encode_request(describe).decode(),
    )
    response = decode_response(result.stdout.encode())
    assert response.outcome == "rejected" and response.admitted is False
    assert response.error_code == "context_mismatch"
    for path in (policy.runtime_root, policy.registry_root):
        assert sandbox.run_as(sandbox.owner, ["/usr/bin/test", "-e", path], check=False).returncode
    if transport == "sudo":
        other = sandbox.run_as(
            sandbox.operator,
            [
                "/usr/bin/sudo",
                "-n",
                "-H",
                "-u",
                sandbox.owner.name,
                "--",
                str(sandbox.helper),
                "internals",
                "executor",
                "serve-stdio",
                "--policy",
                str(sandbox.root / "unapproved-policy.json"),
            ],
            check=False,
        )
        assert other.returncode != 0
