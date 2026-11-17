"""Actual native DSH lifecycle under delegated Linux and SSH execution owners."""

from __future__ import annotations

import json
from pathlib import Path
import shlex
import shutil
import sys
from typing import Any, get_args
from uuid import uuid4

import pytest

from houmao.execution.models import ControllerScopeV1, ExecutionOperation, ExecutionProfileV1
from houmao.execution.owner import OwnerPolicyV1
from tests.integration.agents.dsh.conftest import controlled_messages_server, dsh_executable
from tests.integration.execution.test_owner_stdio import execution_entrypoint


# Imported fixture functions are intentional shared CI infrastructure.
__all__ = ["controlled_messages_server", "dsh_executable", "execution_entrypoint"]


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
                "from houmao.srv_ctrl.commands.credentials import _resolve_agent_def_dir_target, _write_credential_bundle",
                "run = json.loads(Path(sys.argv[1]).read_text())",
                "project = Path(run['project_dir'])",
                "adapter_path = project / '.houmao/agents/tools/dsh/adapter.yaml'",
                "adapter = yaml.safe_load(adapter_path.read_text())",
                "adapter['auth_projection']['file_mappings'] = [{'source': 'execution-key', 'destination': '.ssh/id_ed25519', 'mode': 'copy', 'required': False}]",
                "adapter_path.write_text(yaml.safe_dump(adapter))",
                "private = json.loads((Path(run['run_dir']) / 'private-env.json').read_text())",
                "values = {name: private[name] for name in adapter['auth_projection']['env']['allowlist'] if name in private}",
                "target = _resolve_agent_def_dir_target(project / '.houmao/agents')",
                "for index, key in enumerate(sys.argv[2:]):",
                "    _write_credential_bundle(target=target, tool='dsh', name=f'owner-key-{index}', env_values=values, file_sources={'execution-key': Path(key)}, require_any_input=True, operation='add', clear_env_names=set(), clear_file_sources=set())",
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


@pytest.mark.parametrize("mode,transport", [("headless", "sudo"), ("tui", "ssh")])
def test_native_dsh_launch_control_refresh_and_relaunch_keep_owner(
    execution_accounts: Any,
    execution_entrypoint: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    request: pytest.FixtureRequest,
    mode: str,
    transport: str,
) -> None:
    """Prepare explicit controlled fixtures and drive real owner-bound runtime operations."""

    sandbox = execution_accounts
    endpoint = request.getfixturevalue("execution_ssh") if transport == "ssh" else None
    service_url, model_requests = controlled_messages_server
    repository = Path(__file__).resolve().parents[3]
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
    prepared = sandbox.run_as(
        sandbox.owner,
        [
            sys.executable,
            str(repository / "scripts/agents/test-fixtures/fixture.py"),
            "prepare",
            "--case",
            "cloud-api",
            "--client",
            "dsh",
            "--model",
            "controlled",
            "--mode",
            mode,
            "--surface",
            "manager",
            "--prompt-mode",
            "unattended",
            "--env-file",
            str(selected_env),
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
                "--headless" if mode == "headless" else "--no-headless",
            ],
        )
        assert launched["agent_id"] == agent_id
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
                "--headless" if mode == "headless" else "--no-headless",
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
        _manager(
            sandbox, execution_entrypoint, [*scope, "prompt", "--prompt", "owner-context marker"]
        )
        assert "owner-context marker" in json.dumps(model_requests[-1]["messages"])
        before = sandbox.run_as(sandbox.owner, ["/usr/bin/cat", manifest_path]).stdout
        refreshed = _manager(sandbox, execution_entrypoint, [*scope, "refresh"])
        assert refreshed["outcome"] in {"automatic", "already_current", "refreshed"}
        after = sandbox.run_as(sandbox.owner, ["/usr/bin/cat", manifest_path]).stdout
        assert (
            json.loads(before)["registry_generation_id"]
            == json.loads(after)["registry_generation_id"]
        )
        _manager(sandbox, execution_entrypoint, [*scope, "interrupt"])
        _manager(sandbox, execution_entrypoint, [*scope, "stop"])
        sandbox.tmux(sandbox.owner, ["has-session", "-t", "sibling"])
        _manager(sandbox, execution_entrypoint, [*scope, "relaunch"])
        _manager(sandbox, execution_entrypoint, [*scope, "state"])
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
