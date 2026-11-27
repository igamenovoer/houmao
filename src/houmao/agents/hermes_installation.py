"""Select and observe the execution owner's prepared stock Hermes installation."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shlex
import socket
import stat
import subprocess
from time import monotonic

from pydantic import BaseModel, ConfigDict, ValidationError

from houmao.execution.context import current_execution_binding, current_execution_deadline
from houmao.execution.models import ExecutionBindingV1, validate_absolute_path


HERMES_INSTALLATION_ROOT_ENV = "HOUMAO_HERMES_INSTALLATION_ROOT"
HERMES_EXECUTABLE_ENV = "HOUMAO_HERMES_EXECUTABLE"
QUALIFIED_HERMES_BUILD = "8fc0374447313e276f6b9a2764bfc750190c966a"
_GATEWAY_LOCK_DIR = "gateway-locks"
_BUILD_LABEL = "v0.23.4"
_CHECK_TIMEOUT = 15.0

# The ordinary launcher may recover interrupted checkout updates, and PM's public
# client may create locks and leases even for a currency query. Run the matching
# read-only implementation directly in PM's already provisioned interpreter.
_NATIVE_PROBE = """
import json
import os
import sys
from pathlib import Path

source = Path(sys.argv[1])
store_python = Path(sys.argv[2])
sys.path.insert(0, str(source))

from hermes_cli._early_recovery import interrupted_pull_marker
from hermes_cli.update_lock import MARKER_NAME
from hermes_cli.venv_sync import completion_pending_path
from pm.environments import committed_venv, install_state_dir, runtime_facts_path, site_packages
from pm.install import installed_package, venv_is_current
from pm.runtime import _inputs

if any(path.exists() for path in (
        interrupted_pull_marker(source), completion_pending_path(source),
        install_state_dir(source) / 'publication.json',
        Path(os.environ['HERMES_HOME']) / MARKER_NAME,
)):
    raise SystemExit('maintenance')

if not (Path(sys.prefix) / 'pm-runtime.json').is_file():
    raise SystemExit('pm-runtime')
runtime = json.loads((Path(sys.prefix) / 'pm-runtime.json').read_text())
if runtime.get('inputs') != _inputs(source / 'pm', store_python):
    raise SystemExit('pm-runtime')

app = committed_venv(source)
if app is None or not venv_is_current(extras=['all'], project_root=source):
    raise SystemExit('dependencies')
facts = json.loads(runtime_facts_path(source).read_text())['packages']['venv']
tui = source / 'ui-tui'
node = installed_package('node')
from hermes_cli.source_build import source_product_current
if node is None or node.binary is None or not source_product_current(source, 'tui', tui / 'dist'):
    raise SystemExit('tui')

# Load the real app imports without entering its native startup or lease path.
sys.path.insert(1, str(site_packages(app)))
import websockets
from acp_adapter.gateway_server import GatewayACPAgent
from gateway.control_resolve import RESOLVE_PROTOCOL, resolve_profile
from gateway.control_socket import CONTROL_PROTOCOL_VERSION
from gateway.session_context import bound_session_env
from hermes_cli.gateway_chat import run_gateway_chat
from hermes_cli.gateway_runtime import discover_gateway_endpoint
from hermes_cli.plugins_context import PluginContext
from hermes_cli.version_info import get_version_info, installed_commit_sha
from hermes_constants import get_hermes_home_override

if (CONTROL_PROTOCOL_VERSION != 1 or RESOLVE_PROTOCOL != 1
        or not all(callable(capability) for capability in (
            bound_session_env, discover_gateway_endpoint, get_hermes_home_override,
            GatewayACPAgent, PluginContext.register_session_env, resolve_profile, run_gateway_chat,
        ))):
    raise SystemExit('capabilities')

print(json.dumps({'build': installed_commit_sha(), 'version': get_version_info().base_version,
                  'dependency_environment': str(app), 'dependency_stamp': facts['stamp'],
                  'node': str(node.binary)}))
"""


class PreparedHermesInstallationError(ValueError):
    """Report owner-side Hermes preparation required before worker mutation."""


class _NativeEvidence(BaseModel):
    """Accept only the non-secret fields emitted by the pinned stock probe."""

    model_config = ConfigDict(extra="forbid", strict=True)

    build: str
    version: str
    dependency_environment: str
    dependency_stamp: str
    node: str


@dataclass(frozen=True)
class PreparedHermesEvidence:
    """Identify the observed build and selected native dependency generation."""

    build: str
    version: str
    dependency_environment: Path
    dependency_stamp: str


@dataclass(frozen=True)
class PreparedHermesInstallation:
    """Record one qualified Hermes installation and its private gateway rendezvous."""

    root: Path
    executable: str
    lock_dir: Path
    evidence: PreparedHermesEvidence
    node: Path

    def native_environment(self, home: Path) -> dict[str, str]:
        """Select the stock owner or direct named profile with prepared dependencies."""

        if home.resolve() != home or (home != self.root and home.parent != self.root / "profiles"):
            raise ValueError("Hermes home must be the owner root or a canonical named profile")
        return {
            "HERMES_HOME": str(home),
            "HERMES_GATEWAY_LOCK_DIR": str(self.lock_dir),
            "HERMES_RUNTIME_DIR": str(self.root / "tools"),
            "HERMES_DISABLE_LAZY_INSTALLS": "1",
            "HERMES_NODE": str(self.node),
            "HERMES_TUI_DIR": str(self.root / "hermes-agent" / "ui-tui"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }


def _owner_directory(path: Path, uid: int, *, private: bool = False) -> Path:
    """Require a real target-side directory controlled by the expected OS owner."""

    if path.resolve(strict=True) != path:
        raise ValueError(f"{path.name} must use its canonical non-symlink path")
    metadata = path.stat()
    forbidden = 0o077 if private else 0o022
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != uid or metadata.st_mode & forbidden:
        raise ValueError(f"{path.name} must be an owner-controlled directory")
    return path


def _launcher_interpreter(executable: Path, source: Path, uid: int) -> Path:
    """Check the stock source launcher without executing any startup recovery."""

    metadata = executable.stat()
    if (
        executable.resolve(strict=True) != executable
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != uid
        or metadata.st_mode & 0o022
        or not os.access(executable, os.X_OK)
    ):
        raise ValueError("stock Hermes launcher must be an owner-controlled executable file")
    with executable.open(encoding="utf-8") as stream:
        contents = stream.read(16_385)
    if len(contents) > 16_384:
        raise ValueError("stock Hermes launcher is not in the qualified source format")
    command = shlex.split(contents, comments=True)
    if (
        len(command) != 6
        or command[0] != "exec"
        or command[2:4] != ["-I", "-c"]
        or command[5] != "$@"
    ):
        raise ValueError("stock Hermes launcher is not in the qualified source format")
    launcher_code = ast.parse(command[4])
    expected = ast.parse(f"sys.path.insert(0, {str(source)!r})").body[0]
    if not any(ast.dump(node) == ast.dump(expected) for node in launcher_code.body):
        raise ValueError("stock Hermes launcher is bound to a different source checkout")
    python = Path(validate_absolute_path(command[1]))
    if (
        not python.is_relative_to(source.parent / "tools")
        or not python.resolve(strict=True).is_relative_to(source.parent / "tools")
        or not os.access(python, os.X_OK)
    ):
        raise ValueError("stock Hermes launcher does not use the owner's prepared Python tool")
    return python


def _observe_native_evidence(root: Path, source: Path, python: Path) -> _NativeEvidence:
    """Run bounded Git and stock runtime observations with a private environment."""

    key = hashlib.sha256(str(source).encode()).hexdigest()[:16]
    pm_runtime = root / "installs" / key / "pm-runtime"
    selection_path = pm_runtime / "selected.json"
    if not selection_path.is_file():
        raise ValueError("Hermes PM runtime is not prepared")
    if selection_path.resolve(strict=True) != selection_path:
        raise ValueError("Hermes PM runtime selection is outside the prepared install")
    selection = json.loads(selection_path.read_bytes())
    generation = Path(selection["generation"])
    if generation.parts[:1] != ("generations",) or len(generation.parts) != 2:
        raise ValueError("Hermes PM selection is outside the prepared install")
    pm_python = pm_runtime / generation / "bin" / "python"
    if (
        pm_python.parent.resolve(strict=True) != pm_python.parent
        or not pm_python.resolve(strict=True).is_relative_to(root / "tools")
        or not os.access(pm_python, os.X_OK)
    ):
        raise ValueError("Hermes PM does not use an owner-prepared interpreter")
    bound = current_execution_deadline()
    deadline = monotonic() + _CHECK_TIMEOUT
    if bound is not None:
        deadline = min(deadline, bound)
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(root),
        "LANG": "C.UTF-8",
        "HERMES_HOME": str(root),
        "HERMES_RUNTIME_DIR": str(root / "tools"),
        "HERMES_DISABLE_LAZY_INSTALLS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_LAZY_FETCH": "1",
    }

    def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
        """Keep probe commands inside the operation's read-only budget."""

        remaining = deadline - monotonic()
        if remaining <= 0:
            raise ValueError("prepared Hermes verification exceeded the execution deadline")
        return subprocess.run(
            argv,
            cwd=source,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=remaining,
        )

    checkout = run(["git", "--no-replace-objects", "rev-parse", "HEAD"])
    if checkout.returncode or checkout.stdout.strip() != QUALIFIED_HERMES_BUILD:
        raise ValueError("Hermes source checkout has a different build")
    changes = run(["git", "-c", "core.fsmonitor=false", "status", "--porcelain", "-uno"])
    if changes.returncode or changes.stdout:
        raise ValueError("Hermes source checkout has changes or cannot be verified")
    native = run([str(pm_python), "-I", "-B", "-c", _NATIVE_PROBE, str(source), str(python)])
    if native.returncode:
        diagnostic = {
            "maintenance": "Hermes has unfinished owner maintenance",
            "pm-runtime": "Hermes PM runtime is stale or not prepared",
            "dependencies": "Hermes dependency selection is stale or not prepared",
            "tui": "Hermes Node or the Ink bundle is stale or not prepared",
            "capabilities": "Hermes is missing required native profile and tool capabilities",
        }.get(native.stderr.strip(), "could not qualify the stock Hermes runtime and capabilities")
        raise ValueError(diagnostic)
    return _NativeEvidence.model_validate_json(native.stdout)


def load_prepared_hermes_installation(
    executable: str | Path | None = None,
    *,
    owner: ExecutionBindingV1 | None = None,
    expected_root: Path | None = None,
) -> PreparedHermesInstallation:
    """Observe a trusted owner selection or requalify a previously recorded binding.

    The execution helper provides the installation environment from owner policy.
    Callers must pass only saved owner evidence as ``expected_root`` and must keep
    per-launch environment and credential inputs separate from this selection.
    """

    admitted = current_execution_binding()
    owner = admitted if owner is None else owner
    uid = os.geteuid()
    context_binding = admitted or owner
    context = context_binding.context_id if context_binding is not None else f"local uid {uid}"
    try:
        if (admitted is not None and owner != admitted) or (owner is not None and owner.uid != uid):
            raise ValueError("prepared Hermes selection differs from the admitted execution owner")
        if not hasattr(socket, "SO_PEERCRED"):
            raise ValueError("Hermes worker tool attribution requires Linux Unix peer credentials")
        configured = os.environ.get(HERMES_INSTALLATION_ROOT_ENV)
        if configured is None and expected_root is None:
            raise ValueError(f"set {HERMES_INSTALLATION_ROOT_ENV} in execution-owner configuration")
        configured = str(expected_root) if configured is None else configured
        root = Path(validate_absolute_path(configured))
        if expected_root is not None and root != expected_root:
            raise ValueError("configured Hermes root differs from the recorded owner binding")
        root = _owner_directory(root, uid, private=True)
        source = _owner_directory(root / "hermes-agent", uid)
        _owner_directory(root / "tools", uid)
        lock_dir = _owner_directory(root / _GATEWAY_LOCK_DIR, uid, private=True)
        path = source / ".hermes" / "bin" / "hermes"
        for proposed in (os.environ.get(HERMES_EXECUTABLE_ENV), executable):
            if (
                proposed is not None
                and Path(validate_absolute_path(str(proposed))).resolve() != path
            ):
                raise ValueError("selected Hermes executable is outside the prepared installation")
        python = _launcher_interpreter(path, source, uid)
        native = _observe_native_evidence(root, source, python)
        if native.build != QUALIFIED_HERMES_BUILD or native.version != _BUILD_LABEL.removeprefix(
            "v"
        ):
            raise ValueError("Hermes runtime reports a different installed build")
        dependency_environment = Path(native.dependency_environment)
        node = Path(native.node)
        if (
            not dependency_environment.is_relative_to(root / "installs")
            or dependency_environment.resolve(strict=True) != dependency_environment
            or not native.dependency_stamp
            or not node.resolve(strict=True).is_relative_to(root / "tools")
            or not os.access(node, os.X_OK)
        ):
            raise ValueError("Hermes selected dependencies outside the prepared installation")
        evidence = PreparedHermesEvidence(
            build=native.build,
            version=native.version,
            dependency_environment=dependency_environment,
            dependency_stamp=native.dependency_stamp,
        )
        return PreparedHermesInstallation(root, str(path), lock_dir, evidence, node)
    except (
        OSError,
        SyntaxError,
        TypeError,
        KeyError,
        ValidationError,
        subprocess.SubprocessError,
    ) as exc:
        detail = "could not verify prepared files or run the stock read-only check"
        raise PreparedHermesInstallationError(_preparation_message(context, detail)) from exc
    except ValueError as exc:
        raise PreparedHermesInstallationError(_preparation_message(context, str(exc))) from exc


def _preparation_message(context: str, detail: str) -> str:
    """Identify the owner remedy without echoing native process output."""

    return (
        f"Hermes installation for execution context {context} needs owner preparation: {detail}. "
        f"Prepare stock Hermes {_BUILD_LABEL}, run `hermes pm install`, build Ink, and configure "
        f"{HERMES_INSTALLATION_ROOT_ENV} as described in the managed Hermes setup reference."
    )
