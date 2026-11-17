"""Native transports carry operation data only over bounded stdin/stdout."""

from __future__ import annotations

import os
from pathlib import Path
import pwd
import shlex
import sys

import pytest

from houmao.execution.models import (
    ControllerScopeV1,
    ExecutionBindingV1,
    ExecutionProfileV1,
    ExecutionRequestV1,
    route_fingerprint,
)
from houmao.execution.transports import build_transport_argv, execute_request, transport_environment


def profile(tmp_path: Path, **changes: object) -> ExecutionProfileV1:
    """Build a trusted route targeting one fixture-owned helper."""

    return ExecutionProfileV1.model_validate(
        {
            "name": "worker",
            "transport": "local",
            "account": pwd.getpwuid(os.geteuid()).pw_name,
            "entrypoint": str(tmp_path / "helper"),
            "policy_path": "/etc/houmao/worker.json",
            "project_root": "/target-only/project",
            **changes,
        }
    )


def helper_script(tmp_path: Path, body: str) -> None:
    """Write a private executable protocol fixture without invoking a shell."""

    helper = tmp_path / "helper"
    helper.write_text(f"#!{sys.executable}\n{body}\n")
    helper.chmod(0o700)


def test_native_argv_has_only_fixed_helper_and_transport_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shell payloads belong to JSON rather than local or remote command arguments."""

    monkeypatch.setattr("houmao.execution.transports._native", lambda name: f"/usr/bin/{name}")
    sudo = build_transport_argv(profile(tmp_path, transport="sudo", account="alice"))
    assert sudo[:7] == ["/usr/bin/sudo", "-n", "-H", "-u", "alice", "--", str(tmp_path / "helper")]
    assert sudo[-2:] == ["--policy", "/etc/houmao/worker.json"]
    docker = build_transport_argv(
        profile(tmp_path, transport="docker", account="1000:1000", container_id="a" * 64)
    )
    assert docker[:6] == ["/usr/bin/docker", "exec", "-i", "--user", "1000:1000", "a" * 64]
    assert "-t" not in docker
    ssh = build_transport_argv(
        profile(
            tmp_path,
            transport="ssh",
            account="alice",
            ssh_host="worker.example",
            known_hosts_file="/operator/known_hosts",
            identity_file="/operator/key",
            ssh_port=2222,
        )
    )
    assert "BatchMode=yes" in ssh and "ForwardAgent=no" in ssh
    assert "StrictHostKeyChecking=yes" in ssh and "ClearAllForwardings=yes" in ssh
    assert ssh[-3:-1] == ["--", "worker.example"]
    assert shlex.split(ssh[-1]) == build_transport_argv(profile(tmp_path))


def test_transport_environment_excludes_operator_identity_and_delegation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A child cannot inherit caller roots, keys, tmux server selectors, or loader hooks."""

    for key in (
        "HOME",
        "SSH_AUTH_SOCK",
        "TMUX",
        "TMUX_PANE",
        "SUDO_USER",
        "HOUMAO_GLOBAL_REGISTRY_DIR",
        "ANTHROPIC_API_KEY",
        "PYTHONPATH",
    ):
        monkeypatch.setenv(key, "operator-private")
    environment = transport_environment()
    assert set(environment) == {"PATH", "LANG", "LC_ALL"}
    assert "operator-private" not in environment.values()


def test_real_helper_receives_data_only_and_correlated_response(tmp_path: Path) -> None:
    """Verify actual pipe framing without network or a fake subprocess wrapper."""

    helper_script(
        tmp_path,
        """
import json, os, sys
request = json.load(sys.stdin)
result = {'request_id':request['request_id'], 'outcome':'completed', 'admitted':True,
          'result':{'received':request['arguments'], 'argv':sys.argv[1:], 'environment':dict(os.environ)}}
print(json.dumps(result))
""",
    )
    payload = "$(touch /never-created); `id` 'quoted'"
    response = execute_request(
        profile(tmp_path), ExecutionRequestV1(operation="prompt", arguments={"prompt": payload})
    )
    assert response.outcome == "completed"
    assert response.result["received"] == {"prompt": payload}
    assert response.result["argv"] == [
        "internals",
        "executor",
        "serve-stdio",
        "--policy",
        "/etc/houmao/worker.json",
    ]
    assert "HOME" not in response.result["environment"]


def test_missing_helper_is_confirmed_pre_admission_failure(tmp_path: Path) -> None:
    """No transport process means the mutation could not have been admitted."""

    response = execute_request(profile(tmp_path), ExecutionRequestV1(operation="launch"))
    assert response.outcome == "rejected"
    assert response.admitted is False
    assert response.error_code == "transport_unavailable"


@pytest.mark.parametrize(
    "body,code",
    [
        (
            "import sys; sys.stdin.read(); print('not-json secret-key'); print('stderr-secret',file=sys.stderr)",
            "transport_invalid_result",
        ),
        (
            "import json,sys; json.load(sys.stdin); print(json.dumps({'request_id':'wrong','outcome':'completed','admitted':True}))",
            "transport_uncorrelated_result",
        ),
        (
            "import json,sys; r=json.load(sys.stdin); print(json.dumps({'request_id':r['request_id'],'outcome':'completed','admitted':True})); sys.exit(2)",
            "transport_failed_result",
        ),
    ],
)
def test_failed_result_retains_uncertainty_without_secret_diagnostics(
    tmp_path: Path, body: str, code: str
) -> None:
    """A potentially admitted mutation is never downgraded into a retryable rejection."""

    helper_script(tmp_path, body)
    response = execute_request(profile(tmp_path), ExecutionRequestV1(operation="relaunch"))
    assert response.outcome == "indeterminate"
    assert response.admitted is None
    assert response.error_code == code
    assert "secret" not in response.model_dump_json()


def test_timeout_does_not_resubmit_mutation(tmp_path: Path) -> None:
    """An admitted operation can outlive a lost connection, so send it only once."""

    marker = tmp_path / "attempts"
    helper_script(
        tmp_path,
        f"""
import json, pathlib, sys, time
json.load(sys.stdin)
with pathlib.Path({str(marker)!r}).open('a') as output:
    output.write('one\\n')
time.sleep(10)
""",
    )
    response = execute_request(
        profile(tmp_path, timeout_seconds=0.1), ExecutionRequestV1(operation="relaunch")
    )
    assert response.error_code == "transport_timeout"
    assert response.outcome == "indeterminate"
    assert marker.read_text() == "one\n"


def test_oversized_stdout_is_bounded_and_indeterminate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stop reading output after the limit without claiming an owner rollback."""

    monkeypatch.setattr("houmao.execution.transports.MAX_RESPONSE_BYTES", 1024)
    helper_script(tmp_path, "import sys; sys.stdin.read(); sys.stdout.write('x' * 100000)")
    response = execute_request(profile(tmp_path), ExecutionRequestV1(operation="prompt"))
    assert response.error_code == "transport_output_limit"
    assert response.admitted is None


def test_changed_route_is_rejected_before_transport_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An edited route cannot redirect a command for an existing agent."""

    original = profile(tmp_path)
    binding = ExecutionBindingV1(
        context_id="owner-context",
        host_id="host",
        account=original.account,
        uid=os.geteuid(),
        gid=os.getegid(),
        registry_root="/owner/registry",
        runtime_root="/owner/runtime",
        project_root=original.project_root,
        profile_name=original.name,
        transport=original.transport,
        controller=ControllerScopeV1(
            controller_id="operator", authority="local_uid", operations=("stop",)
        ),
        route_fingerprint=route_fingerprint(original),
    )

    def no_spawn(*args: object, **kwargs: object) -> None:
        """Fail if a mismatched target reaches process execution."""

        raise AssertionError("mismatched route must not spawn")

    monkeypatch.setattr("houmao.execution.transports.subprocess.Popen", no_spawn)
    changed = original.model_copy(update={"project_root": "/other-project"})
    response = execute_request(
        changed, ExecutionRequestV1(operation="stop", expected_binding=binding)
    )
    assert response.error_code == "context_mismatch"
    assert response.admitted is False
