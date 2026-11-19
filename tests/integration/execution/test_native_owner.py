"""Actual native DSH lifecycle under delegated Linux and SSH execution owners."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import sys
from textwrap import dedent
from typing import Any, get_args
from uuid import uuid4

import pytest

from houmao.execution.models import ControllerScopeV1, ExecutionOperation, ExecutionProfileV1
from houmao.execution.owner import OwnerPolicyV1
from tests.integration.agents.dsh.conftest import (
    ControlledModelGate,
    controlled_messages_server,
    controlled_model_gate,
    dsh_executable,
)
from tests.integration.execution.test_owner_stdio import execution_entrypoint


# Imported fixture functions are intentional shared CI infrastructure.
__all__ = [
    "controlled_messages_server",
    "controlled_model_gate",
    "dsh_executable",
    "execution_entrypoint",
]


def _manager(sandbox: Any, entrypoint: Path, arguments: list[str], *, check: bool = True) -> Any:
    """Invoke the maintained operator CLI using only deliberately selected arguments."""

    result = sandbox.run_as(
        sandbox.operator,
        [str(entrypoint), "--print-json", *arguments],
        check=False,
        timeout=120,
    )
    if check:
        assert result.returncode == 0, f"{result.stderr}\n{result.stdout}"
    return json.loads(result.stdout) if result.returncode == 0 else result


def _provision_key_credentials(sandbox: Any, run: dict[str, Any]) -> dict[str, str]:
    """Provision two supported auth-file bindings outside the checkout before birth."""

    keys = [sandbox.owner.home / f"selected-private-key-{index}" for index in range(2)]
    for key in keys:
        sandbox.run_as(
            sandbox.owner,
            [
                "/usr/bin/ssh-keygen",
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-f",
                str(key),
            ],
        )
    script = sandbox.root / "provision-key-credentials.py"
    sandbox.write_root_file(
        script,
        "\n".join(
            [
                "import json, sys",
                "from pathlib import Path",
                "import yaml",
                "from houmao.srv_ctrl.commands.credentials import _DshCredentialUpdate, _resolve_agent_def_dir_target, _write_credential_bundle",
                "run = json.loads(Path(sys.argv[1]).read_text())",
                "project = Path(run['project_dir'])",
                "adapter_path = project / '.houmao/agents/tools/dsh/adapter.yaml'",
                "adapter = yaml.safe_load(adapter_path.read_text())",
                "adapter['auth_projection']['file_mappings'] = [{'source': 'execution-key', 'destination': '.ssh/id_ed25519', 'mode': 'copy', 'required': False}]",
                "adapter_path.write_text(yaml.safe_dump(adapter))",
                "private = json.loads((Path(run['run_dir']) / 'private-env.json').read_text())",
                "params = yaml.safe_load((adapter_path.parent / 'setups/fixture/tool-params.yaml').read_text())['provider']",
                "base_url_env = params['base_url_env']",
                "api_key_env = params['api_key_env']",
                "dsh_update = _DshCredentialUpdate(adapter=params['adapter'], base_url_env=base_url_env, base_url=private[base_url_env], api_key_env=api_key_env, api_key=private.get(api_key_env))",
                "target = _resolve_agent_def_dir_target(project / '.houmao/agents')",
                "for index, key in enumerate(sys.argv[2:]):",
                "    _write_credential_bundle(target=target, tool='dsh', name=f'owner-key-{index}', env_values={}, file_sources={'execution-key': Path(key)}, require_any_input=True, operation='add', clear_env_names=set(), clear_file_sources=set(), dsh_update=dsh_update)",
                "",
            ]
        ),
    )
    sandbox.run_as(
        sandbox.owner,
        [
            sys.executable,
            str(script),
            str(Path(run["run_dir"]) / "run.json"),
            *map(str, keys),
        ],
    )
    return {
        f"owner-key-{index}": sandbox.run_as(
            sandbox.owner, ["/usr/bin/sha256sum", str(key)]
        ).stdout.split()[0]
        for index, key in enumerate(keys)
    }


def _projected_key_hash(sandbox: Any, home: str) -> str:
    """Observe a selected private-key file using a digest rather than exposing key bytes."""

    return sandbox.run_as(
        sandbox.owner,
        [
            "/usr/bin/sha256sum",
            str(Path(home) / ".ssh/id_ed25519"),
        ],
    ).stdout.split()[0]


def _send_stale_stop(
    sandbox: Any, profile_name: str, binding: dict[str, Any], agent_id: str, generation_id: str
) -> dict[str, Any]:
    """Send one old-generation request through the saved restricted owner route."""

    script = sandbox.root / "stale-stop.py"
    sandbox.write_root_file(
        script,
        "\n".join(
            [
                "import sys",
                "from houmao.execution.models import ExecutionBindingV1, ExecutionRequestV1",
                "from houmao.execution.profiles import load_execution_profile",
                "from houmao.execution.transports import execute_request",
                "profile = load_execution_profile(sys.argv[1])",
                "binding = ExecutionBindingV1.model_validate_json(sys.argv[2])",
                "request = ExecutionRequestV1(operation='stop', agent_id=sys.argv[3], generation_id=sys.argv[4], expected_binding=binding)",
                "print(execute_request(profile, request).model_dump_json())",
                "",
            ]
        ),
    )
    return json.loads(
        sandbox.run_as(
            sandbox.operator,
            [
                sys.executable,
                str(script),
                profile_name,
                json.dumps(binding),
                agent_id,
                generation_id,
            ],
        ).stdout
    )


def _crash_gateway(sandbox: Any, manifest_path: str) -> None:
    """Stop only the fixture gateway, leaving the native session and attach state intact."""

    assert Path(manifest_path).is_relative_to(sandbox.owner.home)
    script = "\n".join(
        [
            "import os, signal, sys",
            "from pathlib import Path",
            "from houmao.agents.realm_controller.gateway_storage import gateway_paths_from_manifest_path, read_pid_file",
            "paths = gateway_paths_from_manifest_path(Path(sys.argv[1]))",
            "assert paths is not None",
            "pid = read_pid_file(paths.pid_path)",
            "assert pid is not None and pid > 1",
            "os.kill(pid, signal.SIGKILL)",
        ]
    )
    sandbox.run_as(sandbox.owner, [sys.executable, "-c", script, manifest_path])


def _exercise_authenticated_gateway(
    sandbox: Any, port: int, native_identity: dict[str, Any]
) -> None:
    """Enroll an owner-local caller and interrupt its authenticated Web turn."""

    script = dedent(
        """\
        import json
        from pathlib import Path
        import sys
        from time import monotonic, sleep

        import httpx

        from tests.fixtures.gateway_access import FixtureProofAuth, fixture_admin_key

        native_identity = json.loads(sys.argv[2])
        target = f"http://127.0.0.1:{sys.argv[1]}"
        key, signer = fixture_admin_key(Path.home(), "routed-fixture-admin")
        with httpx.Client(base_url=target, timeout=5) as http:
            enrolled = http.post(
                "/v1/admin/keys",
                json=key.model_dump(mode="json"),
                auth=FixtureProofAuth(signer, purpose="register", proposed_key=key),
            )
            assert enrolled.status_code == 201, enrolled.text
            assert http.get("/v1/control/web/state").status_code == 401
            http.auth = FixtureProofAuth(signer, purpose="admin")

            def state():
                response = http.get("/v1/control/web/state")
                assert response.status_code == 200, response.text
                payload = response.json()
                assert payload["identity"] == native_identity
                assert payload["source"] == "gateway" and payload["availability"] == "available"
                return payload

            assert state()["can_accept_prompt_now"]
            sent = http.post(
                "/v1/control/prompt",
                json={
                    "prompt": "Write 900 words numbered one at a time about astronomy. No tools.",
                    "admission_policy": "ready_only",
                },
            )
            assert sent.status_code == 200, sent.text
            assert sent.json()["outcome"] == "handed_off"
            operation_id = sent.json()["operation_id"]

            deadline = monotonic() + 10
            while monotonic() < deadline:
                observed = state()
                active = observed["active_turn"]
                if active and any(
                    claim["operation_id"] == operation_id and claim["turn"] == active["turn"]
                    for claim in observed["input_claims"]
                ):
                    break
                sleep(0.05)
            else:
                raise AssertionError("The gateway prompt did not produce a correlated active turn")

            interrupted = http.post("/v1/requests", json={"kind": "interrupt", "payload": {}})
            assert interrupted.status_code == 200, interrupted.text
            assert interrupted.json()["request_kind"] == "interrupt"
            deadline = monotonic() + 10
            while monotonic() < deadline:
                observed = state()
                terminal = observed["last_turn"]
                if terminal and terminal["turn"] == active["turn"]:
                    assert terminal["result"] in {"aborted", "cancelled", "abandoned"}, terminal
                    assert observed["can_accept_prompt_now"]
                    break
                sleep(0.05)
            else:
                raise AssertionError("The interrupted turn never reached terminal native state")
        """
    )
    result = sandbox.run_as(
        sandbox.owner,
        [sys.executable, "-c", script, str(port), json.dumps(native_identity)],
        timeout=50,
        check=False,
    )
    assert result.returncode == 0, f"{result.stderr}\n{result.stdout}"


@pytest.mark.parametrize("transport", ["sudo", "ssh"])
def test_native_dsh_web_control_and_gateway_down_lifecycle_keep_owner(
    execution_accounts: Any,
    execution_entrypoint: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    controlled_model_gate: ControlledModelGate,
    request: pytest.FixtureRequest,
    transport: str,
) -> None:
    """Prepare explicit controlled fixtures and drive real owner-bound runtime operations."""

    sandbox = execution_accounts
    endpoint = request.getfixturevalue("execution_ssh") if transport == "ssh" else None
    service_url, model_requests = controlled_messages_server
    repository = Path(__file__).resolve().parents[3]
    live_model = os.environ.get("HOUMAO_TEST_SELF_HOSTED_MODEL")
    live_endpoint = os.environ.get("HOUMAO_TEST_SELF_HOSTED_OPENAI_BASE_URL")
    if live_model or live_endpoint:
        assert live_model and live_endpoint, "Select both the self-hosted model and endpoint"
        model_args = [
            "--case",
            "self-hosted",
            "--model",
            live_model,
            "--base-url",
            live_endpoint,
            "--context-window",
            "262144",
            "--max-output-tokens",
            "1024",
            "--dsh-reasoning",
            '{"off":"none","low":"low","high":"high"}',
            "--dsh-compat",
            '{"supports_developer_role":false}',
        ]
    else:
        selected_env = sandbox.root / "selected-cloud.env"
        sandbox.write_root_file(
            selected_env,
            "\n".join(
                [
                    "HOUMAO_TEST_CLOUD_MODEL=controlled",
                    "HOUMAO_TEST_CLOUD_CONTEXT_WINDOW=8192",
                    "HOUMAO_TEST_CLOUD_MAX_OUTPUT_TOKENS=128",
                    "HOUMAO_TEST_CLOUD_DSH_REASONING=false",
                    "DEEPSEEK_API_KEY=synthetic-execution-owner-only",
                    f"DEEPSEEK_BASE_URL_ANTHROPIC={service_url}",
                    "",
                ]
            ),
        )
        model_args = [
            "--case",
            "cloud-api",
            "--model",
            "controlled",
            "--env-file",
            str(selected_env),
        ]
    prepared = sandbox.run_as(
        sandbox.owner,
        [
            sys.executable,
            str(repository / "scripts/agents/test-fixtures/fixture.py"),
            "prepare",
            *model_args,
            "--client",
            "dsh",
            "--mode",
            "web",
            "--surface",
            "manager",
            "--prompt-mode",
            "unattended",
            "--executable",
            str(dsh_executable),
            "--run-root",
            str(sandbox.owner.home / "native-runs"),
        ],
        check=False,
        timeout=90,
    )
    assert prepared.returncode == 0, f"{prepared.stderr}\n{prepared.stdout}"
    public = json.loads(prepared.stdout)
    run = json.loads(
        sandbox.run_as(
            sandbox.owner,
            ["/usr/bin/cat", str(Path(public["run_dir"]) / "run.json")],
        ).stdout
    )
    project = Path(run["project_dir"])
    key_hashes = _provision_key_credentials(sandbox, run)
    policy_path = sandbox.root / "native-owner-policy.json"
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
    native_bin = sandbox.root / "native-bin"
    sandbox.root_command(["/usr/bin/install", "-d", "-m", "0755", str(native_bin)])
    for name in ("node", "bun"):
        executable = shutil.which(name)
        if executable is not None:
            sandbox.root_command(
                [
                    "/usr/bin/install",
                    "-m",
                    "0755",
                    str(Path(executable).resolve()),
                    str(native_bin / name),
                ]
            )
    profile = ExecutionProfileV1(
        name="native-owner",
        transport=transport,
        account=sandbox.owner.name,
        entrypoint=str(sandbox.helper),
        policy_path=str(policy_path),
        project_root=str(project),
        expected_uid=sandbox.owner.uid,
        expected_gid=sandbox.owner.gid,
        timeout_seconds=90.0,
        environment={"PATH": f"{native_bin}:/usr/local/bin:/usr/bin:/bin"},
        ssh_host="127.0.0.1" if endpoint is not None else None,
        ssh_port=endpoint.port if endpoint is not None else 22,
        identity_file=str(endpoint.identity_file) if endpoint is not None else None,
        known_hosts_file=str(endpoint.known_hosts_file) if endpoint is not None else None,
    )
    policy = OwnerPolicyV1(
        profile=profile,
        controller=ControllerScopeV1(
            controller_id="native-fixture-operator",
            authority="sudo_policy" if transport == "sudo" else "ssh_account",
            operations=tuple(get_args(ExecutionOperation)),
            project_roots=(str(project),),
        ),
        uid=sandbox.owner.uid,
        gid=sandbox.owner.gid,
        registry_root=str(sandbox.owner.home / "registry"),
        runtime_root=str(sandbox.owner.home / "runtime"),
        tmux_socket=str(sandbox.owner.home / "tmux.sock"),
    )
    sandbox.write_root_file(policy_path, policy.model_dump_json())
    profile_dir = sandbox.operator.home / ".config/houmao/executors"
    sandbox.run_as(sandbox.operator, ["/usr/bin/mkdir", "-p", str(profile_dir)])
    sandbox.run_as(sandbox.operator, ["/usr/bin/chmod", "0700", str(profile_dir)])
    sandbox.run_as(
        sandbox.operator,
        ["/usr/bin/tee", str(profile_dir / "native-owner.yaml")],
        input=profile.model_dump_json(),
    )
    sandbox.run_as(
        sandbox.operator, ["/usr/bin/chmod", "0600", str(profile_dir / "native-owner.yaml")]
    )
    assert (
        sandbox.run_as(
            sandbox.operator, ["/usr/bin/test", "-d", str(project)], check=False
        ).returncode
        != 0
    )
    sandbox.tmux(sandbox.operator, ["new-session", "-d", "-s", "same-name", "sleep", "300"])
    agent_id = str(uuid4())
    sibling_id = str(uuid4())
    scope = ["agents", "single", "--agent-id", agent_id]
    try:
        launched = _manager(
            sandbox,
            execution_entrypoint,
            [
                "project",
                "--project-dir",
                str(project),
                "agents",
                "launch",
                "--specialist",
                "fixture-agent",
                "--auth",
                "owner-key-0",
                "--executor",
                "native-owner",
                "--agent-id",
                agent_id,
                "--name",
                "owner-native",
                "--session-name",
                "same-name",
                "--workdir",
                str(project),
                "--gateway-background",
                "--mode",
                "web",
            ],
        )
        assert launched["agent_id"] == agent_id
        assert launched["mode"] == "web" and launched["backend"] == "dsh_web"
        assert launched["native_surface"]["kind"] == "web"
        binding = launched["execution_context"]
        assert binding["uid"] == sandbox.owner.uid and binding["gid"] == sandbox.owner.gid
        assert binding["account"] == sandbox.owner.name
        assert binding["tmux_socket"] == str(sandbox.owner.home / "tmux.sock")
        manifest_path = launched["manifest_path"]
        stat_result = sandbox.run_as(sandbox.owner, ["/usr/bin/stat", "-c", "%u:%g", manifest_path])
        assert stat_result.stdout.strip() == f"{sandbox.owner.uid}:{sandbox.owner.gid}"
        home = _manager(sandbox, execution_entrypoint, [*scope, "home"])
        assert Path(home["home_dir"]).is_relative_to(sandbox.owner.home)
        assert _projected_key_hash(sandbox, home["home_dir"]) == key_hashes["owner-key-0"]
        sibling = _manager(
            sandbox,
            execution_entrypoint,
            [
                "project",
                "agents",
                "launch",
                "--specialist",
                "fixture-agent",
                "--auth",
                "owner-key-1",
                "--executor",
                "native-owner",
                "--agent-id",
                sibling_id,
                "--name",
                "owner-sibling",
                "--session-name",
                "sibling",
                "--gateway-background",
                "--mode",
                "web",
            ],
        )
        sibling_scope = ["agents", "single", "--agent-id", sibling_id]
        assert sibling["agent_id"] == sibling_id
        sibling_home = _manager(sandbox, execution_entrypoint, [*sibling_scope, "home"])
        assert sibling_home["home_dir"] != home["home_dir"]
        sibling_key = _projected_key_hash(sandbox, sibling_home["home_dir"])
        assert sibling_key == key_hashes["owner-key-1"]
        assert sibling_key != key_hashes["owner-key-0"]
        assert sibling["execution_context"] == binding
        sibling_manifest = json.loads(
            sandbox.run_as(
                sandbox.owner,
                ["/usr/bin/cat", sibling["manifest_path"]],
            ).stdout
        )
        _manager(sandbox, execution_entrypoint, [*scope, "state"])
        _manager(sandbox, execution_entrypoint, [*sibling_scope, "state"])
        assert _projected_key_hash(sandbox, sibling_home["home_dir"]) == sibling_key
        assert _projected_key_hash(sandbox, home["home_dir"]) == key_hashes["owner-key-0"]
        prompt = _manager(
            sandbox,
            execution_entrypoint,
            [*scope, "prompt", "--prompt", "Reply only with OWNERWEB02. Do not use tools."],
        )
        assert prompt["success"] is True and prompt["delivery_state"] == "completed"
        if live_model is None:
            assert "OWNERWEB02" in json.dumps(model_requests[-1]["messages"])
        before = sandbox.run_as(sandbox.owner, ["/usr/bin/cat", manifest_path]).stdout
        loaded = json.loads(before)
        refreshed = _manager(sandbox, execution_entrypoint, [*scope, "refresh"])
        assert refreshed["outcome"] in {"automatic", "already_current", "refreshed"}
        after = sandbox.run_as(sandbox.owner, ["/usr/bin/cat", manifest_path]).stdout
        assert loaded["registry_generation_id"] == json.loads(after)["registry_generation_id"]
        gateway = _manager(sandbox, execution_entrypoint, [*scope, "gateway", "status"])
        controlled_model_gate.armed = live_model is None
        try:
            _exercise_authenticated_gateway(
                sandbox, gateway["gateway_port"], loaded["backend_state"]["web_identity"]
            )
        finally:
            controlled_model_gate.release.set()
        detached = _manager(sandbox, execution_entrypoint, [*scope, "gateway", "detach"])
        assert detached["gateway_health"] == "not_attached"
        assert detached["execution_context"] == binding
        offline_state = _manager(sandbox, execution_entrypoint, [*scope, "state"])
        assert offline_state["identity"]["execution_context"] == binding
        assert offline_state["identity"]["mode"] == "web"
        assert offline_state["web"]["source"] == "direct"
        assert offline_state["web"]["availability"] == "available"
        assert (
            offline_state["web"]["identity"]["native_session_id"]
            == (launched["native_surface"]["native_session_id"])
        )
        assert offline_state["gateway"]["gateway_health"] == "not_attached"
        before_reattach = len(model_requests)
        reattached = _manager(
            sandbox, execution_entrypoint, [*scope, "gateway", "attach", "--background"]
        )
        assert reattached["gateway_health"] == "healthy"
        assert reattached["execution_context"] == binding
        assert reattached["native_surface"] == launched["native_surface"]
        assert len(model_requests) == before_reattach
        _crash_gateway(sandbox, manifest_path)
        outage_state = _manager(sandbox, execution_entrypoint, [*scope, "state"])
        assert outage_state["web"]["source"] == "direct"
        assert outage_state["web"]["availability"] == "available"
        assert outage_state["web"]["identity"] == offline_state["web"]["identity"]
        assert outage_state["gateway"]["gateway_health"] != "healthy"
        stopped = _manager(sandbox, execution_entrypoint, [*scope, "stop"])
        assert stopped["success"] and stopped["execution_context"] == binding
        sandbox.tmux(sandbox.owner, ["has-session", "-t", "sibling"])
        revived = _manager(sandbox, execution_entrypoint, [*scope, "relaunch"])
        assert revived["success"] and revived["execution_context"] == binding
        resumed_state = _manager(sandbox, execution_entrypoint, [*scope, "state"])
        assert resumed_state["identity"]["execution_context"] == binding
        assert resumed_state["identity"]["mode"] == "web"
        assert resumed_state["web"]["availability"] == "available"
        assert (
            resumed_state["web"]["identity"]["generation"]
            != (offline_state["web"]["identity"]["generation"])
        )
        rejected = _send_stale_stop(
            sandbox, profile.name, binding, agent_id, offline_state["web"]["identity"]["generation"]
        )
        assert rejected["outcome"] == "rejected" and rejected["admitted"] is False
        assert rejected["error_code"] == "generation_conflict"
        current = _manager(sandbox, execution_entrypoint, [*scope, "state"])
        assert (
            current["web"]["identity"]["generation"]
            == (resumed_state["web"]["identity"]["generation"])
        )
        _manager(sandbox, execution_entrypoint, [*sibling_scope, "state"])
        assert _projected_key_hash(sandbox, sibling_home["home_dir"]) == sibling_key
        assert _projected_key_hash(sandbox, home["home_dir"]) == key_hashes["owner-key-0"]
        sibling_after = json.loads(
            sandbox.run_as(
                sandbox.owner,
                ["/usr/bin/cat", sibling["manifest_path"]],
            ).stdout
        )
        assert sibling_after["registry_generation_id"] == sibling_manifest["registry_generation_id"]
        sandbox.tmux(sandbox.operator, ["has-session", "-t", "same-name"])
    finally:
        _manager(sandbox, execution_entrypoint, [*scope, "stop"], check=False)
        _manager(
            sandbox,
            execution_entrypoint,
            ["agents", "single", "--agent-id", sibling_id, "stop"],
            check=False,
        )
