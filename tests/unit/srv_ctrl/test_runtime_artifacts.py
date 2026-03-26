from __future__ import annotations

import json
from pathlib import Path

import pytest

from houmao.agents.realm_controller.agent_identity import (
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    derive_agent_id_from_name,
    normalize_agent_identity_name,
)
from houmao.agents.realm_controller.gateway_storage import (
    AGENT_GATEWAY_ATTACH_PATH_ENV_VAR,
    AGENT_GATEWAY_ROOT_ENV_VAR,
    load_attach_contract,
    load_gateway_status,
)
from houmao.srv_ctrl.commands.runtime_artifacts import materialize_delegated_launch


def test_materialize_delegated_launch_writes_houmao_runtime_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    published: dict[str, object] = {}
    published_env: dict[str, str] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.runtime_artifacts.publish_live_agent_record",
        lambda record: published.setdefault("record", record),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.runtime_artifacts.set_tmux_session_environment",
        lambda *, session_name, env_vars: published_env.update(
            {"session_name": session_name, **env_vars}
        ),
    )

    manifest_path, session_root, canonical_agent_name, agent_id = materialize_delegated_launch(
        runtime_root=tmp_path,
        api_base_url="http://127.0.0.1:9889",
        session_name="cao-gpu",
        terminal_id="abcd1234",
        tmux_window_name="developer-1",
        provider="codex",
        agent_profile="gpu-kernel-coder",
        working_directory=tmp_path,
    )

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_agent_name = normalize_agent_identity_name("cao-gpu").canonical_name

    assert session_root == manifest_path.parent
    assert canonical_agent_name == expected_agent_name
    assert agent_id == derive_agent_id_from_name(expected_agent_name)
    assert manifest_payload["schema_version"] == 4
    assert manifest_payload["backend"] == "houmao_server_rest"
    assert manifest_payload["runtime"]["session_id"] == session_root.name
    assert manifest_payload["runtime"]["agent_def_dir"] == str(session_root / "agent_def")
    assert manifest_payload["houmao_server"]["api_base_url"] == "http://127.0.0.1:9889"
    assert manifest_payload["houmao_server"]["session_name"] == "cao-gpu"
    assert manifest_payload["houmao_server"]["terminal_id"] == "abcd1234"
    assert manifest_payload["houmao_server"]["tmux_window_name"] == "developer-1"
    assert manifest_payload["registry_generation_id"]
    assert manifest_payload["registry_launch_authority"] == "external"
    assert (
        session_root / "agent_def" / "roles" / "gpu-kernel-coder" / "system-prompt.md"
    ).is_file()
    assert published_env["session_name"] == "cao-gpu"
    assert (
        Path(str(published_env[AGENT_MANIFEST_PATH_ENV_VAR])).resolve() == manifest_path.resolve()
    )
    assert published_env[AGENT_ID_ENV_VAR] == agent_id
    assert Path(str(published_env[AGENT_GATEWAY_ATTACH_PATH_ENV_VAR])).is_file()
    assert Path(str(published_env[AGENT_GATEWAY_ROOT_ENV_VAR])).is_dir()
    attach_contract = load_attach_contract(
        Path(str(published_env[AGENT_GATEWAY_ATTACH_PATH_ENV_VAR]))
    )
    gateway_state = load_gateway_status(
        Path(str(published_env[AGENT_GATEWAY_ROOT_ENV_VAR])) / "state.json"
    )
    assert attach_contract.backend == "houmao_server_rest"
    assert attach_contract.backend_metadata.api_base_url == "http://127.0.0.1:9889"
    assert attach_contract.backend_metadata.session_name == "cao-gpu"
    assert gateway_state.gateway_health == "not_attached"

    record = published["record"]
    assert getattr(record, "identity").backend == "houmao_server_rest"
    assert getattr(record, "runtime").manifest_path == str(manifest_path)
    assert getattr(record, "runtime").session_root == str(session_root)
