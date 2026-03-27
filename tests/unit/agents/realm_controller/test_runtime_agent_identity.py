"""Unit tests for tmux-backed runtime agent-identity resolution."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    derive_agent_id_from_name,
)
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.launch_plan import (
    LaunchPlanRequest,
    build_launch_plan,
)
from houmao.agents.realm_controller.loaders import (
    load_brain_manifest,
    load_role_package,
)
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
)
from houmao.agents.realm_controller.runtime import (
    _resolve_start_session_identity,
    resolve_agent_identity,
)
from houmao.agents.realm_controller.registry_models import (
    LiveAgentRegistryRecordV2,
    RegistryIdentityV1,
    RegistryRuntimeV1,
    RegistryTerminalV1,
)
from houmao.agents.realm_controller.registry_storage import publish_live_agent_record


def _write(path: Path, text: str) -> None:
    """Write text content to a file path, creating parents as needed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolate_shared_registry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Force registry lookups to stay inside each test's temp directory."""

    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str((tmp_path / "registry").resolve()))


def _seed_brain_manifest(agent_def_dir: Path, tmp_path: Path) -> Path:
    """Create a minimal brain manifest and role for runtime tests."""

    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=secret\n", encoding="utf-8")

    manifest_path = tmp_path / "brain.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                "schema_version: 2",
                "inputs:",
                "  tool: codex",
                "runtime:",
                "  launch_executable: codex",
                "  launch_home_selector:",
                "    env_var: CODEX_HOME",
                f"    value: {tmp_path / 'home'}",
                "  launch_contract:",
                "    adapter_defaults:",
                "      args: []",
                "      tool_params: {}",
                "    requested_overrides:",
                "      recipe: null",
                "      direct: null",
                "    tool_metadata:",
                "      tool_params: {}",
                "credentials:",
                "  env_contract:",
                f"    source_file: {env_file}",
                "    allowlisted_env_vars:",
                "      - OPENAI_API_KEY",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt")
    return manifest_path


def _build_cao_manifest(
    agent_def_dir: Path,
    tmp_path: Path,
    *,
    session_name: str,
    path: Path,
    parsing_mode: str = "cao_only",
    agent_name: str | None = None,
    agent_id: str | None = None,
) -> Path:
    """Build and persist a schema-valid CAO session manifest."""

    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)
    manifest = load_brain_manifest(brain_manifest_path)
    role = load_role_package(agent_def_dir, "r")
    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="cao_rest",
            working_directory=tmp_path,
        )
    )

    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="r",
            brain_manifest_path=brain_manifest_path,
            agent_name=agent_name or session_name,
            agent_id=agent_id or derive_agent_id_from_name(agent_name or session_name),
            tmux_session_name=session_name,
            backend_state={
                "api_base_url": "http://localhost:9889",
                "session_name": session_name,
                "terminal_id": "term-1",
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "parsing_mode": parsing_mode,
                "turn_index": 1,
            },
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _build_headless_manifest(
    agent_def_dir: Path,
    tmp_path: Path,
    *,
    backend: str,
    session_name: str,
    path: Path,
    agent_name: str | None = None,
    agent_id: str | None = None,
) -> Path:
    """Build and persist a schema-valid tmux-backed headless manifest."""

    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)
    manifest = load_brain_manifest(brain_manifest_path)
    role = load_role_package(agent_def_dir, "r")
    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend=backend,  # type: ignore[arg-type]
            working_directory=tmp_path,
        )
    )

    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="r",
            brain_manifest_path=brain_manifest_path,
            agent_name=agent_name or session_name,
            agent_id=agent_id or derive_agent_id_from_name(agent_name or session_name),
            tmux_session_name=session_name,
            backend_state={
                "session_id": "sess-or-thread-1",
                "turn_index": 1,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": session_name,
            },
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _publish_registry_resolution_record(
    *,
    manifest_path: Path,
    agent_def_dir: Path,
    session_name: str = "AGENTSYS-gpu",
) -> None:
    """Publish one fresh shared-registry record for resolution tests."""

    now = datetime.now(UTC)
    publish_live_agent_record(
        LiveAgentRegistryRecordV2(
            agent_name=session_name,
            agent_id=derive_agent_id_from_name(session_name),
            generation_id="generation-1",
            published_at=now.isoformat(timespec="seconds"),
            lease_expires_at=(now + timedelta(hours=24)).isoformat(timespec="seconds"),
            identity=RegistryIdentityV1(backend="cao_rest", tool="codex"),
            runtime=RegistryRuntimeV1(
                manifest_path=str(manifest_path.resolve()),
                session_root=str(manifest_path.parent.resolve()),
                agent_def_dir=str(agent_def_dir.resolve()),
            ),
            terminal=RegistryTerminalV1(session_name=session_name),
        )
    )


def _completed(
    args: list[str], *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    """Build a `CompletedProcess` helper for tmux command mocks."""

    return subprocess.CompletedProcess(
        args=args,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_resolve_agent_identity_path_like_missing_fails_fast(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _fail_if_called(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise AssertionError("tmux must not be called for path-like identity")

    monkeypatch.setattr("subprocess.run", _fail_if_called)
    with pytest.raises(SessionManifestError, match="Session manifest not found"):
        resolve_agent_identity(
            agent_identity=str(tmp_path / "missing.json"),
            base=tmp_path,
        )


@pytest.mark.parametrize("parsing_mode", ["cao_only", "shadow_only"])
def test_resolve_agent_identity_name_reads_tmux_manifest_pointer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    parsing_mode: str,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    tmux_agent_def_dir = tmp_path / "live-agent-defs"
    tmux_agent_def_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / "cao.json",
        parsing_mode=parsing_mode,
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "tmux"
        if cmd[1:3] == ["has-session", "-t"]:
            assert cmd[3] == "AGENTSYS-gpu"
            return _completed(cmd)
        if cmd[1:3] == ["show-environment", "-t"]:
            assert cmd[3] == "AGENTSYS-gpu"
            if cmd[4] == AGENT_MANIFEST_PATH_ENV_VAR:
                return _completed(
                    cmd,
                    stdout=f"{AGENT_MANIFEST_PATH_ENV_VAR}={manifest_path}\n",
                )
            return _completed(
                cmd,
                stdout=f"{AGENT_DEF_DIR_ENV_VAR}={tmux_agent_def_dir}\n",
            )
        raise AssertionError(f"Unexpected tmux command: {cmd}")

    monkeypatch.setattr("subprocess.run", _fake_run)

    resolved = resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)
    assert resolved.canonical_agent_identity == "AGENTSYS-gpu"
    assert resolved.session_manifest_path == manifest_path.resolve()
    assert resolved.agent_def_dir == tmux_agent_def_dir.resolve()


def test_resolve_agent_identity_name_fails_when_tmux_session_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "tmux"
        return _completed(
            cmd,
            returncode=1,
            stderr="can't find session: AGENTSYS-gpu",
        )

    monkeypatch.setattr("subprocess.run", _fake_run)
    with pytest.raises(SessionManifestError, match="Agent not found"):
        resolve_agent_identity(agent_identity="gpu", base=tmp_path)


def test_resolve_agent_identity_name_fails_when_manifest_pointer_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    call_index = {"count": 0}

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        call_index["count"] += 1
        if call_index["count"] == 1:
            return _completed(cmd)
        return _completed(cmd, returncode=1, stderr="unknown variable: AGENTSYS_MANIFEST_PATH")

    monkeypatch.setattr("subprocess.run", _fake_run)
    with pytest.raises(SessionManifestError, match="Manifest pointer missing"):
        resolve_agent_identity(agent_identity="gpu", base=tmp_path)


def test_resolve_agent_identity_name_falls_back_when_manifest_pointer_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    registry_root = tmp_path / "registry"
    manifest_path = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / "cao.json",
    )
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root))
    _publish_registry_resolution_record(
        manifest_path=manifest_path,
        agent_def_dir=agent_def_dir,
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text, timeout
        if cmd[1:3] == ["has-session", "-t"]:
            return _completed(cmd)
        return _completed(cmd, returncode=1, stderr="unknown variable: AGENTSYS_MANIFEST_PATH")

    monkeypatch.setattr("subprocess.run", _fake_run)

    resolved = resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)

    assert resolved.canonical_agent_identity == "AGENTSYS-gpu"
    assert resolved.session_manifest_path == manifest_path.resolve()
    assert resolved.agent_def_dir == agent_def_dir.resolve()


def test_resolve_agent_identity_name_scans_metadata_for_suffixed_tmux_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    tmux_agent_def_dir = tmp_path / "live-agent-defs"
    tmux_agent_def_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-gpu-270b87",
        agent_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / "cao-suffixed.json",
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text, timeout
        if cmd[1:3] == ["has-session", "-t"]:
            assert cmd[3] == "AGENTSYS-gpu"
            return _completed(cmd, returncode=1, stderr="can't find session: AGENTSYS-gpu")
        if cmd[1:3] == ["list-sessions", "-F"]:
            return _completed(cmd, stdout="AGENTSYS-gpu-270b87\n")
        if cmd[1:3] == ["show-environment", "-t"]:
            assert cmd[3] == "AGENTSYS-gpu-270b87"
            if cmd[4] == AGENT_MANIFEST_PATH_ENV_VAR:
                return _completed(
                    cmd,
                    stdout=f"{AGENT_MANIFEST_PATH_ENV_VAR}={manifest_path}\n",
                )
            return _completed(
                cmd,
                stdout=f"{AGENT_DEF_DIR_ENV_VAR}={tmux_agent_def_dir}\n",
            )
        raise AssertionError(f"Unexpected tmux command: {cmd}")

    monkeypatch.setattr("subprocess.run", _fake_run)

    resolved = resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)

    assert resolved.canonical_agent_identity == "AGENTSYS-gpu"
    assert resolved.session_manifest_path == manifest_path.resolve()
    assert resolved.agent_def_dir == tmux_agent_def_dir.resolve()


def test_resolve_agent_identity_name_fails_when_manifest_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-other",
        path=tmp_path / "sessions" / "cao.json",
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if cmd[1] == "has-session":
            return _completed(cmd)
        return _completed(cmd, stdout=f"AGENTSYS_MANIFEST_PATH={manifest_path}\n")

    monkeypatch.setattr("subprocess.run", _fake_run)

    with pytest.raises(SessionManifestError, match="does not match addressed tmux session"):
        resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)


def test_resolve_agent_identity_name_fails_when_multiple_suffixed_sessions_match(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    manifest_path_a = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-gpu-270b87",
        agent_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / "cao-a.json",
    )
    manifest_path_b = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-gpu-270b873",
        agent_name="AGENTSYS-gpu",
        agent_id="270b8738f2f97092e572b73d19e6f923",
        path=tmp_path / "sessions" / "cao-b.json",
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text, timeout
        if cmd[1:3] == ["has-session", "-t"]:
            return _completed(cmd, returncode=1, stderr="can't find session: AGENTSYS-gpu")
        if cmd[1:3] == ["list-sessions", "-F"]:
            return _completed(cmd, stdout="AGENTSYS-gpu-270b87\nAGENTSYS-gpu-270b873\n")
        if cmd[1:3] == ["show-environment", "-t"]:
            manifest_path = manifest_path_a if cmd[3] == "AGENTSYS-gpu-270b87" else manifest_path_b
            if cmd[4] == AGENT_MANIFEST_PATH_ENV_VAR:
                return _completed(
                    cmd,
                    stdout=f"{AGENT_MANIFEST_PATH_ENV_VAR}={manifest_path}\n",
                )
            return _completed(
                cmd,
                stdout=f"{AGENT_DEF_DIR_ENV_VAR}={agent_def_dir}\n",
            )
        raise AssertionError(f"Unexpected tmux command: {cmd}")

    monkeypatch.setattr("subprocess.run", _fake_run)

    with pytest.raises(SessionManifestError, match="matched multiple tmux sessions"):
        resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)


def test_resolve_agent_identity_name_uses_explicit_agent_def_dir_override_for_legacy_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    override_agent_def_dir = tmp_path / "override-agent-defs"
    override_agent_def_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / "cao.json",
    )
    show_environment_variables: list[str] = []

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "tmux"
        if cmd[1:3] == ["has-session", "-t"]:
            return _completed(cmd)
        if cmd[1:3] == ["show-environment", "-t"]:
            show_environment_variables.append(cmd[4])
            return _completed(
                cmd,
                stdout=f"{AGENT_MANIFEST_PATH_ENV_VAR}={manifest_path}\n",
            )
        raise AssertionError(f"Unexpected tmux command: {cmd}")

    monkeypatch.setattr("subprocess.run", _fake_run)

    resolved = resolve_agent_identity(
        agent_identity="gpu",
        base=agent_def_dir,
        explicit_agent_def_dir=override_agent_def_dir,
    )

    assert resolved.session_manifest_path == manifest_path.resolve()
    assert resolved.agent_def_dir == override_agent_def_dir.resolve()


def test_resolve_agent_identity_falls_back_to_shared_registry_when_tmux_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    registry_root = tmp_path / "registry"
    manifest_path = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / "cao.json",
    )
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root))

    now = datetime.now(UTC)
    publish_live_agent_record(
        LiveAgentRegistryRecordV2(
            agent_name="AGENTSYS-gpu",
            agent_id=derive_agent_id_from_name("AGENTSYS-gpu"),
            generation_id="generation-1",
            published_at=now.isoformat(timespec="seconds"),
            lease_expires_at=(now + timedelta(hours=24)).isoformat(timespec="seconds"),
            identity=RegistryIdentityV1(backend="cao_rest", tool="codex"),
            runtime=RegistryRuntimeV1(
                manifest_path=str(manifest_path.resolve()),
                session_root=str(manifest_path.parent.resolve()),
                agent_def_dir=str(agent_def_dir.resolve()),
            ),
            terminal=RegistryTerminalV1(session_name="AGENTSYS-gpu"),
        )
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text, timeout
        return _completed(cmd, returncode=1, stderr="can't find session: AGENTSYS-gpu")

    monkeypatch.setattr("subprocess.run", _fake_run)

    resolved = resolve_agent_identity(agent_identity="gpu", base=tmp_path)

    assert resolved.canonical_agent_identity == "AGENTSYS-gpu"
    assert resolved.session_manifest_path == manifest_path.resolve()
    assert resolved.agent_def_dir == agent_def_dir.resolve()


def test_resolve_agent_identity_name_fails_when_agent_def_dir_pointer_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / "cao.json",
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "tmux"
        if cmd[1:3] == ["has-session", "-t"]:
            return _completed(cmd)
        if cmd[1:3] == ["show-environment", "-t"] and cmd[4] == AGENT_MANIFEST_PATH_ENV_VAR:
            return _completed(
                cmd,
                stdout=f"{AGENT_MANIFEST_PATH_ENV_VAR}={manifest_path}\n",
            )
        return _completed(
            cmd,
            returncode=1,
            stderr=f"unknown variable: {AGENT_DEF_DIR_ENV_VAR}",
        )

    monkeypatch.setattr("subprocess.run", _fake_run)

    with pytest.raises(SessionManifestError, match="Agent definition pointer missing"):
        resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)


def test_resolve_agent_identity_name_falls_back_when_agent_def_dir_pointer_stale(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    stale_agent_def_dir = tmp_path / "stale-agent-defs"
    registry_root = tmp_path / "registry"
    manifest_path = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / "cao.json",
    )
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root))
    _publish_registry_resolution_record(
        manifest_path=manifest_path,
        agent_def_dir=agent_def_dir,
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text, timeout
        if cmd[1:3] == ["list-sessions", "-F"]:
            return _completed(cmd, stdout="AGENTSYS-gpu\n")
        if cmd[1:3] == ["has-session", "-t"]:
            return _completed(cmd)
        if cmd[4] == AGENT_MANIFEST_PATH_ENV_VAR:
            return _completed(
                cmd,
                stdout=f"{AGENT_MANIFEST_PATH_ENV_VAR}={manifest_path}\n",
            )
        return _completed(
            cmd,
            stdout=f"{AGENT_DEF_DIR_ENV_VAR}={stale_agent_def_dir}\n",
        )

    monkeypatch.setattr("subprocess.run", _fake_run)

    resolved = resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)

    assert resolved.canonical_agent_identity == "AGENTSYS-gpu"
    assert resolved.session_manifest_path == manifest_path.resolve()
    assert resolved.agent_def_dir == agent_def_dir.resolve()


def test_resolve_agent_identity_name_fails_when_agent_def_dir_pointer_blank(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / "cao.json",
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "tmux"
        if cmd[1:3] == ["has-session", "-t"]:
            return _completed(cmd)
        if cmd[1:3] == ["show-environment", "-t"] and cmd[4] == AGENT_MANIFEST_PATH_ENV_VAR:
            return _completed(
                cmd,
                stdout=f"{AGENT_MANIFEST_PATH_ENV_VAR}={manifest_path}\n",
            )
        return _completed(
            cmd,
            stdout=f"{AGENT_DEF_DIR_ENV_VAR}=\n",
        )

    monkeypatch.setattr("subprocess.run", _fake_run)

    with pytest.raises(SessionManifestError, match="Agent definition pointer missing"):
        resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)


def test_resolve_agent_identity_name_fails_when_agent_def_dir_pointer_is_relative(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / "cao.json",
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "tmux"
        if cmd[1:3] == ["has-session", "-t"]:
            return _completed(cmd)
        if cmd[1:3] == ["show-environment", "-t"] and cmd[4] == AGENT_MANIFEST_PATH_ENV_VAR:
            return _completed(
                cmd,
                stdout=f"{AGENT_MANIFEST_PATH_ENV_VAR}={manifest_path}\n",
            )
        return _completed(
            cmd,
            stdout=f"{AGENT_DEF_DIR_ENV_VAR}=relative/agents\n",
        )

    monkeypatch.setattr("subprocess.run", _fake_run)

    with pytest.raises(SessionManifestError, match="must be an absolute path"):
        resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)


def test_resolve_agent_identity_name_fails_when_agent_def_dir_pointer_is_stale(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / "cao.json",
    )
    stale_agent_def_dir = tmp_path / "missing-agent-defs"

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "tmux"
        if cmd[1:3] == ["has-session", "-t"]:
            return _completed(cmd)
        if cmd[1:3] == ["show-environment", "-t"] and cmd[4] == AGENT_MANIFEST_PATH_ENV_VAR:
            return _completed(
                cmd,
                stdout=f"{AGENT_MANIFEST_PATH_ENV_VAR}={manifest_path}\n",
            )
        return _completed(
            cmd,
            stdout=f"{AGENT_DEF_DIR_ENV_VAR}={stale_agent_def_dir}\n",
        )

    monkeypatch.setattr("subprocess.run", _fake_run)

    with pytest.raises(SessionManifestError, match="points to missing directory"):
        resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)


@pytest.mark.parametrize("backend", ["codex_headless", "claude_headless", "gemini_headless"])
def test_resolve_agent_identity_accepts_tmux_backed_headless_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    backend: str,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    tmux_agent_def_dir = tmp_path / "live-agent-defs"
    tmux_agent_def_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _build_headless_manifest(
        agent_def_dir,
        tmp_path,
        backend=backend,
        session_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / f"{backend}.json",
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "tmux"
        if cmd[1:3] == ["has-session", "-t"]:
            return _completed(cmd)
        if cmd[1:3] == ["show-environment", "-t"]:
            if cmd[4] == AGENT_MANIFEST_PATH_ENV_VAR:
                return _completed(
                    cmd,
                    stdout=f"{AGENT_MANIFEST_PATH_ENV_VAR}={manifest_path}\n",
                )
            return _completed(
                cmd,
                stdout=f"{AGENT_DEF_DIR_ENV_VAR}={tmux_agent_def_dir}\n",
            )
        raise AssertionError(f"Unexpected tmux command: {cmd}")

    monkeypatch.setattr("subprocess.run", _fake_run)
    resolved = resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)
    assert resolved.session_manifest_path == manifest_path.resolve()
    assert resolved.agent_def_dir == tmux_agent_def_dir.resolve()


def test_resolve_start_session_identity_uses_timestamp_based_tmux_handle_for_raw_agent_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.list_tmux_sessions_shared",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.time.time_ns",
        lambda: 1760000123456000000,
    )

    resolved = _resolve_start_session_identity(
        manifest={},
        tool="codex",
        role_name="gpu-kernel-coder",
        requested_agent_name="gpu",
        requested_agent_identity=None,
        requested_agent_id="deadbeefcafefeed",
    )

    assert resolved.agent_name == "gpu"
    assert resolved.canonical_agent_name == "AGENTSYS-gpu"
    assert resolved.agent_id == "deadbeefcafefeed"
    assert resolved.tmux_session_name == "AGENTSYS-gpu-1760000123456"


def test_resolve_start_session_identity_rejects_reserved_prefixed_raw_agent_name() -> None:
    with pytest.raises(SessionManifestError, match="raw creation-time name"):
        _resolve_start_session_identity(
            manifest={},
            tool="codex",
            role_name="gpu-kernel-coder",
            requested_agent_name="AGENTSYS-gpu",
            requested_agent_identity=None,
            requested_agent_id=None,
        )


def test_resolve_start_session_identity_fails_when_generated_default_name_collides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical_agent_name = "AGENTSYS-gpu"
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.list_tmux_sessions_shared",
        lambda: {f"{canonical_agent_name}-1760000123456"},
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.time.time_ns",
        lambda: 1760000123456000000,
    )

    with pytest.raises(SessionManifestError, match="already in use"):
        _resolve_start_session_identity(
            manifest={},
            tool="codex",
            role_name="gpu-kernel-coder",
            requested_agent_name="gpu",
            requested_agent_identity=None,
            requested_agent_id=None,
        )


def test_resolve_start_session_identity_preserves_explicit_tmux_session_name_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.list_tmux_sessions_shared",
        lambda: (_ for _ in ()).throw(AssertionError("default generator should be bypassed")),
    )

    resolved = _resolve_start_session_identity(
        manifest={},
        tool="codex",
        role_name="gpu-kernel-coder",
        requested_agent_name="gpu",
        requested_agent_identity=None,
        requested_agent_id=derive_agent_id_from_name("gpu"),
        requested_tmux_session_name="custom-gpu",
    )

    assert resolved.agent_name == "gpu"
    assert resolved.canonical_agent_name == "AGENTSYS-gpu"
    assert resolved.tmux_session_name == "custom-gpu"


def test_tmux_backed_manifest_build_rejects_suffixed_handle_without_explicit_identity(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)
    manifest = load_brain_manifest(brain_manifest_path)
    role = load_role_package(agent_def_dir, "r")
    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="cao_rest",
            working_directory=tmp_path,
        )
    )

    with pytest.raises(SessionManifestError, match="agent_name, agent_id, and tmux_session_name"):
        build_session_manifest_payload(
            SessionManifestRequest(
                launch_plan=launch_plan,
                role_name="r",
                brain_manifest_path=brain_manifest_path,
                backend_state={
                    "api_base_url": "http://localhost:9889",
                    "session_name": "AGENTSYS-gpu-270b87",
                    "terminal_id": "term-1",
                    "profile_name": "runtime-profile",
                    "profile_path": str(tmp_path / "runtime-profile.md"),
                    "parsing_mode": "cao_only",
                    "turn_index": 1,
                },
            )
        )
