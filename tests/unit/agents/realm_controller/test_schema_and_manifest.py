from __future__ import annotations

import json
from pathlib import Path

import pytest

from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    load_session_manifest,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
)


def _identity_fields(session_name: str) -> dict[str, str]:
    return {
        "agent_name": session_name,
        "agent_id": derive_agent_id_from_name(session_name),
        "tmux_session_name": session_name,
    }


def _sample_plan(tmp_path: Path) -> LaunchPlan:
    return LaunchPlan(
        backend="claude_headless",
        tool="claude",
        executable="claude",
        args=["-p"],
        working_directory=tmp_path,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env={"ANTHROPIC_API_KEY": "secret"},
        env_var_names=["ANTHROPIC_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="native_append_system_prompt",
            role_name="gpu-kernel-coder",
            prompt="Be precise",
            bootstrap_message="bootstrap",
        ),
        metadata={"headless_output_format": "stream-json"},
    )


def _sample_cao_plan(tmp_path: Path) -> LaunchPlan:
    return LaunchPlan(
        backend="cao_rest",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={"OPENAI_API_KEY": "secret"},
        env_var_names=["OPENAI_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="gpu-kernel-coder",
            prompt="Be precise",
        ),
        metadata={},
    )


def _sample_houmao_plan(tmp_path: Path) -> LaunchPlan:
    return LaunchPlan(
        backend="houmao_server_rest",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={"OPENAI_API_KEY": "secret"},
        env_var_names=["OPENAI_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="gpu-kernel-coder",
            prompt="Be precise",
        ),
        metadata={},
    )


def test_session_manifest_write_and_load_round_trip(tmp_path: Path) -> None:
    plan = _sample_plan(tmp_path)
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("AGENTSYS-claude"),
            backend_state={
                "session_id": "sess-1",
                "turn_index": 2,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": "AGENTSYS-claude",
            },
        )
    )

    path = tmp_path / "session.json"
    write_session_manifest(path, payload)
    loaded = load_session_manifest(path)

    assert loaded.path == path
    assert loaded.payload["schema_version"] == 3
    assert loaded.payload["backend"] == "claude_headless"
    assert loaded.payload["agent_name"] == "AGENTSYS-claude"
    assert loaded.payload["agent_id"] == derive_agent_id_from_name("AGENTSYS-claude")
    assert loaded.payload["tmux_session_name"] == "AGENTSYS-claude"
    assert loaded.payload["headless"]["session_id"] == "sess-1"
    assert loaded.payload["backend_state"]["tmux_session_name"] == "AGENTSYS-claude"
    assert "secret" not in path.read_text(encoding="utf-8")


def test_manifest_write_validation_fails_with_field_path(tmp_path: Path) -> None:
    plan = _sample_plan(tmp_path)
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("AGENTSYS-claude"),
            backend_state={
                "session_id": "sess-1",
                "turn_index": 0,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": "AGENTSYS-claude",
            },
        )
    )
    payload["launch_plan"]["role_injection"] = {"role_name": "gpu-kernel-coder"}

    with pytest.raises(SessionManifestError, match=r"\$\.launch_plan\.role_injection\.method"):
        write_session_manifest(tmp_path / "session.json", payload)


def test_manifest_load_validation_fails_with_field_path(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    agent_id = derive_agent_id_from_name("AGENTSYS-r")
    path.write_text(
        (
            "{"
            '"schema_version": 3,'
            '"backend": "claude_headless",'
            '"tool": "claude",'
            '"role_name": "r",'
            '"created_at_utc": "2026-01-01T00:00:00+00:00",'
            '"working_directory": "/tmp/work",'
            '"brain_manifest_path": "/tmp/brain.yaml",'
            '"agent_name": "AGENTSYS-r",'
            f'"agent_id": "{agent_id}",'
            '"tmux_session_name": "AGENTSYS-r",'
            '"job_dir": null,'
            '"launch_plan": {"backend":"claude_headless","tool":"claude","executable":"claude","args":[],"working_directory":"/tmp/work","home_selector":{"env_var":"CLAUDE_CONFIG_DIR","home_path":"/tmp/home"},"env_var_names":[],"role_injection":{"method":"cao_profile","role_name":"r"},"metadata":{}},'
            '"backend_state": [],'
            '"headless": {"session_id":"sess","turn_index":0,"role_bootstrap_applied":true,"working_directory":"/tmp/work"}'
            "}"
        ),
        encoding="utf-8",
    )

    with pytest.raises(SessionManifestError, match=r"\$\.backend_state"):
        load_session_manifest(path)


def test_legacy_cao_manifest_schema_is_rejected(tmp_path: Path) -> None:
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_cao_plan(tmp_path),
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("AGENTSYS-gpu"),
            backend_state={
                "api_base_url": "http://localhost:9889",
                "session_name": "AGENTSYS-gpu",
                "terminal_id": "term-123",
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "parsing_mode": "cao_only",
                "turn_index": 1,
            },
        )
    )
    payload["schema_version"] = 1
    payload["cao"].pop("parsing_mode")
    payload["backend_state"].pop("parsing_mode")

    path = tmp_path / "legacy-cao-session.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SessionManifestError, match="schema-version mismatch"):
        load_session_manifest(path)


def test_cao_manifest_round_trip_persists_optional_tmux_window_name(
    tmp_path: Path,
) -> None:
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_cao_plan(tmp_path),
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("AGENTSYS-gpu"),
            backend_state={
                "api_base_url": "http://localhost:9889",
                "session_name": "AGENTSYS-gpu",
                "terminal_id": "term-123",
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "tmux_window_name": "developer-1",
                "parsing_mode": "shadow_only",
                "turn_index": 1,
            },
        )
    )

    path = tmp_path / "cao-session.json"
    write_session_manifest(path, payload)
    loaded = load_session_manifest(path)

    assert loaded.payload["agent_name"] == "AGENTSYS-gpu"
    assert loaded.payload["agent_id"] == derive_agent_id_from_name("AGENTSYS-gpu")
    assert loaded.payload["tmux_session_name"] == "AGENTSYS-gpu"
    assert loaded.payload["cao"]["tmux_window_name"] == "developer-1"
    assert loaded.payload["backend_state"]["tmux_window_name"] == "developer-1"


def test_houmao_manifest_round_trip_uses_dedicated_backend_section(tmp_path: Path) -> None:
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_houmao_plan(tmp_path),
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("AGENTSYS-gpu"),
            backend_state={
                "api_base_url": "http://127.0.0.1:9889",
                "session_name": "cao-gpu",
                "terminal_id": "abcd1234",
                "tmux_window_name": "developer-1",
                "parsing_mode": "shadow_only",
                "turn_index": 1,
            },
        )
    )

    path = tmp_path / "houmao-session.json"
    write_session_manifest(path, payload)
    loaded = load_session_manifest(path)

    assert loaded.payload["backend"] == "houmao_server_rest"
    assert loaded.payload["houmao_server"]["api_base_url"] == "http://127.0.0.1:9889"
    assert loaded.payload["houmao_server"]["session_name"] == "cao-gpu"
    assert loaded.payload["houmao_server"]["terminal_id"] == "abcd1234"
    assert loaded.payload["houmao_server"]["tmux_window_name"] == "developer-1"
    assert "cao" not in loaded.payload or loaded.payload["cao"] is None
