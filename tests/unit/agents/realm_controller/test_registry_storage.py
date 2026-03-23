from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.registry_models import (
    LiveAgentRegistryRecordV2,
    RegistryIdentityV1,
    RegistryRuntimeV1,
    RegistryTerminalV1,
)
from houmao.agents.realm_controller.registry_storage import (
    DEFAULT_REGISTRY_LEASE_TTL,
    LIVE_AGENT_REGISTRY_SCHEMA,
    cleanup_stale_live_agent_records,
    new_registry_generation_id,
    publish_live_agent_record,
    resolve_global_registry_root,
    resolve_live_agent_record,
)
from houmao.agents.realm_controller.schema_validation import load_schema
from houmao.owned_paths import AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR


def _sample_record(
    *,
    agent_name: str = "AGENTSYS-gpu",
    generation_id: str = "generation-1",
    now: datetime | None = None,
) -> LiveAgentRegistryRecordV2:
    published_at = now or datetime.now(UTC)
    return LiveAgentRegistryRecordV2(
        agent_name=agent_name,
        agent_id=derive_agent_id_from_name(agent_name),
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


class _SchemaInvalidDumpRecord(LiveAgentRegistryRecordV2):
    """Test-only model that emits a schema-invalid payload on dump."""

    def model_dump(self, *args: object, **kwargs: object) -> dict[str, object]:
        payload = super().model_dump(*args, **kwargs)
        payload["runtime"] = {}
        return payload


def test_default_registry_root_uses_platformdirs_home_anchor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_home = tmp_path / "home-anchor"
    fake_user_data_path = fake_home / ".local" / "share" / "houmao"
    monkeypatch.delenv(AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR, raising=False)
    monkeypatch.setattr(
        "houmao.owned_paths.platformdirs.user_data_path",
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

    assert published.agent_id == derive_agent_id_from_name("AGENTSYS-gpu")
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


def test_resolve_live_agent_record_returns_none_for_malformed_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    record_dir = registry_root / "live_agents" / derive_agent_id_from_name("AGENTSYS-gpu")
    record_dir.mkdir(parents=True)
    (record_dir / "record.json").write_text("{not-json}\n", encoding="utf-8")

    assert resolve_live_agent_record("gpu") is None


def test_registry_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError, match="timezone-aware ISO-8601 timestamp"):
        LiveAgentRegistryRecordV2(
            agent_name="AGENTSYS-gpu",
            agent_id=derive_agent_id_from_name("AGENTSYS-gpu"),
            generation_id="generation-1",
            published_at="2026-03-13T12:00:00",
            lease_expires_at="2026-03-14T12:00:00",
            identity=RegistryIdentityV1(backend="claude_headless", tool="claude"),
            runtime=RegistryRuntimeV1(
                manifest_path="/tmp/runtime/session/manifest.json",
                session_root="/tmp/runtime/session",
                agent_def_dir="/tmp/agents",
            ),
            terminal=RegistryTerminalV1(session_name="AGENTSYS-gpu"),
        )


def test_registry_schema_is_packaged_and_covers_optional_gateway_and_mailbox_groups() -> None:
    schema = load_schema(LIVE_AGENT_REGISTRY_SCHEMA)

    gateway = schema["properties"]["gateway"]
    mailbox = schema["properties"]["mailbox"]

    assert gateway["anyOf"][1]["type"] == "null"
    gateway_object = schema["$defs"]["RegistryGatewayV1"]
    assert gateway_object["required"] == ["gateway_root", "attach_path"]
    assert gateway_object["properties"]["host"]["anyOf"][1]["type"] == "null"
    assert gateway_object["properties"]["protocol_version"]["anyOf"][1]["type"] == "null"

    assert mailbox["anyOf"][1]["type"] == "null"
    mailbox_object = schema["$defs"]["RegistryMailboxFilesystemV1"]
    assert mailbox_object["required"] == [
        "transport",
        "principal_id",
        "address",
        "filesystem_root",
        "bindings_version",
    ]
    assert mailbox_object["properties"]["transport"]["const"] == "filesystem"


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
    expired_dir = live_agents_dir / expired_record.agent_id
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
    fresh_dir = live_agents_dir / fresh_record.agent_id
    fresh_dir.mkdir()
    (fresh_dir / "record.json").write_text(
        json.dumps(fresh_record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = cleanup_stale_live_agent_records(
        now=fresh_now,
        grace_period=timedelta(seconds=0),
    )

    assert sorted(result.removed_agent_ids) == sorted([expired_record.agent_id, "malformed"])
    assert result.preserved_agent_ids == (fresh_record.agent_id,)
    assert result.failed_agent_ids == ()
    assert not expired_dir.exists()
    assert not malformed_dir.exists()
    assert fresh_dir.exists()


def test_publish_cleans_up_temp_file_when_atomic_replace_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))

    def _fail_replace(self: Path, target: Path) -> Path:
        del target
        raise OSError(f"replace failed for {self}")

    monkeypatch.setattr(Path, "replace", _fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        publish_live_agent_record(_sample_record())

    live_agents_dir = tmp_path / "registry" / "live_agents"
    assert list(live_agents_dir.rglob("*.tmp")) == []


def test_publish_rejects_schema_invalid_initial_write_before_creating_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    invalid_record = _SchemaInvalidDumpRecord(**_sample_record().model_dump())

    with pytest.raises(SessionManifestError, match="schema validation failed before publish"):
        publish_live_agent_record(invalid_record)

    assert list(registry_root.rglob("record.json")) == []
    assert list(registry_root.rglob("*.tmp")) == []


def test_publish_rejects_schema_invalid_refresh_before_replacing_existing_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    publish_live_agent_record(_sample_record())

    record_path = (
        registry_root / "live_agents" / derive_agent_id_from_name("AGENTSYS-gpu") / "record.json"
    )
    original_text = record_path.read_text(encoding="utf-8")
    invalid_refresh = _SchemaInvalidDumpRecord(**_sample_record().model_dump())

    with pytest.raises(SessionManifestError, match="schema validation failed before publish"):
        publish_live_agent_record(invalid_refresh)

    assert record_path.read_text(encoding="utf-8") == original_text
    assert list(record_path.parent.glob("*.tmp")) == []


def test_cleanup_reports_failed_removals_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    live_agents_dir = registry_root / "live_agents"
    live_agents_dir.mkdir(parents=True)

    now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    expired_record = _sample_record(
        agent_name="AGENTSYS-old",
        generation_id=new_registry_generation_id(),
        now=now - timedelta(days=2),
    )
    removable_dir = live_agents_dir / expired_record.agent_id
    removable_dir.mkdir()
    (removable_dir / "record.json").write_text(
        json.dumps(expired_record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    failed_dir = live_agents_dir / "stale-failure"
    failed_dir.mkdir()
    (failed_dir / "record.json").write_text("{not-json}\n", encoding="utf-8")

    fresh_record = _sample_record(
        agent_name="AGENTSYS-fresh",
        generation_id=new_registry_generation_id(),
        now=now,
    )
    fresh_dir = live_agents_dir / fresh_record.agent_id
    fresh_dir.mkdir()
    (fresh_dir / "record.json").write_text(
        json.dumps(fresh_record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    original_rmtree = shutil.rmtree

    def _fake_rmtree(path: Path, *, ignore_errors: bool = False) -> None:
        del ignore_errors
        if Path(path).name == "stale-failure":
            raise OSError("directory busy")
        original_rmtree(path)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.registry_storage.shutil.rmtree",
        _fake_rmtree,
    )

    result = cleanup_stale_live_agent_records(
        now=now,
        grace_period=timedelta(seconds=0),
    )

    assert result.removed_agent_ids == (expired_record.agent_id,)
    assert result.preserved_agent_ids == (fresh_record.agent_id,)
    assert result.failed_agent_ids == ("stale-failure",)
    assert not removable_dir.exists()
    assert fresh_dir.exists()
    assert failed_dir.exists()
