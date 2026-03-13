from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.registry_models import (
    LiveAgentRegistryRecordV1,
    RegistryIdentityV1,
    RegistryRuntimeV1,
    RegistryTerminalV1,
    derive_agent_key,
)
from houmao.agents.realm_controller.registry_storage import (
    AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR,
    DEFAULT_REGISTRY_LEASE_TTL,
    cleanup_stale_live_agent_records,
    new_registry_generation_id,
    publish_live_agent_record,
    resolve_global_registry_root,
    resolve_live_agent_record,
)


def _sample_record(
    *,
    agent_name: str = "AGENTSYS-gpu",
    generation_id: str = "generation-1",
    now: datetime | None = None,
) -> LiveAgentRegistryRecordV1:
    published_at = now or datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    return LiveAgentRegistryRecordV1(
        agent_name=agent_name,
        agent_key=derive_agent_key(agent_name),
        generation_id=generation_id,
        published_at=published_at.isoformat(timespec="seconds"),
        lease_expires_at=(published_at + DEFAULT_REGISTRY_LEASE_TTL).isoformat(timespec="seconds"),
        identity=RegistryIdentityV1(backend="claude_headless", tool="claude"),
        runtime=RegistryRuntimeV1(
            manifest_path="/tmp/runtime/session/manifest.json",
            session_root="/tmp/runtime/session",
            agent_def_dir="/tmp/agents",
        ),
        terminal=RegistryTerminalV1(session_name=agent_name),
    )


def test_default_registry_root_uses_platformdirs_home_anchor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_home = tmp_path / "home-anchor"
    fake_user_data_path = fake_home / ".local" / "share" / "houmao"
    monkeypatch.delenv(AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR, raising=False)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.registry_storage.platformdirs.user_data_path",
        lambda **kwargs: fake_user_data_path,
    )

    assert resolve_global_registry_root() == (fake_home / ".houmao" / "registry").resolve()


def test_registry_root_honors_absolute_env_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    override_root = tmp_path / "custom-registry"
    monkeypatch.setenv(AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR, str(override_root))

    assert resolve_global_registry_root() == override_root.resolve()


def test_registry_publish_and_resolve_accepts_optional_prefix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    record = _sample_record()

    published = publish_live_agent_record(record)
    resolved = resolve_live_agent_record("gpu")

    assert published.agent_key == derive_agent_key("AGENTSYS-gpu")
    assert resolved is not None
    assert resolved.agent_name == "AGENTSYS-gpu"
    assert resolved.generation_id == "generation-1"


def test_registry_rejects_fresh_duplicate_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    publish_live_agent_record(_sample_record(generation_id="generation-1"))

    with pytest.raises(SessionManifestError, match="ownership conflict"):
        publish_live_agent_record(_sample_record(generation_id="generation-2"))


def test_cleanup_removes_expired_or_malformed_live_agent_dirs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    live_agents_dir = registry_root / "live_agents"
    live_agents_dir.mkdir(parents=True)

    fresh_now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    expired_record = _sample_record(
        agent_name="AGENTSYS-old",
        generation_id=new_registry_generation_id(),
        now=fresh_now - timedelta(days=2),
    )
    expired_dir = live_agents_dir / expired_record.agent_key
    expired_dir.mkdir()
    (expired_dir / "record.json").write_text(
        json.dumps(expired_record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    malformed_dir = live_agents_dir / "malformed"
    malformed_dir.mkdir()
    (malformed_dir / "record.json").write_text("{not-json}\n", encoding="utf-8")

    fresh_record = _sample_record(
        agent_name="AGENTSYS-fresh",
        generation_id=new_registry_generation_id(),
        now=fresh_now,
    )
    fresh_dir = live_agents_dir / fresh_record.agent_key
    fresh_dir.mkdir()
    (fresh_dir / "record.json").write_text(
        json.dumps(fresh_record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = cleanup_stale_live_agent_records(
        now=fresh_now,
        grace_period=timedelta(seconds=0),
    )

    assert sorted(result.removed_agent_keys) == sorted([expired_record.agent_key, "malformed"])
    assert result.preserved_agent_keys == (fresh_record.agent_key,)
    assert not expired_dir.exists()
    assert not malformed_dir.exists()
    assert fresh_dir.exists()
