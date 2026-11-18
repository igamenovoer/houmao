"""Shared isolation, tmux observation, and Houmao CLI helpers for the 3.0 review campaign."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_access_runtime import load_gateway_admin_seed
from houmao.gateway.access import (
    GatewayAdminKey,
    GatewayClientBinding,
    load_gateway_signer,
)
from houmao.gateway.client import GatewayClient

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUN_ROOT = REPO_ROOT / "tmp/houmao-30-iter1"
DEFAULT_ACCESS_ROOT = Path.home() / ".local/state/houmao-30-iter1"
DEFAULT_TMUX_SERVER = "houmao-30-iter1"

_PROVIDER_PREFIXES = (
    "ANTHROPIC_",
    "CLAUDE_CODE_",
    "OPENAI_",
    "KIMI_",
    "DEEPSEEK_",
    "QWEN_",
    "DSH_",
)
_CLEAR_ENV_VARS = (
    "TMUX",
    "TMUX_PANE",
    "TMUX_TMPDIR",
)


@dataclass(frozen=True)
class CommandResult:
    """Captured subprocess execution outcome for diagnostic command logging."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    def parse_json_stdout(self) -> Any | None:
        """Parse JSON stdout when a `--print-json` Houmao command emits structured output."""

        text = self.stdout.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError:
            return None


def private_mkdir(path: Path) -> Path:
    """Create a directory restricted to the current user (`0700`)."""

    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)
    return path


def private_write_text(path: Path, content: str, *, mode: int = 0o600) -> Path:
    """Write a private file under `0700` parent directories with strict permissions."""

    private_mkdir(path.parent)
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)
    return path


def resolve_real_tmux(*, exclude_bin: Path | None = None) -> Path:
    """Locate the system `tmux` binary outside any campaign shim directory."""

    excluded = {(DEFAULT_RUN_ROOT / "bin").resolve()}
    if exclude_bin is not None:
        excluded.add(exclude_bin.resolve())
    search_parts = [
        entry
        for entry in os.environ.get("PATH", os.defpath).split(os.pathsep)
        if entry and Path(entry).resolve() not in excluded
    ]
    resolved = shutil.which("tmux", path=os.pathsep.join(search_parts))
    if resolved is None:
        raise FileNotFoundError("Unable to locate `tmux` executable on PATH")
    return Path(resolved).resolve()


def resolve_houmao_mgr() -> str:
    """Locate the `houmao-mgr` console script inside the active Pixi environment."""

    candidate = Path(sys.executable).resolve().parent / "houmao-mgr"
    if candidate.is_file():
        return str(candidate)
    resolved = shutil.which("houmao-mgr")
    if resolved is None:
        raise FileNotFoundError("Unable to locate `houmao-mgr`; run via `pixi run python ...`")
    return resolved


def isolated_tmux_tmpdir(run_root: Path) -> Path:
    """Return the isolated `TMUX_TMPDIR` directory inside the scratch run root."""

    return private_mkdir(run_root.resolve() / "tsock")


def isolated_tmux_socket(run_root: Path) -> Path:
    """Return the exact isolated tmux socket path matching `houmao.execution.tmux`."""

    socket_dir = private_mkdir(isolated_tmux_tmpdir(run_root) / f"tmux-{os.getuid()}")
    return (socket_dir / "default").resolve()


def ensure_tmux_shim(run_root: Path) -> Path:
    """Create a `0700` tmux PATH shim binding `TMUX_TMPDIR` to the isolated socket directory."""

    shim = run_root / "bin/tmux"
    real_tmux = resolve_real_tmux(exclude_bin=shim.parent)
    tmpdir = isolated_tmux_tmpdir(run_root)
    script = (
        "#!/bin/sh\n"
        "unset TMUX TMUX_PANE\n"
        f"export TMUX_TMPDIR={shlex.quote(str(tmpdir))}\n"
        f'exec {shlex.quote(str(real_tmux))} "$@"\n'
    )
    return private_write_text(shim, script, mode=0o700)


def build_isolated_env(
    run_root: Path,
    *,
    server_name: str = DEFAULT_TMUX_SERVER,
    access_root: Path | None = None,
    project_dir: Path | None = None,
    extra_env: Mapping[str, str] | None = None,
    path_prefix: Sequence[Path] = (),
    strip_default_dsh: bool = False,
) -> dict[str, str]:
    """Construct an isolated process environment cleared of ambient tmux and provider variables."""

    del server_name
    shim = ensure_tmux_shim(run_root)
    tmpdir = isolated_tmux_tmpdir(run_root)
    state_root = private_mkdir(run_root / "houmao-state")
    registry_dir = private_mkdir(state_root / "registry")
    runtime_dir = private_mkdir(state_root / "runtime")
    mailbox_dir = private_mkdir(state_root / "mailbox")
    # Keep XDG_CONFIG_HOME outside the git checkout so gateway `_reject_checkout()` passes.
    private_access_root = private_mkdir((access_root or DEFAULT_ACCESS_ROOT).resolve())
    config_dir = private_mkdir(private_access_root / "config")

    cleaned: dict[str, str] = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith((*_PROVIDER_PREFIXES, "HOUMAO_")) and key not in _CLEAR_ENV_VARS
    }
    cleaned["TMUX_TMPDIR"] = str(tmpdir)
    cleaned["HOUMAO_GLOBAL_REGISTRY_DIR"] = str(registry_dir)
    cleaned["HOUMAO_GLOBAL_RUNTIME_DIR"] = str(runtime_dir)
    cleaned["HOUMAO_GLOBAL_MAILBOX_DIR"] = str(mailbox_dir)
    cleaned["XDG_CONFIG_HOME"] = str(config_dir)
    if project_dir is not None:
        cleaned["HOUMAO_PROJECT_OVERLAY_DIR"] = str(project_dir / ".houmao")
    if extra_env:
        cleaned.update(extra_env)

    original_path = cleaned.get("PATH", os.defpath).split(os.pathsep)
    if strip_default_dsh:
        dsh_path = shutil.which("dsh", path=os.pathsep.join(original_path))
        if dsh_path is not None:
            dsh_parent = str(Path(dsh_path).resolve().parent)
            original_path = [entry for entry in original_path if entry != dsh_parent]

    prefix_parts = [str(item) for item in path_prefix] + [str(shim.parent)]
    cleaned["PATH"] = os.pathsep.join([*prefix_parts, *original_path])
    return cleaned


def _default_tmux_socket() -> Path:
    """Return the user's shared system tmux default socket path (never to be killed)."""

    return Path(f"/tmp/tmux-{os.getuid()}/default").resolve()


def run_real_tmux(
    args: Sequence[str],
    *,
    socket_path: Path | None = None,
) -> CommandResult:
    """Invoke `tmux` directly with inherited `TMUX`/`TMUX_PANE`/`TMUX_TMPDIR` cleared."""

    real_tmux = str(resolve_real_tmux())
    cmd = [real_tmux]
    if socket_path is not None:
        resolved_socket = socket_path.resolve()
        if resolved_socket == _default_tmux_socket():
            raise ValueError("Refusing to target system default tmux socket as isolated")
        cmd.extend(["-S", str(resolved_socket)])
    elif args and args[0] == "kill-server":
        raise ValueError("Refusing to invoke `kill-server` on the default tmux server")

    cmd.extend(args)
    env = {key: value for key, value in os.environ.items() if key not in _CLEAR_ENV_VARS}
    completed = subprocess.run(
        cmd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=15.0,
    )
    return CommandResult(
        argv=tuple(cmd),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def list_tmux_sessions(*, socket_path: Path | None = None) -> list[str]:
    """List session names on either the default server or an explicit isolated socket."""

    res = run_real_tmux(["list-sessions", "-F", "#{session_name}"], socket_path=socket_path)
    if res.returncode != 0:
        return []
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def capture_tmux_pane(socket_path: Path, session_name: str, *, lines: int = 40) -> str:
    """Read the last `lines` lines from an isolated tmux session pane."""

    res = run_real_tmux(
        ["capture-pane", "-p", "-t", session_name, "-S", f"-{max(1, lines)}"],
        socket_path=socket_path,
    )
    if res.returncode != 0:
        return f"<capture-pane failed rc={res.returncode}: {res.stderr.strip()}>"
    return res.stdout


def kill_isolated_tmux_server(socket_path: Path) -> CommandResult:
    """Shut down only the isolated `-S <socket_path>` tmux server."""

    resolved_socket = socket_path.resolve()
    if resolved_socket == _default_tmux_socket():
        raise ValueError("Refusing to stop the default tmux server")
    return run_real_tmux(["kill-server"], socket_path=resolved_socket)


def run_houmao_mgr(
    args: Sequence[str],
    *,
    env: Mapping[str, str],
    cwd: Path | None = None,
    input_text: str | None = None,
    print_json: bool = False,
    timeout: float = 180.0,
) -> CommandResult:
    """Execute `houmao-mgr` in the isolated campaign environment without leaking secrets."""

    mgr = resolve_houmao_mgr()
    cmd = [mgr]
    if print_json:
        cmd.append("--print-json")
    cmd.extend(args)
    completed = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd is not None else None,
        env=dict(env),
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    return CommandResult(
        argv=tuple(cmd),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse `KEY=VALUE` entries from a dotenv file in memory without logging values."""

    parsed: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, value = line.split("=", 1)
        cleaned_key = key.strip()
        cleaned_val = value.strip()
        if (
            len(cleaned_val) >= 2
            and cleaned_val[0] == cleaned_val[-1]
            and cleaned_val[0] in {"'", '"'}
        ):
            cleaned_val = cleaned_val[1:-1]
        if cleaned_key:
            parsed[cleaned_key] = cleaned_val
    return parsed


def http_json(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 10.0,
) -> tuple[int, dict[str, Any] | str]:
    """Perform a simple GET request and return `(status_code, decoded_json_or_text)`."""

    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        raise ValueError("Only plain http/https URLs without embedded credentials are permitted")
    req = Request(url, headers=dict(headers or {}), method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except ValueError:
                return resp.status, raw
    except HTTPError as err:
        raw = err.read().decode("utf-8", errors="replace")
        try:
            return err.code, json.loads(raw)
        except ValueError:
            return err.code, raw
    except (URLError, TimeoutError, OSError) as err:
        return 0, f"{type(err).__name__}: {err}"


def probe_openai_models(
    base_url: str,
    *,
    api_key: str | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Query `<base_url>/models` to inspect endpoint reachability and served model IDs."""

    normalized = base_url.rstrip("/")
    if not normalized.endswith("/v1"):
        models_url = f"{normalized}/v1/models"
    else:
        models_url = f"{normalized}/models"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    status, body = http_json(models_url, headers=headers, timeout=timeout)
    model_ids: list[str] = []
    if status == 200 and isinstance(body, dict):
        data = body.get("data")
        if isinstance(data, list):
            model_ids = [
                str(item["id"])
                for item in data
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            ]
    return {
        "url": models_url,
        "reachable": status == 200,
        "http_status": status,
        "model_ids": model_ids,
        "error": None if status == 200 else str(body)[:240],
    }


def generate_admin_keyset(
    keys_dir: Path,
    principals: Sequence[str] = ("iter1-operator-admin", "iter1-reviewer-admin"),
) -> dict[str, Any]:
    """Generate Ed25519 keypairs and a validated `gateway-admin-seed.json` outside the checkout."""

    ssh_keygen = shutil.which("ssh-keygen") or "/usr/bin/ssh-keygen"
    if not Path(ssh_keygen).is_file():
        raise FileNotFoundError("Unable to locate `ssh-keygen` executable")
    if not principals:
        raise ValueError("At least one admin key principal is required")

    target_dir = private_mkdir(keys_dir.resolve())
    generated: list[dict[str, str]] = []
    seed_entries: list[dict[str, str]] = []

    for principal in principals:
        priv_path = target_dir / f"{principal}_ed25519"
        pub_path = Path(f"{priv_path}.pub")
        priv_path.unlink(missing_ok=True)
        pub_path.unlink(missing_ok=True)
        proc = subprocess.run(
            [ssh_keygen, "-q", "-t", "ed25519", "-N", "", "-C", principal, "-f", str(priv_path)],
            text=True,
            capture_output=True,
            check=False,
            timeout=15.0,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ssh-keygen failed for {principal}: {proc.stderr.strip()}")
        priv_path.chmod(0o600)
        pub_path.chmod(0o600)

        raw_pub = pub_path.read_text(encoding="utf-8").strip()
        validated_key = GatewayAdminKey(principal=principal, public_key=raw_pub)
        load_gateway_signer(priv_path)
        seed_entries.append({"principal": principal, "public_key": validated_key.public_key})
        generated.append(
            {
                "principal": principal,
                "key_id": validated_key.key_id,
                "private_key_path": str(priv_path),
                "public_key_path": str(pub_path),
                "public_key": validated_key.public_key,
            }
        )

    seed_path = target_dir / "gateway-admin-seed.json"
    private_write_text(
        seed_path,
        json.dumps({"admin_keys": seed_entries}, indent=2) + "\n",
        mode=0o600,
    )
    validated_seed = load_gateway_admin_seed(seed_path)
    return {
        "keys_dir": str(target_dir),
        "seed_path": str(seed_path),
        "enrolled_count": len(validated_seed.admin_keys),
        "keys": generated,
    }


def admin_gateway_probe(
    base_url: str,
    *,
    admin_private_key_path: Path | None = None,
) -> dict[str, Any]:
    """Inspect public endpoint metadata, unsigned `/v1/usage`, and signed admin gateway access."""

    unauth_usage_code, unauth_usage_body = http_json(f"{base_url.rstrip('/')}/v1/usage")
    public_client = GatewayClient(base_url=base_url)
    try:
        descriptor = public_client.describe_endpoint()
        endpoint_info: dict[str, Any] = descriptor.model_dump(mode="json")
    except (GatewayHttpError, ValueError, OSError) as exc:
        return {
            "endpoint_error": str(exc),
            "unsigned_usage": {"http_status": unauth_usage_code, "body": unauth_usage_body},
        }

    result: dict[str, Any] = {
        "endpoint": endpoint_info,
        "unsigned_usage": {"http_status": unauth_usage_code, "body": unauth_usage_body},
    }
    if admin_private_key_path is not None and admin_private_key_path.is_file():
        binding = GatewayClientBinding(
            base_url=base_url,
            owner=descriptor.target.owner,
            purpose="admin",
            private_key_path=str(admin_private_key_path),
        )
        admin_client = GatewayClient(base_url=base_url, binding=binding)
        try:
            result["admin_status"] = admin_client.status().model_dump(mode="json")
        except (GatewayHttpError, ValueError, OSError) as exc:
            result["admin_status_error"] = str(exc)
        try:
            result["admin_usage"] = admin_client.get_usage().model_dump(mode="json")
        except (GatewayHttpError, ValueError, OSError) as exc:
            result["admin_usage_error"] = str(exc)
    return result
