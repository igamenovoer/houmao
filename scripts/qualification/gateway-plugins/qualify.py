"""Build fixture wheels, then qualify installed gateways without checkout imports.

The ``prepare`` action may use a package index to provision dependency wheels.
The ``run`` action installs only from that wheelhouse and performs no provider
calls. Its installed runner is copied outside the repository before execution.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import sysconfig
import tempfile
import time
from typing import Any, Callable
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import uuid

_SELF_CLIENTS: dict[str, Any] = {}
_ADMIN_CLIENTS: dict[str, Any] = {}


class QualificationError(RuntimeError):
    """Report an explicit prerequisite or behavioral qualification failure."""


def _run(command: list[str], *, cwd: Path, env: dict[str, str], log: Path) -> None:
    """Run a subprocess while keeping raw diagnostics in its private work root."""

    with log.open("a", encoding="utf-8") as stream:
        result = subprocess.run(command, cwd=cwd, env=env, stdout=stream, stderr=stream)
    if result.returncode:
        raise QualificationError(
            f"Subprocess failed with exit code {result.returncode}; inspect the local operation log"
        )


def _external_root(path: Path, source_root: Path) -> Path:
    """Require generated environments, credentials, and runs outside the checkout."""

    root = path.resolve()
    if root == source_root or root.is_relative_to(source_root):
        raise QualificationError("Qualification output must be outside the checkout")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def _clean_environment() -> dict[str, str]:
    """Remove import injection and native-provider authentication fallbacks."""

    env = os.environ.copy()
    for name in tuple(env):
        if name in {"PYTHONPATH", "PYTHONHOME", "TMUX", "TMUX_PANE"} or name.endswith(
            ("_API_KEY", "_AUTH_TOKEN")
        ):
            env.pop(name, None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def _prepare(source_root: Path, wheelhouse: Path) -> dict[str, object]:
    """Build all external distributions and download their dependency wheels."""

    env = _clean_environment()
    log = wheelhouse / "prepare.log"
    projects = [
        source_root,
        source_root / "examples/gateway-plugin",
        source_root / "tests/fixtures/gateway-plugins/fixture-package",
        source_root / "tests/fixtures/gateway-plugins/duplicate-package",
    ]
    for project in projects:
        _run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(wheelhouse), str(project)],
            cwd=wheelhouse,
            env=env,
            log=log,
        )
    selected = _required_wheels(wheelhouse)
    _run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--only-binary=:all:",
            "--dest",
            str(wheelhouse),
            *(str(wheel) for wheel in selected),
        ],
        cwd=wheelhouse,
        env=env,
        log=log,
    )
    return {
        "action": "prepare",
        "result": "passed",
        "wheel_count": len(list(wheelhouse.glob("*.whl"))),
    }


def _required_wheels(wheelhouse: Path) -> list[Path]:
    """Fail setup explicitly when a required product or external wheel is missing."""

    patterns = (
        "houmao-*.whl",
        "houmao_example_notifications-*.whl",
        "houmao_gateway_qualification_fixtures-*.whl",
        "houmao_gateway_duplicate_fixture-*.whl",
    )
    wheels: list[Path] = []
    for pattern in patterns:
        matches = sorted(wheelhouse.glob(pattern))
        if len(matches) != 1:
            raise QualificationError(f"Setup requires exactly one wheel matching {pattern}")
        wheels.append(matches[0])
    return wheels


def _qualify(source_root: Path, wheelhouse: Path, work_root: Path) -> dict[str, object]:
    """Install a fresh environment offline and run its copied qualification driver."""

    artifacts = [
        {"filename": wheel.name, "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}
        for wheel in _required_wheels(wheelhouse)
    ]
    real_tmux = shutil.which("tmux")
    if real_tmux is None:
        raise QualificationError("Setup requires a real tmux executable")
    if shutil.which("ps") is None:
        raise QualificationError("Setup requires ps to confirm owned fixture process cleanup")
    if (work_root / "venv").exists():
        raise QualificationError("Setup requires a fresh work root without an existing venv")
    env = _clean_environment()
    log = work_root / "operations.log"
    _run([sys.executable, "-m", "venv", str(work_root / "venv")], cwd=work_root, env=env, log=log)
    python = work_root / "venv/bin/python"
    _run(
        [
            str(python),
            "-m",
            "pip",
            "--isolated",
            "install",
            "--no-index",
            "--find-links",
            str(wheelhouse),
            "Houmao",
            "houmao-example-notifications",
            "houmao-gateway-qualification-fixtures",
            "houmao-gateway-duplicate-fixture",
        ],
        cwd=work_root,
        env=env,
        log=log,
    )
    runner = work_root / "installed_runner.py"
    shutil.copyfile(Path(__file__).resolve(), runner)
    env["PATH"] = str(work_root / "venv/bin") + os.pathsep + env.get("PATH", "")
    env["HOUMAO_PLUGIN_FIXTURE_REAL_TMUX"] = real_tmux
    env["HOUMAO_GLOBAL_REGISTRY_DIR"] = str(work_root / "registry")
    env["XDG_CONFIG_HOME"] = str(work_root / "config")
    env["HOUMAO_PLUGIN_UNSELECTED_IMPORT_MARKER"] = str(work_root / "unselected-imported")
    # Unix-domain socket limits also apply when pytest supplies a long work
    # root. This private namespace is short and belongs only to this run.
    with tempfile.TemporaryDirectory(prefix="hgp-", dir="/tmp") as socket_root:
        env["TMUX_TMPDIR"] = socket_root
        _prepare_isolated_socket(socket_root)
        try:
            _run(
                [
                    str(python),
                    "-I",
                    str(runner),
                    "installed-run",
                    "--source-root",
                    str(source_root),
                    "--work-root",
                    str(work_root),
                ],
                cwd=work_root,
                env=env,
                log=log,
            )
        finally:
            subprocess.run(
                [real_tmux, "-S", _isolated_socket(socket_root), "kill-server"],
                cwd=work_root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
    report = json.loads((work_root / "qualification.json").read_text(encoding="utf-8"))
    report["artifacts"] = artifacts
    (work_root / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def _isolated_socket(socket_root: str) -> str:
    """Select the runtime's default socket inside this run's private tmux root."""

    return str(Path(socket_root) / f"tmux-{os.getuid()}" / "default")


def _prepare_isolated_socket(socket_root: str) -> None:
    """Provide the parent required by tmux's explicit socket option."""

    Path(_isolated_socket(socket_root)).parent.mkdir(mode=0o700)


def _tmux_command(*arguments: str) -> list[str]:
    """Select only the installed runner's private tmux server."""

    return [
        os.environ["HOUMAO_PLUGIN_FIXTURE_REAL_TMUX"],
        "-S",
        _isolated_socket(os.environ["TMUX_TMPDIR"]),
        *arguments,
    ]


def _bind_self(base_url: str, controller: Any, *, save: Path | None = None) -> None:
    """Use the current fixture generation's explicit owner-local proof binding."""

    from houmao.agents.realm_controller.gateway_access_runtime import owner_gateway_client_binding
    from houmao.agents.realm_controller.gateway_client import GatewayClient

    port = urlsplit(base_url).port
    _require(port is not None, "Qualification gateway did not publish a resolved port")
    assert port is not None
    binding, incarnation = owner_gateway_client_binding(
        controller.manifest_path,
        port=port,
        private=True,
        prefer_self=True,
    )
    _require(
        binding is not None and binding.base_url == base_url, "Fixture self binding unavailable"
    )
    _SELF_CLIENTS[base_url] = GatewayClient(
        base_url=base_url,
        binding=binding,
        target_incarnation=incarnation,
        timeout_seconds=25,
    )
    if save is not None:
        assert binding is not None
        descriptor = os.open(save, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(binding.model_dump_json().encode())


def _bind_admin(base_url: str, controller: Any) -> None:
    """Select the seeded and explicitly configured admin for an installed gateway."""

    from houmao.agents.realm_controller.gateway_access_runtime import owner_gateway_client_binding
    from houmao.agents.realm_controller.gateway_client import GatewayClient

    port = urlsplit(base_url).port
    assert port is not None
    binding, incarnation = owner_gateway_client_binding(
        controller.manifest_path,
        port=port,
        private=False,
    )
    _require(
        binding is not None and binding.base_url == base_url and binding.purpose == "admin",
        "Fixture admin binding unavailable",
    )
    _ADMIN_CLIENTS[base_url] = GatewayClient(
        binding=binding,
        target_incarnation=incarnation,
        timeout_seconds=25,
    )


def _prepare_request(
    base_url: str,
    path: str,
    payload: dict[str, Any] | None,
    *,
    signed: bool = True,
    client: Any = None,
) -> urllib.request.Request:
    """Prepare the exact gateway request, including proof for plugin operations."""

    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    method = "POST" if data is not None else "GET"
    headers = {"Content-Type": "application/json"} if data else {}
    if signed and (path.startswith("/v1/plugins") or client is not None):
        binding = client if client is not None else _SELF_CLIENTS.get(base_url)
        _require(binding is not None, "Qualification selected no explicit gateway caller binding")
        return binding._prepare_request(method, path, data, headers)
    return urllib.request.Request(base_url + path, data=data, method=method, headers=headers)


def _request(
    base_url: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    signed: bool = True,
    client: Any = None,
) -> tuple[int, Any]:
    """Call the real gateway, returning structured errors for assertions."""

    from houmao.agents.realm_controller.errors import GatewayHttpError
    from houmao.agents.realm_controller.gateway_client import _build_gateway_client_opener

    try:
        request = _prepare_request(base_url, path, payload, signed=signed, client=client)
    except GatewayHttpError as error:
        if error.status_code is None:
            raise
        return error.status_code, {"detail": error.detail}
    opener = _build_gateway_client_opener(respect_proxy_env=False, ssl_context=None)
    try:
        with opener.open(request, timeout=25) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


def _fixture_admin(file_path: Path) -> Any:
    """Generate an explicit fixture admin key in owner-only private storage."""

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from houmao.gateway.access import GatewayAdminKey, public_key_text

    signer = Ed25519PrivateKey.generate()
    descriptor = os.open(file_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as target:
        target.write(
            signer.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.OpenSSH,
                serialization.NoEncryption(),
            )
        )
    return GatewayAdminKey(
        principal="fixture-admin", public_key=public_key_text(signer.public_key())
    )


def _verify_plugin_access(
    base_url: str,
    *,
    root: Path,
    private_paths: tuple[str, ...],
    admin_path: str,
    admin_payload: dict[str, Any],
) -> None:
    """Verify the installed plugin against both admin states and both signing roles."""

    from houmao.agents.realm_controller.gateway_client import GatewayClient
    from houmao.gateway.access import GatewayClientBinding

    unsigned = GatewayClient(base_url=base_url)
    discovery = unsigned.describe_endpoint()
    _require(
        discovery.admin_access == "open", "Fresh fixture did not start with open administration"
    )
    for path in private_paths:
        _require(
            _request(base_url, path, signed=False)[0] == 401, "An unsigned private probe passed"
        )
        _require(
            _request(base_url, path)[0] == 200, "Current self proof did not admit ordinary access"
        )
    _require(
        _request(base_url, admin_path, admin_payload, signed=False)[0] == 200,
        "Open policy did not admit an anonymous plugin control",
    )

    file_path = root / "fixture-admin.key"
    key = _fixture_admin(file_path)
    registration = GatewayClientBinding(
        base_url=base_url,
        owner=discovery.target.owner,
        purpose="register",
        private_key_path=str(file_path),
    )
    GatewayClient(
        binding=registration,
        target_incarnation=discovery.target.incarnation,
        registration_key=key,
    ).add_admin_key(key)
    admin = GatewayClient(
        binding=registration.model_copy(update={"purpose": "admin"}),
        target_incarnation=discovery.target.incarnation,
    )
    try:
        _require(
            unsigned.describe_endpoint().admin_access == "key_required",
            "First enrollment failed to close open administration",
        )
        _require(
            _request(base_url, admin_path, admin_payload, signed=False)[0] == 401,
            "A key-required unsigned plugin control passed",
        )
        _require(
            _request(base_url, admin_path, admin_payload)[0] == 403,
            "Self proof authorized a key-required plugin control",
        )
        _require(
            _request(base_url, admin_path, admin_payload, client=admin)[0] == 200,
            "Listed admin proof did not admit the plugin control",
        )
        for path in private_paths:
            _require(
                _request(base_url, path)[0] == 200,
                "Current self proof did not retain ordinary access after enrollment",
            )
            _require(
                _request(base_url, path, client=admin)[0] == 200,
                "Listed admin proof did not admit ordinary plugin access",
            )
    finally:
        admin.remove_admin_key(key.key_id)
    _require(
        unsigned.describe_endpoint().admin_access == "open",
        "Final removal did not reopen plugin administration",
    )


def _event(source_id: str) -> dict[str, object]:
    """Create a public event with no credential or real user content."""

    return {
        "source_event_id": source_id,
        "text": "Synthetic qualification notification",
        "metadata": {},
    }


def _wait(predicate: Callable[[], bool], message: str, *, seconds: float = 15.0) -> None:
    """Wait for a bounded local state transition with a specific failure reason."""

    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise QualificationError(message)


def _require(condition: bool, message: str) -> None:
    """Raise an assertion that remains active under optimized interpreters."""

    if not condition:
        raise QualificationError(message)


def _ready(base_url: str) -> bool:
    """Read normal headless readiness from the actual gateway."""

    _, state = _request(base_url, "/v1/control/headless/state", client=_ADMIN_CLIENTS.get(base_url))
    return state.get("can_accept_prompt_now") is True


def _attach_running(controller: Any) -> str:
    """Attach with persisted settings and wait for the selected example."""

    attached = controller.attach_gateway()
    _require(attached.status == "ok", "Normal gateway restart failed")
    status = controller.gateway_status()
    base_url = f"http://{status.gateway_host}:{status.gateway_port}"
    _bind_self(base_url, controller)
    _wait(
        lambda: (
            _request(base_url, "/v1/plugins/notifications/_status")[1].get("lifecycle") == "running"
        ),
        "Restarted gateway did not restore its plugin selection",
    )
    return base_url


def _arm_handoff_barrier(root: Path, control: dict[str, Any], control_path: Path) -> None:
    """Select a new finite CLI barrier without retaining an event payload."""

    (root / "paused").unlink(missing_ok=True)
    (root / "paused.pid").unlink(missing_ok=True)
    (root / "released").unlink(missing_ok=True)
    control["pause_handoff"] = True
    control_path.write_text(json.dumps(control), encoding="utf-8")


def _process_alive(pid: int) -> bool:
    """Check only the explicitly recorded fixture PID, rejecting zombies."""

    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "stat="],
        capture_output=True,
        text=True,
        check=False,
    )
    state = result.stdout.strip()
    return result.returncode == 0 and bool(state) and state[0] not in {"Z", "X"}


def _drop_success_reply(base_url: str, cursor: Path, count_file: Path) -> None:
    """Discard an actual successful reply at the sender application boundary."""

    listener = urlsplit(base_url)
    connection = http.client.HTTPConnection(listener.hostname, listener.port, timeout=25)
    try:
        request = _prepare_request(
            base_url, "/v1/plugins/notifications/notify", _event("lost-reply")
        )
        connection.request(
            request.get_method(),
            urlsplit(request.full_url).path,
            body=request.data,
            headers=dict(request.header_items()),
        )
        _wait(
            lambda: (
                int(count_file.read_text(encoding="utf-8")) == 3
                and cursor.read_text(encoding="utf-8").strip() == "lost-reply"
            ),
            "The deliberately unobserved success was not actually handed off",
        )
        # Deliberately do not call getresponse(): the sender never observes
        # the completed application reply, despite the confirmed handoff.
    finally:
        connection.close()


def _kill_gateway_during_handoff(
    controller: Any,
    base_url: str,
    root: Path,
    control: dict[str, Any],
    control_path: Path,
) -> None:
    """Kill the real gateway during dispatch and forbid its orphaned native launch."""

    _arm_handoff_barrier(root, control, control_path)
    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(
            _request,
            base_url,
            "/v1/plugins/notifications/notify",
            _event("gateway-died-in-flight"),
        )
        _wait(
            lambda: (root / "paused").exists(),
            "Gateway-loss request did not reach the handoff barrier",
        )
        grants = list(
            controller.manifest_path.with_suffix(".turn-artifacts").glob(
                "*/.dispatch-permission.json"
            )
        )
        _require(bool(grants), "The paused native request had no payload-free launch fence")
        grant = max(grants, key=lambda path: path.stat().st_mtime_ns)
        shim_pid = int((root / "paused.pid").read_text(encoding="utf-8"))
        current = json.loads(
            (controller.gateway_root / "run/current-instance.json").read_text(encoding="utf-8")
        )
        os.kill(current["pid"], signal.SIGKILL)
        (root / "released").touch()
        try:
            pending.result(timeout=10)
        except (OSError, http.client.HTTPException):
            pass
        else:
            raise QualificationError("Gateway process death did not fail the sender connection")
    _wait(
        lambda: (grant.parent / "exitcode").exists() or not _process_alive(shim_pid),
        "Orphaned bridge or pre-launch fixture process did not stop",
    )
    time.sleep(0.4)
    _require(
        int((root / "invocations").read_text(encoding="utf-8")) == 4,
        "A dead gateway's request launched after connection loss",
    )
    control["pause_handoff"] = False
    control_path.write_text(json.dumps(control), encoding="utf-8")


def _seed_brain(root: Path, executable: Path) -> Path:
    """Seed a minimal supported brain for the installed deterministic CLI."""

    import yaml

    home = root / "home"
    home.mkdir(parents=True)
    # This noncredential marker satisfies launch readiness for the selected
    # synthetic executable. It is generated externally and is never a login.
    (home / "auth.json").write_text('{"qualification_stub":true}\n', encoding="utf-8")
    role = root / "agent-def/roles/qualification/system-prompt.md"
    role.parent.mkdir(parents=True)
    role.write_text("Synthetic qualification role.\n", encoding="utf-8")
    variables = root / "selected-empty.env"
    variables.write_text("", encoding="utf-8")
    adapter = root / "synthetic-adapter.yaml"
    contract = {
        "adapter_defaults": {"args": [], "tool_params": {}},
        "requested_overrides": {"preset": None, "direct": None},
        "tool_metadata": {"tool_params": {}},
        "construction_provenance": {
            "adapter_path": str(adapter),
            "preset_path": None,
            "preset_overrides_present": False,
            "direct_overrides_present": False,
        },
    }
    manifest = {
        "schema_version": 3,
        "inputs": {
            "tool": "codex",
            "skills": [],
            "setup": "default",
            "auth": "default",
            "adapter_path": str(adapter),
            "preset_path": None,
        },
        "launch_policy": {"operator_prompt_mode": "unattended"},
        "runtime": {
            "runtime_root": str(root / "runtime"),
            "home_id": "fixture-home",
            "home_path": str(home),
            "launch_helper": str(home / "launch.sh"),
            "launch_executable": str(executable),
            "launch_home_selector": {"env_var": "CODEX_HOME", "value": str(home)},
            "launch_contract": contract,
            "cao_parsing_mode": "shadow_only",
        },
        "credentials": {
            "auth_path": str(root / "unused-auth"),
            "projected_files": [],
            "env_contract": {"source_file": str(variables), "allowlisted_env_vars": []},
        },
    }
    path = root / "brain.yaml"
    path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    return path


def _configuration(account: str) -> Any:
    """Select healthy and adversarial implementations without ambient discovery."""

    from houmao.gateway.plugins import GatewayPluginConfiguration

    plugins: dict[str, Any] = {
        "notifications": {
            "implementation": "example-notifications",
            "config": {"account": account},
        },
    }
    for instance, implementation in {
        "conflicting": "fixture-conflicting",
        "startup": "fixture-startup-failure",
        "worker": "fixture-worker-failure",
        "unsupported": "fixture-unsupported-sdk",
        "reserved": "fixture-reserved-route",
        "duplicate": "fixture-duplicate",
        "missing": "fixture-does-not-exist",
        "import-failure": "fixture-import-failure",
    }.items():
        plugins[instance] = {"implementation": implementation}
    return GatewayPluginConfiguration.model_validate(
        {"plugins": plugins, "dispatch_timeout_seconds": 3.0}
    )


def _installed_run(source_root: Path, work_root: Path) -> dict[str, object]:
    """Exercise installed product gateways with deterministic native execution."""

    import houmao
    import houmao_example_plugin
    import houmao_gateway_fixtures
    from houmao.agents.realm_controller.runtime import start_runtime_session

    for module in (houmao, houmao_example_plugin, houmao_gateway_fixtures):
        origin = Path(module.__file__ or "").resolve()
        _require(
            origin.is_relative_to(work_root / "venv"),
            "An installed module escaped the fresh environment",
        )
        _require(
            not origin.is_relative_to(source_root),
            "A qualification module imported from the checkout",
        )
    stdlib = Path(sysconfig.get_path("stdlib")).resolve()
    stdlib_zip = (
        Path(sys.base_prefix)
        / "lib"
        / f"python{sys.version_info.major}{sys.version_info.minor}.zip"
    )
    for value in sys.path:
        if not value:
            continue
        entry = Path(value).resolve()
        if entry.is_relative_to(source_root):
            _require(
                entry in {stdlib, stdlib / "lib-dynload", stdlib_zip.resolve()},
                "The installed import search path contains checkout sources or site-packages",
            )
    results: list[dict[str, object]] = []
    owners: list[dict[str, Any]] = []
    for mode in ("detached_process", "tmux_auxiliary_window"):
        root = work_root / mode
        root.mkdir()
        control_path = root / "control.json"
        control = {
            "count_file": str(root / "invocations"),
            "turn_seconds": 1.0,
            "paused_file": str(root / "paused"),
            "release_file": str(root / "released"),
        }
        control_path.write_text(json.dumps(control), encoding="utf-8")
        os.environ["HOUMAO_PLUGIN_FIXTURE_CONTROL"] = str(control_path)
        brain = _seed_brain(root, work_root / "venv/bin/houmao-fixture-codex")
        controller = start_runtime_session(
            agent_def_dir=root / "agent-def",
            brain_manifest_path=brain,
            role_name="qualification",
            runtime_root=root / "runtime",
            backend="codex_headless",
            working_directory=root,
            agent_name="plugin-qualification-" + uuid.uuid4().hex[:10],
        )
        try:
            attach = controller.attach_gateway(
                host_override="127.0.0.1",
                port_override=0,
                execution_mode_override=mode,
                plugin_config=_configuration("shared-fixture-account"),
            )
            _require(attach.status == "ok", "Normal gateway attach failed")
            status = controller.gateway_status()
            base_url = f"http://{status.gateway_host}:{status.gateway_port}"
            _bind_self(base_url, controller)
            _wait(
                lambda: (
                    _request(base_url, "/v1/plugins/notifications/_status")[1].get("lifecycle")
                    == "running"
                ),
                "Healthy external plugin did not activate",
            )
            http_status, owner = _request(base_url, "/v1/plugins/notifications/owner")
            _require(http_status == 200, "Owner-bound example route failed")
            owners.append(owner)
            _require(
                owner["account"] == "shared-fixture-account",
                "An instance selected another service account",
            )
            _verify_plugin_access(
                base_url,
                root=root,
                private_paths=("/v1/plugins/notifications/owner",),
                admin_path="/v1/plugins/notifications/refresh-credentials",
                admin_payload={},
            )
            _run(
                [
                    str(work_root / "venv/bin/houmao-mgr"),
                    "agents",
                    "single",
                    "--agent-id",
                    owner["agent_id"],
                    "gateway",
                    "status",
                ],
                cwd=root,
                env=os.environ.copy(),
                log=work_root / "operations.log",
            )
            _, plugin_status = _request(base_url, "/v1/plugins")
            _require(
                "PRIVATE_FIXTURE_EXCEPTION_MUST_NOT_LEAK" not in json.dumps(plugin_status),
                "Host status leaked an implementation exception",
            )
            statuses = {item["instance_id"]: item for item in plugin_status["plugins"]}
            _wait(
                lambda: (
                    _request(base_url, "/v1/plugins/worker/_status")[1].get("lifecycle") == "failed"
                ),
                "Worker failure did not revoke its instance",
            )
            _require(
                _request(base_url, "/v1/plugins/worker/ping")[0] == 503,
                "A failed worker retained its custom route",
            )
            for instance in (
                "conflicting",
                "startup",
                "unsupported",
                "reserved",
                "duplicate",
                "missing",
                "import-failure",
            ):
                _require(
                    statuses[instance]["lifecycle"] == "failed",
                    "An adversarial instance escaped failure isolation",
                )
                _require(
                    _request(base_url, f"/v1/plugins/{instance}/ping")[0] == 503,
                    "A failed instance custom route was not guarded",
                )
            _require(
                _request(base_url, "/health")[0] == 200, "Core health failed with a broken plugin"
            )
            _require(
                not (work_root / "unselected-imported").exists(),
                "Discovery imported an unselected implementation",
            )
            _require(
                _request(
                    base_url,
                    "/v1/plugins/notifications/notify",
                    {**_event("invalid"), "agent_id": "another-owner"},
                )[0]
                == 422,
                "Event input accepted an owner override",
            )
            _require(
                _request(base_url, "/v1/plugins/notifications/refresh-credentials", {})
                == (200, {"refreshed": False}),
                "No-auth credential refresh attempted selected authentication",
            )
            first = _request(base_url, "/v1/plugins/notifications/notify", _event("first"))
            _require(
                first[0] == 200 and first[1].get("disposition") == "dispatched",
                "Actual client handoff was not confirmed",
            )
            busy = _request(base_url, "/v1/plugins/notifications/notify", _event("sender-retained"))
            _require(busy[0] == 409, "Busy body did not return an immediate readiness error")
            count_file = root / "invocations"
            _wait(
                lambda: count_file.exists(), "The deterministic provider executable was not invoked"
            )
            _wait(
                lambda: (
                    _request(base_url, "/v1/control/headless/state")[1].get("can_accept_prompt_now")
                    is True
                ),
                "Headless work did not finish",
                seconds=15,
            )
            count = int(count_file.read_text(encoding="utf-8"))
            time.sleep(0.4)
            _require(
                int(count_file.read_text(encoding="utf-8")) == count == 1,
                "A failed event was cached and resent",
            )
            retry = _request(
                base_url, "/v1/plugins/notifications/notify", _event("sender-retained")
            )
            _require(retry[0] == 200, "A fresh sender retry did not succeed")
            _wait(
                lambda: int(count_file.read_text(encoding="utf-8")) == 2,
                "Sender retry did not launch a new client",
            )
            _wait(
                lambda: (
                    _request(base_url, "/v1/control/headless/state")[1].get("can_accept_prompt_now")
                    is True
                ),
                "Sender retry did not complete",
            )
            cursor = (
                controller.gateway_root
                / "plugins/notifications/bindings"
                / owner["binding_id"]
                / "last-dispatched-id.txt"
            )
            _require(
                cursor.read_text(encoding="utf-8").strip() == "sender-retained",
                "A successful source cursor was not persisted",
            )
            detached = controller.detach_gateway()
            _require(detached.status == "ok", "Normal gateway-only detach failed")
            base_url = _attach_running(controller)
            _, restarted_owner = _request(base_url, "/v1/plugins/notifications/owner")
            _require(restarted_owner == owner, "Gateway-only restart changed owner/account binding")
            _require(
                cursor.read_text(encoding="utf-8").strip() == "sender-retained",
                "Gateway restart lost its source cursor",
            )
            _require(
                int(count_file.read_text(encoding="utf-8")) == 2,
                "Gateway restart replayed an earlier event",
            )
            _wait(lambda: _ready(base_url), "Gateway-only restart did not preserve its ready body")
            _drop_success_reply(base_url, cursor, count_file)
            _wait(lambda: _ready(base_url), "The unobserved successful turn did not finish")
            duplicate = _request(base_url, "/v1/plugins/notifications/notify", _event("lost-reply"))
            _require(duplicate[0] == 200, "Sender could not retry after discarding a success reply")
            _wait(
                lambda: int(count_file.read_text(encoding="utf-8")) == 4,
                "A lost-reply sender retry did not demonstrate possible duplicate dispatch",
            )
            _wait(lambda: _ready(base_url), "Lost-reply sender retry did not complete")
            _kill_gateway_during_handoff(controller, base_url, root, control, control_path)
            base_url = _attach_running(controller)
            _wait(
                lambda: _ready(base_url), "A killed gateway did not recover normal body admission"
            )
            _require(
                int(count_file.read_text(encoding="utf-8")) == 4,
                "A restarted gateway cached and resent its interrupted request",
            )
            _require(
                cursor.read_text(encoding="utf-8").strip() == "lost-reply",
                "Gateway death advanced an unconfirmed source cursor",
            )
            recovered = _request(
                base_url, "/v1/plugins/notifications/notify", _event("gateway-died-in-flight")
            )
            _require(recovered[0] == 200, "Fresh sender retry after gateway recovery failed")
            _wait(
                lambda: int(count_file.read_text(encoding="utf-8")) == 5,
                "Recovered gateway did not execute a fresh sender request",
            )
            _wait(lambda: _ready(base_url), "Recovered gateway sender retry did not complete")
            # Pause the real execution CLI boundary before native Popen. Changing
            # the existing manifest generation simulates replacement of the body.
            _arm_handoff_barrier(root, control, control_path)
            with ThreadPoolExecutor(max_workers=1) as executor:
                pending = executor.submit(
                    _request,
                    base_url,
                    "/v1/plugins/notifications/notify",
                    _event("replaced-in-flight"),
                )
                _wait(
                    lambda: (root / "paused").exists(),
                    "Native execution did not reach the controlled handoff barrier",
                )
                manifest_path = controller.manifest_path
                original = manifest_path.read_text(encoding="utf-8")
                try:
                    if mode == "detached_process":
                        manifest = json.loads(original)
                        manifest["registry_generation_id"] = uuid.uuid4().hex
                        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    else:
                        subprocess.run(
                            _tmux_command("kill-window", "-t", f"{controller.tmux_session_name}:0"),
                            check=True,
                            capture_output=True,
                            text=True,
                        )
                    (root / "released").touch()
                    lost = pending.result(timeout=10)
                finally:
                    if mode == "detached_process":
                        manifest_path.write_text(original, encoding="utf-8")
            _require(lost[0] == 503, "Replacement during handoff did not fail the original request")
            time.sleep(0.4)
            _require(
                int(count_file.read_text(encoding="utf-8")) == 5,
                "An expired request reached a replacement body",
            )
            results.append(
                {
                    "execution_mode": mode,
                    "result": "passed",
                    "healthy_route": True,
                    "operator_access": True,
                    "open_and_key_required_controls": True,
                    "verified_private_callers": True,
                    "cursor_continuity": True,
                    "gateway_process_loss": True,
                    "gateway_restart_no_replay": True,
                    "lost_reply_duplicate": True,
                    "isolated_failures": True,
                    "busy_error": 409,
                    "in_flight_error": 503,
                    "body_change": "generation_replaced"
                    if mode == "detached_process"
                    else "body_window_died",
                    "sender_retry": True,
                    "no_replay": True,
                    "native_client_invocations": 5,
                }
            )
        finally:
            stopped = controller.stop(force_cleanup=True)
            _require(stopped.status == "ok", "Qualification could not stop its runtime session")
            remaining = subprocess.run(
                _tmux_command("has-session", "-t", str(controller.tmux_session_name)),
                capture_output=True,
                text=True,
                check=False,
            )
            _require(
                remaining.returncode != 0, "Qualification left its synthetic tmux session running"
            )
    _require(
        owners[0]["agent_id"] != owners[1]["agent_id"],
        "Owner fixtures did not create distinct logical owners",
    )
    _require(
        owners[0]["binding_id"] != owners[1]["binding_id"],
        "Independent owners/accounts reused a state binding",
    )
    report: dict[str, object] = {
        "action": "run",
        "result": "passed",
        "python_version": sys.version.split()[0],
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "fresh_environment": True,
        "isolated_tmux_server": True,
        "checkout_imports": False,
        "checkout_source_search_paths": False,
        "offline_install": True,
        "versions": {
            name: importlib.metadata.version(name)
            for name in (
                "Houmao",
                "houmao-example-notifications",
                "houmao-gateway-qualification-fixtures",
                "houmao-gateway-duplicate-fixture",
            )
        },
        "modes": results,
        "owner_isolation": True,
        "selected_only_imports": True,
        "provider_network_calls": 0,
        "cleanup": "completed",
    }
    (work_root / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    """Expose separate online preparation and offline qualification actions."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "installed-run"))
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    source_root = (args.source_root or Path(__file__).resolve().parents[3]).resolve()
    try:
        if args.action == "installed-run":
            if args.work_root is None:
                raise QualificationError("An installed run requires an explicit external work root")
            report = _installed_run(source_root, args.work_root.resolve())
        else:
            if args.wheelhouse is None:
                raise QualificationError("Setup requires an explicitly pre-provisioned wheelhouse")
            wheelhouse = _external_root(args.wheelhouse, source_root)
            if args.action == "prepare":
                report = _prepare(source_root, wheelhouse)
            else:
                if args.work_root is None:
                    raise QualificationError("Setup requires an explicit fresh external work root")
                report = _qualify(
                    source_root, wheelhouse, _external_root(args.work_root, source_root)
                )
    except (QualificationError, OSError, ValueError) as exc:
        print(json.dumps({"result": "failed", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
