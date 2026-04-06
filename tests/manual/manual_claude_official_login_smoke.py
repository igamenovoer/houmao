"""Manual smoke validation for the local Claude `official-login` fixture."""

from __future__ import annotations

import argparse
import os
from json import JSONDecodeError, JSONDecoder
from pathlib import Path
import shutil
import subprocess
import tempfile


def _decode_json_stream(output: str) -> list[dict[str, object]]:
    """Decode one whitespace-separated JSON object stream."""

    decoder = JSONDecoder()
    payloads: list[dict[str, object]] = []
    index = 0
    while index < len(output):
        while index < len(output) and output[index].isspace():
            index += 1
        if index >= len(output):
            break
        payload, index = decoder.raw_decode(output, index)
        if not isinstance(payload, dict):
            raise RuntimeError("Expected a JSON object in CLI output.")
        payloads.append(payload)
    return payloads


def _run_command(*, args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run one subprocess command and raise on failure."""

    process = subprocess.run(
        args,
        cwd=str(cwd),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit={process.returncode}): {' '.join(args)}\n"
            f"stdout:\n{process.stdout}\n"
            f"stderr:\n{process.stderr}"
        )
    return process


def _default_repo_root() -> Path:
    """Return the repository root for this manual script."""

    return Path(__file__).resolve().parents[2]


def _default_agent_def_dir(repo_root: Path) -> Path:
    """Return the default fixture agent-definition root."""

    return repo_root / "tests" / "fixtures" / "agents"


def _default_source_config_dir() -> Path:
    """Return the default vendor Claude config root."""

    configured = os.environ.get("CLAUDE_CONFIG_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".claude"


def _official_login_auth_root(agent_def_dir: Path, auth_name: str) -> Path:
    """Return the local-only Claude auth bundle root."""

    return agent_def_dir / "tools" / "claude" / "auth" / auth_name


def _prepare_official_login_bundle(*, auth_root: Path, source_config_dir: Path) -> Path:
    """Provision the local-only `official-login` bundle from vendor login state."""

    credentials_path = source_config_dir / ".credentials.json"
    if not credentials_path.is_file():
        raise RuntimeError(
            f"Vendor Claude credentials not found at `{credentials_path}`. "
            "Pass `--source-config-dir` pointing at the Claude config root "
            "that contains `.credentials.json`."
        )

    files_dir = auth_root / "files"
    env_dir = auth_root / "env"
    files_dir.mkdir(parents=True, exist_ok=True)
    env_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(credentials_path, files_dir / ".credentials.json")
    (files_dir / ".claude.json").write_text("{}\n", encoding="utf-8")
    (env_dir / "vars.env").write_text("# local overrides for official-login\n", encoding="utf-8")

    for stale_name in ("credentials.json", "claude_state.template.json"):
        stale_path = files_dir / stale_name
        if stale_path.exists():
            stale_path.unlink()

    return auth_root


def _load_launch_payload(output: str) -> dict[str, object]:
    """Extract the managed-agent launch payload from CLI JSON stream output."""

    try:
        payloads = _decode_json_stream(output)
    except JSONDecodeError as exc:
        raise RuntimeError(f"Failed to decode launch output as JSON stream: {exc}") from exc
    for payload in payloads:
        if payload.get("status") == "Managed agent launch complete":
            return payload
    raise RuntimeError(f"Did not find launch-complete payload in output:\n{output}")


def _validated_env(*, agent_def_dir: Path, overlay_root: Path | None = None) -> dict[str, str]:
    """Return the sanitized environment for the smoke launch."""

    env = dict(os.environ)
    env["HOUMAO_AGENT_DEF_DIR"] = str(agent_def_dir.resolve())
    env["HOUMAO_CLI_PRINT_STYLE"] = "json"
    if overlay_root is not None:
        env["HOUMAO_PROJECT_OVERLAY_DIR"] = str(overlay_root.resolve())
    for variable in (
        "HOUMAO_GLOBAL_RUNTIME_DIR",
        "HOUMAO_GLOBAL_MAILBOX_DIR",
        "HOUMAO_LOCAL_JOBS_DIR",
        "HOUMAO_JOB_DIR",
    ):
        env.pop(variable, None)
    return env


def _run_smoke_launch(*, repo_root: Path, agent_def_dir: Path, auth_name: str) -> tuple[Path, dict[str, object]]:
    """Run the headless Claude smoke launch from a fresh temp workdir."""

    tmp_root = repo_root / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    workdir = Path(
        tempfile.mkdtemp(prefix="claude-official-login-smoke-", dir=str(tmp_root))
    ).resolve()
    overlay_root = workdir / ".houmao"
    env = _validated_env(agent_def_dir=agent_def_dir, overlay_root=overlay_root)

    process = _run_command(
        args=[
            "pixi",
            "run",
            "houmao-mgr",
            "agents",
            "launch",
            "--agents",
            "server-api-smoke",
            "--provider",
            "claude_code",
            "--auth",
            auth_name,
            "--headless",
        ],
        cwd=workdir,
        env=env,
    )
    payload = _load_launch_payload(process.stdout)
    return workdir, payload


def _stop_and_cleanup_session(
    *,
    workdir: Path,
    agent_def_dir: Path,
    agent_id: str,
    manifest_path: Path,
) -> None:
    """Stop and clean up the launched managed session."""

    env = _validated_env(agent_def_dir=agent_def_dir, overlay_root=workdir / ".houmao")
    _run_command(
        args=[
            "pixi",
            "run",
            "houmao-mgr",
            "agents",
            "stop",
            "--agent-id",
            agent_id,
        ],
        cwd=workdir,
        env=env,
    )
    _run_command(
        args=[
            "pixi",
            "run",
            "houmao-mgr",
            "agents",
            "cleanup",
            "session",
            "--manifest-path",
            str(manifest_path),
            "--include-job-dir",
        ],
        cwd=workdir,
        env=env,
    )


def main() -> None:
    """Provision and optionally run the local Claude `official-login` smoke flow."""

    repo_root = _default_repo_root()
    parser = argparse.ArgumentParser(
        description="Provision and run the local Claude official-login smoke validation flow."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=repo_root,
        help="Repository root (defaults to the current checkout).",
    )
    parser.add_argument(
        "--agent-def-dir",
        type=Path,
        default=_default_agent_def_dir(repo_root),
        help="Agent definition root (defaults to tests/fixtures/agents).",
    )
    parser.add_argument(
        "--auth-name",
        default="official-login",
        help="Local Claude auth bundle name to provision and launch.",
    )
    parser.add_argument(
        "--source-config-dir",
        type=Path,
        default=None,
        help="Vendor Claude config root containing `.credentials.json`.",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Provision the local-only auth bundle and exit without launching.",
    )
    parser.add_argument(
        "--skip-provision",
        action="store_true",
        help="Use an already-prepared local-only auth bundle without refreshing it.",
    )
    args = parser.parse_args()

    resolved_repo_root = args.repo_root.resolve()
    resolved_agent_def_dir = args.agent_def_dir.resolve()
    auth_root = _official_login_auth_root(resolved_agent_def_dir, args.auth_name)

    if not args.skip_provision:
        source_config_dir = (
            args.source_config_dir.resolve()
            if args.source_config_dir is not None
            else _default_source_config_dir().resolve()
        )
        prepared_root = _prepare_official_login_bundle(
            auth_root=auth_root,
            source_config_dir=source_config_dir,
        )
        print("claude-official-login-prepare=PASS")
        print(f"auth_root={prepared_root}")
        print(f"source_config_dir={source_config_dir}")

    if args.prepare_only:
        return

    if shutil.which("tmux") is None:
        raise RuntimeError("tmux not found on PATH")

    workdir, launch_payload = _run_smoke_launch(
        repo_root=resolved_repo_root,
        agent_def_dir=resolved_agent_def_dir,
        auth_name=args.auth_name,
    )
    agent_id = str(launch_payload["agent_id"])
    manifest_path = Path(str(launch_payload["manifest_path"])).resolve()
    overlay_root = Path(str(launch_payload["overlay_root"])).resolve()

    if overlay_root != workdir / ".houmao":
        raise RuntimeError(
            f"Expected overlay root `{workdir / '.houmao'}`, got `{overlay_root}`."
        )
    if not manifest_path.is_file():
        raise RuntimeError(f"Expected manifest path `{manifest_path}` to exist after launch.")

    _stop_and_cleanup_session(
        workdir=workdir,
        agent_def_dir=resolved_agent_def_dir,
        agent_id=agent_id,
        manifest_path=manifest_path,
    )

    print("claude-official-login-smoke=PASS")
    print(f"workdir={workdir}")
    print(f"agent_id={agent_id}")
    print(f"manifest_path={manifest_path}")
    print(f"auth_root={auth_root}")


if __name__ == "__main__":
    main()
