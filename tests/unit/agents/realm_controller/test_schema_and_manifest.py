from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from houmao.agents.launch_policy import LaunchPolicyProvenance
from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.errors import RetiredJoinedSessionError, SessionManifestError
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    load_session_manifest,
    parse_session_manifest_payload,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
)
from houmao.agents.realm_controller.session_authority import resolve_manifest_session_authority
from houmao.execution.context import observed_local_binding


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
        launch_policy_provenance=LaunchPolicyProvenance(
            requested_operator_prompt_mode="unattended",
            detected_tool_version="2.1.296",
            selected_strategy_id="claude-unattended-2.1.296",
            selection_source="registry",
        ),
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


def _sample_local_interactive_plan(tmp_path: Path) -> LaunchPlan:
    return LaunchPlan(
        backend="local_interactive",
        tool="claude",
        executable="claude",
        args=["--dangerously-skip-permissions"],
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


@pytest.mark.parametrize("explicit_null_adoption_fields", [True, False])
def test_session_manifest_write_and_load_round_trip(
    tmp_path: Path, *, explicit_null_adoption_fields: bool
) -> None:
    plan = _sample_plan(tmp_path)
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("HOUMAO-claude"),
            backend_state={
                "session_id": "sess-1",
                "turn_index": 2,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": "HOUMAO-claude",
                "tmux_window_id": "@7",
                "tmux_pane_id": "%7",
            },
            memory_root=(tmp_path / "memory" / "agents" / "agent-a").resolve(),
            memo_file=(tmp_path / "memory" / "agents" / "agent-a" / "houmao-memo.md").resolve(),
            pages_dir=(tmp_path / "memory" / "agents" / "agent-a" / "pages").resolve(),
        )
    )

    adoption_fields = ("session_origin", "launch_args", "launch_env")
    assert all(payload["agent_launch_authority"][field] is None for field in adoption_fields)
    if not explicit_null_adoption_fields:
        for field in adoption_fields:
            del payload["agent_launch_authority"][field]

    path = tmp_path / "session.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = load_session_manifest(path)
    write_session_manifest(path, payload)
    assert load_session_manifest(path) == loaded

    assert loaded.path == path
    assert loaded.payload["schema_version"] == 6
    assert loaded.payload["mode"] == "headless"
    assert loaded.payload["launch_plan"]["mode"] == "headless"
    assert loaded.payload["backend"] == "claude_headless"
    assert loaded.payload["agent_name"] == "HOUMAO-claude"
    assert loaded.payload["agent_id"] == derive_agent_id_from_name("HOUMAO-claude")
    assert loaded.payload["tmux_session_name"] == "HOUMAO-claude"
    assert loaded.payload["registry_launch_authority"] == "runtime"
    assert loaded.payload["runtime"]["session_id"] == "sess-1"
    assert loaded.payload["runtime"]["memory_root"] == str(
        (tmp_path / "memory" / "agents" / "agent-a").resolve()
    )
    assert loaded.payload["runtime"]["memo_file"] == str(
        (tmp_path / "memory" / "agents" / "agent-a" / "houmao-memo.md").resolve()
    )
    assert loaded.payload["runtime"]["pages_dir"] == str(
        (tmp_path / "memory" / "agents" / "agent-a" / "pages").resolve()
    )
    assert loaded.payload["runtime"]["agent_pid"] is None
    assert loaded.payload["tmux"]["session_name"] == "HOUMAO-claude"
    assert loaded.payload["tmux"]["primary_window_id"] == "@7"
    assert loaded.payload["tmux"]["primary_pane_id"] == "%7"
    assert loaded.payload["agent_launch_authority"]["primary_window_index"] == "0"
    assert loaded.payload["agent_launch_authority"]["primary_window_id"] == "@7"
    assert loaded.payload["agent_launch_authority"]["primary_pane_id"] == "%7"
    assert all(loaded.payload["agent_launch_authority"][field] is None for field in adoption_fields)
    assert loaded.payload["headless"]["session_id"] == "sess-1"
    assert loaded.payload["backend_state"]["tmux_session_name"] == "HOUMAO-claude"
    assert loaded.payload["launch_policy_provenance"]["selected_strategy_id"] == (
        "claude-unattended-2.1.296"
    )
    assert loaded.payload["launch_plan"]["launch_policy_provenance"]["detected_tool_version"] == (
        "2.1.296"
    )
    assert loaded.payload["system_prompt"] == {
        "format": "text",
        "role_name": "gpu-kernel-coder",
        "text": "Be precise",
        "sha256": hashlib.sha256("Be precise".encode("utf-8")).hexdigest(),
        "source": "launch_plan.role_injection.prompt",
    }
    assert "secret" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("headless", [False, True], ids=["tui", "headless"])
def test_retired_joined_manifest_cannot_be_loaded_or_written(
    tmp_path: Path, *, headless: bool
) -> None:
    plan = _sample_plan(tmp_path) if headless else _sample_local_interactive_plan(tmp_path)
    native = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("HOUMAO-claude"),
            backend_state={"tmux_window_id": "@7", "tmux_pane_id": "%7"},
        )
    )
    retired = deepcopy(native)
    authority = retired["agent_launch_authority"]
    authority["session_origin"] = "joined_tmux"
    authority["posture_kind"] = "headless_launch_options" if headless else "unavailable"
    if headless:
        authority["launch_args"] = ["-p"]
    retired["launch_plan"]["metadata"]["session_origin"] = "joined_tmux"

    new_path = tmp_path / "new" / "manifest.json"
    with pytest.raises(RetiredJoinedSessionError, match="fresh supported managed launch"):
        write_session_manifest(new_path, retired)
    assert not new_path.parent.exists()

    path = tmp_path / "manifest.json"
    stored = json.dumps(retired)
    path.write_text(stored, encoding="utf-8")
    with pytest.raises(RetiredJoinedSessionError, match="owning Houmao release") as rejected:
        load_session_manifest(path)
    assert rejected.value.agent_id == native["agent_id"]
    assert rejected.value.agent_name == native["agent_name"]
    assert rejected.value.brain_manifest_path == str(tmp_path / "brain.yaml")
    assert rejected.value.home_path == str(plan.home_path)
    with pytest.raises(RetiredJoinedSessionError):
        write_session_manifest(path, native)
    assert list(tmp_path.iterdir()) == [path]
    assert path.read_text(encoding="utf-8") == stored


@pytest.mark.parametrize("marker", ["authority", "metadata"])
def test_partial_manifest_still_reports_retired_adoption(marker: str) -> None:
    launch_plan = {
        "mailboxes": {
            "offline": {"binding": {"credential_ref": "archive-ref"}},
            "online": {"binding": None},
        }
    }
    payload = {"schema_version": 6, "launch_plan": launch_plan}
    if marker == "authority":
        payload["agent_launch_authority"] = {"session_origin": "joined_tmux"}
    else:
        launch_plan["metadata"] = {"session_origin": "joined_tmux"}

    with pytest.raises(RetiredJoinedSessionError) as rejected:
        parse_session_manifest_payload(payload, source="legacy fixture")
    assert rejected.value.mailbox_credential_refs == ("archive-ref",)
    assert "archive-ref" not in str(rejected.value)


def test_codex_service_manifest_requires_current_owner_binding(tmp_path: Path) -> None:
    """Accept current owner authority and reject retired or mismatched Codex state."""

    binding = observed_local_binding(
        working_directory=tmp_path,
        runtime_root=tmp_path / "runtime",
        registry_root=tmp_path / "registry",
        tmux_socket=str(tmp_path / "tmux.sock"),
    )
    plan = replace(
        _sample_plan(tmp_path),
        backend="codex_app_server",
        tool="codex",
        executable="/selected/codex",
        args=["app-server", "--listen", "stdio://"],
        home_env_var="CODEX_HOME",
        execution_binding=binding,
        metadata={"tmux_socket_path": binding.tmux_socket},
    )
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("HOUMAO-codex"),
            session_id="runtime-id",
            registry_generation_id="generation",
            backend_state={
                "runtime_session_id": "runtime-id",
                "generation_id": "generation",
                "service_incarnation": "incarnation",
                "native_session_id": "codex-thread",
                "working_directory": str(tmp_path),
                "tmux_session_name": "HOUMAO-codex",
                "tmux_window_id": "@7",
                "tmux_pane_id": "%7",
            },
        )
    )
    parsed = parse_session_manifest_payload(payload, source="test")
    assert parsed.mode == "service" and parsed.native_surface is None
    assert parsed.backend_state["native_session_id"] == "codex-thread"
    assert parsed.tmux is not None and parsed.tmux.primary_window_role == "supervisor_logs"
    assert parsed.codex is None and parsed.headless is None

    legacy = deepcopy(payload)
    legacy["codex"] = {"thread_id": "codex-thread", "turn_index": 0, "pid": 1}
    with pytest.raises(SessionManifestError, match=r"Retired Codex.*Start a fresh runtime session"):
        parse_session_manifest_payload(legacy, source="legacy")
    legacy["schema_version"] = 5
    with pytest.raises(SessionManifestError, match=r"schema-version mismatch.*fresh runtime"):
        parse_session_manifest_payload(legacy, source="legacy-v5")

    for key, value in (
        ("generation_id", "other-generation"),
        ("runtime_session_id", "other-session"),
        ("tmux_pane_id", "%8"),
        ("working_directory", "/other/workspace"),
    ):
        stale = deepcopy(payload)
        stale["backend_state"][key] = value
        with pytest.raises(SessionManifestError, match="current service identity differs"):
            parse_session_manifest_payload(stale, source="stale")


def test_bound_manifest_generation_change_requires_captured_handoff(tmp_path: Path) -> None:
    """A stale writer cannot revert a committed relaunch even after its admission check."""

    binding = observed_local_binding(
        working_directory=tmp_path,
        runtime_root=tmp_path / "runtime",
        registry_root=tmp_path / "registry",
        tmux_socket=str(tmp_path / "tmux.sock"),
    )
    plan = replace(
        _sample_plan(tmp_path),
        execution_binding=binding,
        metadata={"tmux_socket_path": binding.tmux_socket},
    )
    original = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("HOUMAO-claude"),
            registry_generation_id="previous-generation",
            backend_state={
                "session_id": "sess-1",
                "turn_index": 0,
                "role_bootstrap_applied": False,
                "working_directory": str(tmp_path),
                "tmux_session_name": "HOUMAO-claude",
            },
        )
    )
    path = tmp_path / "session.json"
    write_session_manifest(path, original)
    replacement = deepcopy(original)
    replacement["registry_generation_id"] = "next-generation"
    replacement["runtime"]["registry_generation_id"] = "next-generation"
    with pytest.raises(SessionManifestError, match="generation changed"):
        write_session_manifest(path, replacement)
    write_session_manifest(path, replacement, expected_registry_generation_id="previous-generation")
    committed = path.read_bytes()

    with pytest.raises(SessionManifestError, match="generation changed"):
        write_session_manifest(path, original)
    assert path.read_bytes() == committed


def test_manifest_preserves_saved_socket_over_current_operation(tmp_path: Path) -> None:
    """Updating a saved runtime cannot move it onto the caller's current server."""

    from houmao.execution.tmux import tmux_server_scope

    request = SessionManifestRequest(
        launch_plan=_sample_plan(tmp_path),
        role_name="gpu-kernel-coder",
        brain_manifest_path=tmp_path / "brain.yaml",
        **_identity_fields("HOUMAO-claude"),
        backend_state={
            "session_id": "sess-1",
            "turn_index": 0,
            "role_bootstrap_applied": False,
            "tmux_session_name": "HOUMAO-claude",
            "tmux_socket_path": "/owner/saved.sock",
        },
    )
    with tmux_server_scope("/caller/current.sock"):
        payload = build_session_manifest_payload(request)
    assert payload["tmux"]["socket_path"] == "/owner/saved.sock"
    path = tmp_path / "manifest.json"
    write_session_manifest(path, payload)
    assert load_session_manifest(path).payload["tmux"]["socket_path"] == "/owner/saved.sock"


def test_manifest_write_validation_fails_with_field_path(tmp_path: Path) -> None:
    plan = _sample_plan(tmp_path)
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("HOUMAO-claude"),
            backend_state={
                "session_id": "sess-1",
                "turn_index": 0,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": "HOUMAO-claude",
            },
        )
    )
    payload["launch_plan"]["role_injection"] = {"role_name": "gpu-kernel-coder"}

    with pytest.raises(SessionManifestError, match=r"\$\.launch_plan\.role_injection\.method"):
        write_session_manifest(tmp_path / "session.json", payload)


def test_manifest_write_rejects_retired_auto_skill_role_injection(tmp_path: Path) -> None:
    """Current boundaries reject persisted auto-skill prompt delivery."""

    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_plan(tmp_path),
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("HOUMAO-claude"),
            backend_state={
                "session_id": "sess-1",
                "turn_index": 0,
                "role_bootstrap_applied": False,
                "working_directory": str(tmp_path),
                "tmux_session_name": "HOUMAO-claude",
            },
        )
    )
    payload["launch_plan"]["role_injection"]["method"] = "auto_skill_system_prompt"

    with pytest.raises(SessionManifestError, match=r"role_injection\.method"):
        write_session_manifest(tmp_path / "session.json", payload)


def test_manifest_load_rejects_v3_manifest_without_upgrade(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    agent_id = derive_agent_id_from_name("HOUMAO-r")
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
            '"agent_name": "HOUMAO-r",'
            f'"agent_id": "{agent_id}",'
            '"tmux_session_name": "HOUMAO-r",'
            '"job_dir": null,'
            '"launch_plan": {"backend":"claude_headless","tool":"claude","executable":"claude","args":[],"working_directory":"/tmp/work","home_selector":{"env_var":"CLAUDE_CONFIG_DIR","home_path":"/tmp/home"},"env_var_names":[],"role_injection":{"method":"cao_profile","role_name":"r"},"metadata":{}},'
            '"backend_state": [],'
            '"headless": {"session_id":"sess","turn_index":0,"role_bootstrap_applied":true,"working_directory":"/tmp/work"}'
            "}"
        ),
        encoding="utf-8",
    )

    with pytest.raises(SessionManifestError, match="Start a fresh runtime session"):
        load_session_manifest(path)


def test_legacy_cao_manifest_schema_is_rejected(tmp_path: Path) -> None:
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_cao_plan(tmp_path),
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("HOUMAO-gpu"),
            backend_state={
                "api_base_url": "http://localhost:9889",
                "session_name": "HOUMAO-gpu",
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
            **_identity_fields("HOUMAO-gpu"),
            backend_state={
                "api_base_url": "http://localhost:9889",
                "session_name": "HOUMAO-gpu",
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

    assert loaded.payload["agent_name"] == "HOUMAO-gpu"
    assert loaded.payload["agent_id"] == derive_agent_id_from_name("HOUMAO-gpu")
    assert loaded.payload["tmux_session_name"] == "HOUMAO-gpu"
    assert loaded.payload["cao"]["tmux_window_name"] == "developer-1"
    assert loaded.payload["backend_state"]["tmux_window_name"] == "developer-1"


def test_local_interactive_manifest_round_trip_uses_dedicated_backend_section(
    tmp_path: Path,
) -> None:
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_local_interactive_plan(tmp_path),
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("HOUMAO-claude"),
            backend_state={
                "turn_index": 2,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": "HOUMAO-claude",
            },
        )
    )

    path = tmp_path / "local-interactive-session.json"
    write_session_manifest(path, payload)
    loaded = load_session_manifest(path)

    assert loaded.payload["backend"] == "local_interactive"
    assert loaded.payload["local_interactive"]["turn_index"] == 2
    assert loaded.payload["local_interactive"]["role_bootstrap_applied"] is True
    assert "headless" not in loaded.payload or loaded.payload["headless"] is None


def test_houmao_manifest_round_trip_uses_dedicated_backend_section(tmp_path: Path) -> None:
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_houmao_plan(tmp_path),
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("HOUMAO-gpu"),
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
    assert loaded.payload["gateway_authority"]["attach"]["managed_agent_ref"] == "cao-gpu"
    assert loaded.payload["gateway_authority"]["control"]["terminal_id"] == "abcd1234"
    assert "cao" not in loaded.payload or loaded.payload["cao"] is None


def test_resolve_manifest_session_authority_normalizes_houmao_server_attach(tmp_path: Path) -> None:
    manifest_path = tmp_path / "houmao-session.json"
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_houmao_plan(tmp_path),
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("HOUMAO-gpu"),
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

    authority = resolve_manifest_session_authority(
        manifest_path=manifest_path,
        payload=parse_session_manifest_payload(payload, source=str(manifest_path)),
    )

    assert authority.attach.require_pair_target() == ("http://127.0.0.1:9889", "cao-gpu")
    assert authority.control.require_terminal_id() == "abcd1234"


def test_resolve_manifest_session_authority_normalizes_cao_control(tmp_path: Path) -> None:
    manifest_path = tmp_path / "cao-session.json"
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_cao_plan(tmp_path),
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("HOUMAO-gpu"),
            backend_state={
                "api_base_url": "http://localhost:9889",
                "session_name": "HOUMAO-gpu",
                "terminal_id": "term-123",
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "parsing_mode": "shadow_only",
                "turn_index": 1,
            },
        )
    )

    authority = resolve_manifest_session_authority(
        manifest_path=manifest_path,
        payload=parse_session_manifest_payload(payload, source=str(manifest_path)),
    )

    assert authority.control.require_terminal_id() == "term-123"
    assert authority.control.api_base_url == "http://localhost:9889"
    assert authority.control.profile_name == "runtime-profile"


def test_resolve_manifest_session_authority_rejects_missing_gateway_authority(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "cao-session.json"
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_cao_plan(tmp_path),
            role_name="gpu-kernel-coder",
            brain_manifest_path=tmp_path / "brain.yaml",
            **_identity_fields("HOUMAO-gpu"),
            backend_state={
                "api_base_url": "http://localhost:9889",
                "session_name": "HOUMAO-gpu",
                "terminal_id": "term-123",
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "parsing_mode": "shadow_only",
                "turn_index": 1,
            },
        )
    )
    payload["gateway_authority"] = None

    with pytest.raises(SessionManifestError, match="Start a fresh runtime session"):
        resolve_manifest_session_authority(
            manifest_path=manifest_path,
            payload=parse_session_manifest_payload(payload, source=str(manifest_path)),
        )
