from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable, Literal

import pytest
from pydantic import ValidationError

from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.registry_models import (
    LiveAgentRegistryRecordV2,
    ManagedAgentRegistryRecordV3,
    RegistryIdentityV1,
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryRuntimeV1,
    RegistryTerminalV1,
    RegistryTerminalV2,
)
from houmao.agents.realm_controller.registry_storage import (
    DEFAULT_REGISTRY_LEASE_TTL,
    LIVE_AGENT_REGISTRY_SCHEMA,
    TMUX_BACKED_REGISTRY_SENTINEL_LEASE_TTL,
    cleanup_stale_live_agent_records,
    new_registry_generation_id,
    publish_live_agent_record,
    resolve_cleanup_managed_agent_record_by_agent_id,
    resolve_global_registry_root,
    resolve_live_agent_record,
    resolve_live_agent_records_by_terminal_session_name,
    resolve_managed_agent_records_by_name,
    resolve_relaunchable_managed_agent_record_by_agent_id,
)
from houmao.agents.realm_controller.schema_validation import load_schema
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR


def _sample_record(
    *,
    agent_name: str = "HOUMAO-gpu",
    generation_id: str = "generation-1",
    now: datetime | None = None,
    lease_ttl: timedelta = DEFAULT_REGISTRY_LEASE_TTL,
) -> LiveAgentRegistryRecordV2:
    published_at = now or datetime.now(UTC)
    return LiveAgentRegistryRecordV2(
        agent_name=agent_name,
        agent_id=derive_agent_id_from_name(agent_name),
        generation_id=generation_id,
        published_at=published_at.isoformat(timespec="seconds"),
        lease_expires_at=(published_at + lease_ttl).isoformat(timespec="seconds"),
        identity=RegistryIdentityV1(backend="claude_headless", tool="claude"),
        runtime=RegistryRuntimeV1(
            manifest_path="/tmp/runtime/session/manifest.json",
            session_root="/tmp/runtime/session",
            agent_def_dir="/tmp/agents",
        ),
        terminal=RegistryTerminalV1(session_name=agent_name),
    )


def _sample_lifecycle_record(
    *,
    agent_name: str = "HOUMAO-gpu",
    generation_id: str = "generation-1",
    now: datetime | None = None,
    lease_ttl: timedelta = DEFAULT_REGISTRY_LEASE_TTL,
    lifecycle_state: Literal["active", "stopped", "relaunching", "retired"] = "active",
    relaunchable: bool = True,
    stop_reason: str | None = "operator_stop",
) -> ManagedAgentRegistryRecordV3:
    published_at = now or datetime.now(UTC)
    current_session_name = agent_name if lifecycle_state in {"active", "relaunching"} else None
    return ManagedAgentRegistryRecordV3(
        agent_name=agent_name,
        agent_id=derive_agent_id_from_name(agent_name),
        generation_id=generation_id,
        lifecycle=RegistryLifecycleV1(
            state=lifecycle_state,
            relaunchable=relaunchable,
            state_updated_at=published_at.isoformat(timespec="seconds"),
            stopped_at=(
                published_at.isoformat(timespec="seconds")
                if lifecycle_state in {"stopped", "retired"}
                else None
            ),
            stop_reason=stop_reason if lifecycle_state in {"stopped", "retired"} else None,
        ),
        identity=RegistryIdentityV1(backend="claude_headless", tool="claude"),
        runtime=RegistryRuntimeV1(
            manifest_path="/tmp/runtime/session/manifest.json",
            session_root="/tmp/runtime/session",
            agent_def_dir="/tmp/agents",
        ),
        terminal=RegistryTerminalV2(
            current_session_name=current_session_name,
            last_session_name=agent_name,
        ),
        liveness=(
            RegistryLivenessV1(
                published_at=published_at.isoformat(timespec="seconds"),
                lease_expires_at=(published_at + lease_ttl).isoformat(timespec="seconds"),
            )
            if lifecycle_state in {"active", "relaunching"}
            else None
        ),
        gateway=None,
        mailbox=None,
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
    monkeypatch.delenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, raising=False)
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
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(override_root))

    assert resolve_global_registry_root() == override_root.resolve()


def test_registry_publish_and_resolve_accepts_friendly_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    record = _sample_record(agent_name="gpu")

    published = publish_live_agent_record(record)
    resolved = resolve_live_agent_record("gpu")

    assert published.agent_id == derive_agent_id_from_name("gpu")
    assert resolved is not None
    assert resolved.agent_name == "gpu"
    assert resolved.generation_id == "generation-1"


def test_registry_loads_legacy_v2_payload_as_active_lifecycle_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    legacy_record = _sample_record(agent_name="gpu")
    record_path = registry_root / "live_agents" / legacy_record.agent_id / "record.json"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(
        json.dumps(legacy_record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    resolved = resolve_live_agent_record("gpu")

    assert resolved is not None
    assert resolved.lifecycle.state == "active"
    assert resolved.terminal.current_session_name == "gpu"
    assert resolved.terminal.last_session_name == "gpu"
    assert resolved.liveness is not None


def test_registry_resolves_exact_terminal_session_matches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    publish_live_agent_record(_sample_record(agent_name="gpu-a"))
    publish_live_agent_record(_sample_record(agent_name="gpu-b"))

    resolved = resolve_live_agent_records_by_terminal_session_name("gpu-a")

    assert len(resolved) == 1
    assert resolved[0].agent_name == "gpu-a"
    assert resolved[0].terminal.session_name == "gpu-a"


def test_registry_terminal_session_lookup_skips_expired_records(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    published_at = now - timedelta(days=2)
    publish_live_agent_record(
        _sample_record(
            agent_name="gpu",
            now=published_at,
        ),
        now=published_at,
    )

    resolved = resolve_live_agent_records_by_terminal_session_name("gpu", now=now)

    assert resolved == ()


def test_tmux_sentinel_record_resolves_after_former_lease_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    now = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    published_at = now - timedelta(days=31)
    publish_live_agent_record(
        _sample_record(
            agent_name="gpu",
            now=published_at,
            lease_ttl=TMUX_BACKED_REGISTRY_SENTINEL_LEASE_TTL,
        ),
        now=published_at,
    )

    by_name = resolve_live_agent_record("gpu", now=now)
    by_session = resolve_live_agent_records_by_terminal_session_name("gpu", now=now)

    assert by_name is not None
    assert by_name.agent_name == "gpu"
    assert len(by_session) == 1
    assert by_session[0].agent_name == "gpu"


def test_stopped_registry_record_is_relaunchable_and_not_live(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    record = _sample_lifecycle_record(agent_name="gpu", lifecycle_state="stopped")

    published = publish_live_agent_record(record)

    assert published.lifecycle.state == "stopped"
    assert resolve_live_agent_record("gpu") is None
    all_matches = resolve_managed_agent_records_by_name("gpu")
    assert len(all_matches) == 1
    assert all_matches[0].lifecycle.state == "stopped"
    relaunchable = resolve_relaunchable_managed_agent_record_by_agent_id(published.agent_id)
    assert relaunchable is not None
    assert relaunchable.lifecycle.state == "stopped"
    assert relaunchable.terminal.current_session_name is None
    assert relaunchable.terminal.last_session_name == "gpu"
    cleanup_record = resolve_cleanup_managed_agent_record_by_agent_id(published.agent_id)
    assert cleanup_record is not None
    assert cleanup_record.runtime.session_root == "/tmp/runtime/session"


def test_retired_registry_record_is_durable_but_not_relaunchable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    record = _sample_lifecycle_record(
        agent_name="gpu",
        lifecycle_state="retired",
        relaunchable=False,
    )

    published = publish_live_agent_record(record)

    assert published.lifecycle.state == "retired"
    assert resolve_live_agent_record("gpu") is None
    all_matches = resolve_managed_agent_records_by_name("gpu")
    assert len(all_matches) == 1
    assert all_matches[0].lifecycle.state == "retired"
    assert resolve_relaunchable_managed_agent_record_by_agent_id(published.agent_id) is None
    cleanup_record = resolve_cleanup_managed_agent_record_by_agent_id(published.agent_id)
    assert cleanup_record is not None
    assert cleanup_record.lifecycle.state == "retired"


def test_registry_rejects_fresh_duplicate_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    publish_live_agent_record(_sample_record(generation_id="generation-1"))

    with pytest.raises(SessionManifestError, match="ownership conflict"):
        publish_live_agent_record(_sample_record(generation_id="generation-2"))


def test_registry_allows_new_active_generation_after_stopped_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    publish_live_agent_record(
        _sample_lifecycle_record(
            agent_name="gpu",
            generation_id="generation-1",
            lifecycle_state="stopped",
        )
    )

    published = publish_live_agent_record(
        _sample_lifecycle_record(
            agent_name="gpu",
            generation_id="generation-2",
            lifecycle_state="active",
        )
    )

    assert published.lifecycle.state == "active"
    assert published.generation_id == "generation-2"
    assert published.terminal.current_session_name == "gpu"


def test_resolve_live_agent_record_returns_none_for_malformed_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    record_dir = registry_root / "live_agents" / derive_agent_id_from_name("HOUMAO-gpu")
    record_dir.mkdir(parents=True)
    (record_dir / "record.json").write_text("{not-json}\n", encoding="utf-8")

    assert resolve_live_agent_record("gpu") is None


def test_registry_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError, match="timezone-aware ISO-8601 timestamp"):
        LiveAgentRegistryRecordV2(
            agent_name="HOUMAO-gpu",
            agent_id=derive_agent_id_from_name("HOUMAO-gpu"),
            generation_id="generation-1",
            published_at="2026-03-13T12:00:00",
            lease_expires_at="2026-03-14T12:00:00",
            identity=RegistryIdentityV1(backend="claude_headless", tool="claude"),
            runtime=RegistryRuntimeV1(
                manifest_path="/tmp/runtime/session/manifest.json",
                session_root="/tmp/runtime/session",
                agent_def_dir="/tmp/agents",
            ),
            terminal=RegistryTerminalV1(session_name="HOUMAO-gpu"),
        )


@pytest.mark.parametrize(
    ("record", "match"),
    [
        (
            lambda: _sample_lifecycle_record(lifecycle_state="retired", relaunchable=True),
            "retired lifecycle records must not remain relaunchable",
        ),
        (
            lambda: ManagedAgentRegistryRecordV3(
                **{
                    **_sample_lifecycle_record(lifecycle_state="stopped").model_dump(),
                    "lifecycle": {
                        "state": "stopped",
                        "relaunchable": True,
                        "state_updated_at": "2026-03-13T12:00:00+00:00",
                        "stopped_at": None,
                        "stop_reason": "operator_stop",
                    },
                }
            ),
            "stopped_at is required",
        ),
    ],
)
def test_registry_rejects_invalid_lifecycle_shapes(
    record: Callable[[], object],
    match: str,
) -> None:
    with pytest.raises(ValidationError, match=match):
        record()


def test_registry_schema_is_packaged_and_covers_optional_gateway_and_mailbox_groups() -> None:
    schema = load_schema(LIVE_AGENT_REGISTRY_SCHEMA)

    gateway = schema["properties"]["gateway"]
    mailbox = schema["properties"]["mailbox"]

    assert gateway["anyOf"][1]["type"] == "null"
    gateway_object = schema["$defs"]["RegistryGatewayV1"]
    assert gateway_object["required"] == ["host", "port", "state_path", "protocol_version"]
    assert gateway_object["properties"]["host"]["enum"] == ["127.0.0.1", "0.0.0.0"]
    assert gateway_object["properties"]["protocol_version"]["const"] == "v1"

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
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.registry_storage.tmux_session_exists",
        lambda *, session_name: True,
    )
    live_agents_dir = registry_root / "live_agents"
    live_agents_dir.mkdir(parents=True)

    fresh_now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    expired_record = _sample_record(
        agent_name="HOUMAO-old",
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
        agent_name="HOUMAO-fresh",
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
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))

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
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
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
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    publish_live_agent_record(_sample_record())

    record_path = (
        registry_root / "live_agents" / derive_agent_id_from_name("HOUMAO-gpu") / "record.json"
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
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.registry_storage.tmux_session_exists",
        lambda *, session_name: True,
    )
    live_agents_dir = registry_root / "live_agents"
    live_agents_dir.mkdir(parents=True)

    now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    expired_record = _sample_record(
        agent_name="HOUMAO-old",
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
        agent_name="HOUMAO-fresh",
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


def test_cleanup_dry_run_reports_candidates_without_deleting(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    live_agents_dir = registry_root / "live_agents"
    live_agents_dir.mkdir(parents=True)

    now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    expired_record = _sample_record(
        agent_name="HOUMAO-old",
        generation_id=new_registry_generation_id(),
        now=now - timedelta(days=2),
    )
    expired_dir = live_agents_dir / expired_record.agent_id
    expired_dir.mkdir()
    (expired_dir / "record.json").write_text(
        json.dumps(expired_record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = cleanup_stale_live_agent_records(
        now=now,
        grace_period=timedelta(seconds=0),
        dry_run=True,
    )

    assert result.removed_agent_ids == ()
    assert result.planned_agent_ids == (expired_record.agent_id,)
    assert expired_dir.exists()
    assert result.actions == (result.actions[0],)
    assert result.actions[0].outcome == "planned"


def test_cleanup_default_tmux_probe_marks_fresh_record_stale(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    live_agents_dir = registry_root / "live_agents"
    live_agents_dir.mkdir(parents=True)

    now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    fresh_record = _sample_record(
        agent_name="HOUMAO-fresh",
        generation_id=new_registry_generation_id(),
        now=now,
    )
    fresh_dir = live_agents_dir / fresh_record.agent_id
    fresh_dir.mkdir()
    (fresh_dir / "record.json").write_text(
        json.dumps(fresh_record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.registry_storage.tmux_session_exists",
        lambda *, session_name: False,
    )

    result = cleanup_stale_live_agent_records(
        now=now,
        grace_period=timedelta(seconds=0),
        dry_run=True,
    )

    assert result.planned_agent_ids == (fresh_record.agent_id,)
    assert result.preserved_agent_ids == ()
    assert result.actions[0].reason == "local tmux liveness probe found no owning session"


def test_cleanup_default_tmux_probe_marks_sentinel_record_stale_when_tmux_dead(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    live_agents_dir = registry_root / "live_agents"
    live_agents_dir.mkdir(parents=True)

    now = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    published_at = now - timedelta(days=31)
    sentinel_record = _sample_record(
        agent_name="HOUMAO-sentinel",
        generation_id=new_registry_generation_id(),
        now=published_at,
        lease_ttl=TMUX_BACKED_REGISTRY_SENTINEL_LEASE_TTL,
    )
    sentinel_dir = live_agents_dir / sentinel_record.agent_id
    sentinel_dir.mkdir()
    (sentinel_dir / "record.json").write_text(
        json.dumps(sentinel_record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.registry_storage.tmux_session_exists",
        lambda *, session_name: False,
    )

    result = cleanup_stale_live_agent_records(
        now=now,
        grace_period=timedelta(seconds=0),
        dry_run=True,
    )

    assert result.planned_agent_ids == (sentinel_record.agent_id,)
    assert result.preserved_agent_ids == ()
    assert result.actions[0].reason == "local tmux liveness probe found no owning session"


def test_cleanup_default_tmux_probe_preserves_live_fresh_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    live_agents_dir = registry_root / "live_agents"
    live_agents_dir.mkdir(parents=True)

    now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    fresh_record = _sample_record(
        agent_name="HOUMAO-fresh",
        generation_id=new_registry_generation_id(),
        now=now,
    )
    fresh_dir = live_agents_dir / fresh_record.agent_id
    fresh_dir.mkdir()
    (fresh_dir / "record.json").write_text(
        json.dumps(fresh_record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.registry_storage.tmux_session_exists",
        lambda *, session_name: True,
    )

    result = cleanup_stale_live_agent_records(
        now=now,
        grace_period=timedelta(seconds=0),
        dry_run=True,
    )

    assert result.planned_agent_ids == ()
    assert result.preserved_agent_ids == (fresh_record.agent_id,)
    assert result.actions[0].reason == "local tmux liveness probe confirmed the owning session"


def test_cleanup_no_tmux_check_preserves_fresh_record_without_local_probe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    live_agents_dir = registry_root / "live_agents"
    live_agents_dir.mkdir(parents=True)

    now = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    fresh_record = _sample_record(
        agent_name="HOUMAO-fresh",
        generation_id=new_registry_generation_id(),
        now=now,
    )
    fresh_dir = live_agents_dir / fresh_record.agent_id
    fresh_dir.mkdir()
    (fresh_dir / "record.json").write_text(
        json.dumps(fresh_record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    def _unexpected_tmux_probe(*, session_name: str) -> bool:
        del session_name
        raise AssertionError("tmux probe should be skipped when --no-tmux-check is used")

    monkeypatch.setattr(
        "houmao.agents.realm_controller.registry_storage.tmux_session_exists",
        _unexpected_tmux_probe,
    )

    result = cleanup_stale_live_agent_records(
        now=now,
        grace_period=timedelta(seconds=0),
        dry_run=True,
        probe_local_tmux=False,
    )

    assert result.planned_agent_ids == ()
    assert result.preserved_agent_ids == (fresh_record.agent_id,)
    assert result.actions[0].reason == "lease remains fresh and local tmux checking was disabled"
