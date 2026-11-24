"""Focused actual Codex owner-routing smoke using a controlled Responses endpoint."""

from __future__ import annotations

from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shlex
import sys
import threading
from typing import Any, get_args
from uuid import uuid4

import pytest

from houmao.execution.models import ControllerScopeV1, ExecutionOperation, ExecutionProfileV1
from houmao.execution.owner import OwnerPolicyV1
from tests.integration.execution.test_native_owner import _manager
from tests.integration.execution.test_owner_stdio import execution_entrypoint

__all__ = ["execution_entrypoint"]


@pytest.fixture
def controlled_responses_server() -> Iterator[tuple[str, list[dict[str, Any]]]]:
    """Serve the minimal real Responses SSE contract used by the local Codex source tests."""

    requests: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        """Capture requests without logging authentication headers or payload contents."""

        def do_POST(self) -> None:
            """Return one completed assistant message without tools or external traffic."""

            assert self.path.endswith("/responses")
            requests.append(json.loads(self.rfile.read(int(self.headers["content-length"]))))
            response_id = f"response-{len(requests)}"
            item = {
                "type": "message",
                "role": "assistant",
                "id": f"message-{len(requests)}",
                "content": [{"type": "output_text", "text": "Controlled Codex owner result"}],
            }
            frames = [
                {"type": "response.created", "response": {"id": response_id}},
                {"type": "response.output_item.done", "item": item},
                {
                    "type": "response.completed",
                    "response": {
                        "id": response_id,
                        "usage": {"input_tokens": 11, "output_tokens": 5, "total_tokens": 16},
                    },
                },
            ]
            # Primary reference: extern/orphan/codex/codex-rs/core/tests/common/responses.rs.
            payload = "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames).encode()
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: Any) -> None:
            """Keep intentionally synthetic fixture traffic out of test diagnostics."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_actual_codex_headless_owner_routing(
    execution_accounts: Any,
    execution_entrypoint: Path,
    controlled_responses_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Launch and complete one native Codex turn as a different authorized Linux owner."""

    selected = os.environ.get("HOUMAO_EXECUTION_CODEX_EXECUTABLE")
    if selected is None:
        pytest.skip(
            "Set HOUMAO_EXECUTION_CODEX_EXECUTABLE to a deliberately selected native Codex executable"
        )
    executable = Path(selected).resolve()
    assert executable.is_file() and executable.is_absolute()
    sandbox = execution_accounts
    base_url, requests = controlled_responses_server
    repository = Path(__file__).resolve().parents[3]
    env_file = sandbox.root / "selected-codex-self-hosted.env"
    sandbox.write_root_file(
        env_file,
        "\n".join(
            [
                "HOUMAO_TEST_SELF_HOSTED_API_KEY=synthetic-codex-owner-only",
                "HOUMAO_TEST_SELF_HOSTED_MODEL=controlled",
                f"HOUMAO_TEST_SELF_HOSTED_OPENAI_BASE_URL={base_url}",
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
            "self-hosted",
            "--client",
            "codex",
            "--model",
            "controlled",
            "--mode",
            "headless",
            "--surface",
            "manager",
            "--prompt-mode",
            "unattended",
            "--env-file",
            str(env_file),
            "--executable",
            str(executable),
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
            sandbox.owner, ["/usr/bin/cat", str(Path(public["run_dir"]) / "run.json")]
        ).stdout
    )
    project = Path(run["project_dir"])
    policy_path = sandbox.root / "codex-owner-policy.json"
    sandbox.install_helper(f'#!/bin/sh\nexec {shlex.quote(str(execution_entrypoint))} "$@"\n')
    sandbox.authorize_helper_arguments(
        ["internals", "executor", "serve-stdio", "--policy", str(policy_path)]
    )
    profile = ExecutionProfileV1(
        name="codex-owner",
        transport="sudo",
        account=sandbox.owner.name,
        entrypoint=str(sandbox.helper),
        policy_path=str(policy_path),
        project_root=str(project),
        expected_uid=sandbox.owner.uid,
        expected_gid=sandbox.owner.gid,
        timeout_seconds=90.0,
        environment={"PATH": "/usr/local/bin:/usr/bin:/bin"},
    )
    policy = OwnerPolicyV1(
        profile=profile,
        controller=ControllerScopeV1(
            controller_id="codex-smoke-operator",
            authority="sudo_policy",
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
        ["/usr/bin/tee", str(profile_dir / "codex-owner.yaml")],
        input=profile.model_dump_json(),
    )
    sandbox.run_as(
        sandbox.operator, ["/usr/bin/chmod", "0600", str(profile_dir / "codex-owner.yaml")]
    )
    agent_id = str(uuid4())
    scope = ["agents", "single", "--agent-id", agent_id]
    admin_key = sandbox.operator.home / "gateway-signing"
    sandbox.run_as(
        sandbox.operator,
        ["/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(admin_key)],
    )
    public_key = sandbox.run_as(
        sandbox.operator, ["/usr/bin/cat", str(admin_key) + ".pub"]
    ).stdout.strip()
    seed = sandbox.owner.home / "gateway-seed.json"
    sandbox.write_root_file(
        seed,
        json.dumps({"admin_keys": [{"principal": "test-operator", "public_key": public_key}]}),
        mode="0600",
    )
    sandbox.root_command(["/usr/bin/chown", sandbox.owner.name, str(seed)])
    assert (
        sandbox.run_as(sandbox.operator, ["/usr/bin/test", "-r", str(seed)], check=False).returncode
        != 0
    )
    assert (
        sandbox.run_as(
            sandbox.owner, ["/usr/bin/test", "-r", str(admin_key)], check=False
        ).returncode
        != 0
    )

    deployment_path = sandbox.owner.home / "gateway-access.json"
    sandbox.write_root_file(deployment_path, '{"public_input_enabled":true}', mode="0600")
    sandbox.root_command(["/usr/bin/chown", sandbox.owner.name, str(deployment_path)])
    probe_path = sandbox.root / "gateway-probe.py"
    sandbox.write_root_file(
        probe_path,
        """import json, sys
from pathlib import Path
from houmao.agents.realm_controller.gateway_access_runtime import gateway_access_for_manifest
from houmao.gateway.access import GatewayClientBinding, GatewayOwner
from houmao.gateway.client import GatewayClient, GatewayHttpError
mode, endpoint, agent_id, context_id, selector = sys.argv[1:]
if mode == "remember-self":
    access = gateway_access_for_manifest(Path(selector))
    anchor = Path.home() / 'previous-self'
    anchor.touch(mode=0o600)
    anchor.write_text(json.dumps([selector, access.target.incarnation]))
    sys.exit(0)
binding = None
generation = None
if mode == "old-self":
    manifest, generation = json.loads((Path.home() / 'previous-self').read_text())
    binding = GatewayClientBinding(
        base_url=endpoint, owner=GatewayOwner(agent_id=agent_id, context_id=context_id),
        purpose="caller", managed_self_manifest_path=manifest,
    )
elif mode != "unsigned":
    binding = GatewayClientBinding(
        base_url=endpoint, owner=GatewayOwner(agent_id=agent_id, context_id=context_id),
        purpose="caller", private_key_path=selector,
    )
gateway = GatewayClient(base_url=endpoint, binding=binding, target_incarnation=generation)
try:
    gateway.status()
except GatewayHttpError as error:
    print(json.dumps({"status": error.status_code, "detail": error.detail}))
else:
    print(json.dumps({"status": 200}))
""",
    )
    try:
        launched = _manager(
            sandbox,
            execution_entrypoint,
            [
                "project",
                "agents",
                "launch",
                "--specialist",
                "fixture-agent",
                "--executor",
                "codex-owner",
                "--agent-id",
                agent_id,
                "--name",
                "owner-codex",
                "--mode",
                "headless",
                "--no-gateway",
                "--gateway-admin-seed",
                str(seed),
            ],
        )
        assert launched["execution_context"]["uid"] == sandbox.owner.uid
        home = _manager(sandbox, execution_entrypoint, [*scope, "home"])
        assert home["tool"] == "codex" and home["backend"] == "codex_headless"
        assert home["home_env_var"] == "CODEX_HOME"
        assert home["identity"]["execution_owner"] == sandbox.owner.name
        assert Path(home["home_dir"]).is_relative_to(sandbox.owner.home)
        mode = sandbox.run_as(
            sandbox.owner, ["/usr/bin/stat", "-c", "%u:%g", launched["manifest_path"]]
        ).stdout.strip()
        assert mode == f"{sandbox.owner.uid}:{sandbox.owner.gid}"
        context_id = launched["execution_context"]["context_id"]
        gateway_status = _manager(
            sandbox, execution_entrypoint, [*scope, "gateway", "attach", "--background"]
        )
        endpoint = f"http://127.0.0.1:{gateway_status['gateway_port']}"

        def _probe(
            account: Any, mode: str, selector: Path, *, target: str = agent_id
        ) -> dict[str, Any]:
            """Run the bound client on the selected Linux account."""

            result = sandbox.run_as(
                account,
                [
                    sys.executable,
                    str(probe_path),
                    mode,
                    endpoint,
                    target,
                    context_id,
                    str(selector),
                ],
            )
            return json.loads(result.stdout) if result.stdout else {}

        assert _probe(sandbox.operator, "unsigned", admin_key)["status"] == 401
        assert _probe(sandbox.operator, "admin", admin_key)["status"] == 200
        assert _probe(sandbox.operator, "admin", admin_key, target=str(uuid4()))["status"] is None
        _probe(sandbox.owner, "remember-self", Path(launched["manifest_path"]))
        _manager(
            sandbox, execution_entrypoint, [*scope, "prompt", "--prompt", "codex owner marker"]
        )
        assert requests and "codex owner marker" in json.dumps(requests[-1].get("input"))
        state = _manager(sandbox, execution_entrypoint, [*scope, "state"])
        assert state["last_turn"]["result"] == "success"
        assert state["identity"]["execution_context"]["uid"] == sandbox.owner.uid
        _manager(sandbox, execution_entrypoint, [*scope, "gateway", "detach"])
        _manager(sandbox, execution_entrypoint, [*scope, "relaunch"])
        reattached = _manager(
            sandbox,
            execution_entrypoint,
            [*scope, "gateway", "attach", "--background", "--access-config", str(deployment_path)],
        )
        endpoint = f"http://127.0.0.1:{reattached['gateway_port']}"
        assert _probe(sandbox.operator, "admin", admin_key)["status"] == 200
        assert _probe(sandbox.owner, "old-self", seed)["status"] is None
    finally:
        _manager(sandbox, execution_entrypoint, [*scope, "stop"], check=False)
