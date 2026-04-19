"""Tests for ``DiscoveredAgentIndex`` and ``RegistryDiscoveryService``."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import (
    DiscoveredAgent,
    DiscoveredAgentIndex,
    RegistryDiscoveryService,
    _summary_from_record,
)
from houmao.agents.realm_controller.registry_models import (
    LiveAgentRegistryRecordV2,
    RegistryIdentityV1,
    RegistryRuntimeV1,
    RegistryTerminalV1,
)
from houmao.agents.realm_controller.registry_storage import (
    TMUX_BACKED_REGISTRY_SENTINEL_LEASE_TTL,
)


def _make_record(
    *,
    agent_id: str = "abc123",
    agent_name: str = "HOUMAO-alpha",
    generation_id: str = "gen-1",
    tool: str = "claude",
    backend: str = "claude_headless",
    session_name: str = "HOUMAO-alpha-abc123",
    manifest_path: str = "/tmp/manifest.json",
    session_root: str = "/tmp/session",
    published_at: datetime | None = None,
    lease_expires_at: datetime | None = None,
) -> LiveAgentRegistryRecordV2:
    """Create a minimal valid registry record for testing."""

    now = datetime.now(UTC)
    return LiveAgentRegistryRecordV2(
        agent_id=agent_id,
        agent_name=agent_name,
        generation_id=generation_id,
        published_at=(published_at or now).isoformat(timespec="seconds"),
        lease_expires_at=(lease_expires_at or now + timedelta(hours=24)).isoformat(
            timespec="seconds"
        ),
        identity=RegistryIdentityV1(backend=backend, tool=tool),
        runtime=RegistryRuntimeV1(manifest_path=manifest_path, session_root=session_root),
        terminal=RegistryTerminalV1(session_name=session_name),
    )


def _make_discovered(
    **kwargs: object,
) -> DiscoveredAgent:
    """Create a DiscoveredAgent from record kwargs."""

    record = _make_record(**kwargs)  # type: ignore[arg-type]
    return DiscoveredAgent(record=record, summary=_summary_from_record(record))


# ---------------------------------------------------------------------------
# DiscoveredAgentIndex tests
# ---------------------------------------------------------------------------


class TestDiscoveredAgentIndex:
    """Tests for the in-memory agent index."""

    def test_empty_index_returns_none_for_id(self) -> None:
        idx = DiscoveredAgentIndex()
        assert idx.get_by_id("nonexistent") is None

    def test_empty_index_returns_empty_for_name(self) -> None:
        idx = DiscoveredAgentIndex()
        assert idx.get_by_name("anything") == []

    def test_empty_index_list_all_empty(self) -> None:
        idx = DiscoveredAgentIndex()
        assert idx.list_all() == []

    def test_get_by_id_returns_match(self) -> None:
        agent = _make_discovered(agent_id="abc123", agent_name="HOUMAO-alpha")
        idx = DiscoveredAgentIndex()
        idx.replace({"abc123": agent})
        assert idx.get_by_id("abc123") is agent

    def test_get_by_id_returns_none_for_miss(self) -> None:
        agent = _make_discovered(agent_id="abc123")
        idx = DiscoveredAgentIndex()
        idx.replace({"abc123": agent})
        assert idx.get_by_id("xyz999") is None

    def test_get_by_name_returns_match(self) -> None:
        agent = _make_discovered(agent_id="abc123", agent_name="HOUMAO-alpha")
        idx = DiscoveredAgentIndex()
        idx.replace({"abc123": agent})
        result = idx.get_by_name("alpha")
        assert len(result) == 1
        assert result[0] is agent

    def test_get_by_name_canonical_form(self) -> None:
        agent = _make_discovered(agent_id="abc123", agent_name="HOUMAO-alpha")
        idx = DiscoveredAgentIndex()
        idx.replace({"abc123": agent})
        result = idx.get_by_name("HOUMAO-alpha")
        assert len(result) == 1

    def test_get_by_name_returns_multiple_for_ambiguous(self) -> None:
        a1 = _make_discovered(
            agent_id="abc123",
            agent_name="HOUMAO-alpha",
            session_name="HOUMAO-alpha-abc123",
        )
        a2 = _make_discovered(
            agent_id="def456",
            agent_name="HOUMAO-alpha",
            session_name="HOUMAO-alpha-def456",
        )
        idx = DiscoveredAgentIndex()
        idx.replace({"abc123": a1, "def456": a2})
        result = idx.get_by_name("alpha")
        assert len(result) == 2

    def test_list_all_sorted_by_name(self) -> None:
        a_beta = _make_discovered(
            agent_id="b1",
            agent_name="HOUMAO-beta",
            session_name="HOUMAO-beta-b1",
        )
        a_alpha = _make_discovered(
            agent_id="a1",
            agent_name="HOUMAO-alpha",
            session_name="HOUMAO-alpha-a1",
        )
        idx = DiscoveredAgentIndex()
        idx.replace({"b1": a_beta, "a1": a_alpha})
        result = idx.list_all()
        assert [a.record.agent_name for a in result] == ["HOUMAO-alpha", "HOUMAO-beta"]

    def test_replace_clears_previous(self) -> None:
        agent = _make_discovered(agent_id="abc123")
        idx = DiscoveredAgentIndex()
        idx.replace({"abc123": agent})
        idx.replace({})
        assert idx.get_by_id("abc123") is None
        assert idx.list_all() == []


# ---------------------------------------------------------------------------
# RegistryDiscoveryService scan tests
# ---------------------------------------------------------------------------


def _write_record(registry_root: Path, record: LiveAgentRegistryRecordV2) -> None:
    """Persist a record to the test registry directory."""

    agent_dir = registry_root / "live_agents" / record.agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "record.json").write_text(
        json.dumps(record.model_dump(mode="json"), indent=2), encoding="utf-8"
    )


class TestRegistryDiscoveryScan:
    """Tests for the scan logic."""

    def _make_service(self, tmp_path: Path) -> RegistryDiscoveryService:
        """Create a service pointing at a tmp registry root."""

        config = PassiveServerConfig(runtime_root=tmp_path)
        return RegistryDiscoveryService(config)

    def test_fresh_live_agent_is_discovered(self, tmp_path: Path) -> None:
        record = _make_record(agent_id="abc123", session_name="HOUMAO-alpha-abc123")
        registry_root = tmp_path / "registry"
        _write_record(registry_root, record)

        svc = self._make_service(tmp_path)
        with (
            patch("houmao.passive_server.discovery.global_registry_paths") as mock_paths,
            patch(
                "houmao.passive_server.discovery._get_live_tmux_session_names",
                return_value={"HOUMAO-alpha-abc123"},
            ),
        ):
            from houmao.agents.realm_controller.registry_storage import GlobalRegistryPaths

            mock_paths.return_value = GlobalRegistryPaths(
                root=registry_root, live_agents_dir=registry_root / "live_agents"
            )
            svc.scan_once()

        assert svc.index.get_by_id("abc123") is not None

    def test_expired_agent_excluded(self, tmp_path: Path) -> None:
        now = datetime.now(UTC)
        record = _make_record(
            agent_id="expired1",
            session_name="HOUMAO-alpha-expired1",
            published_at=now - timedelta(hours=48),
            lease_expires_at=now - timedelta(hours=1),
        )
        registry_root = tmp_path / "registry"
        _write_record(registry_root, record)

        svc = self._make_service(tmp_path)
        with (
            patch("houmao.passive_server.discovery.global_registry_paths") as mock_paths,
            patch(
                "houmao.passive_server.discovery._get_live_tmux_session_names",
                return_value={"HOUMAO-alpha-expired1"},
            ),
        ):
            from houmao.agents.realm_controller.registry_storage import GlobalRegistryPaths

            mock_paths.return_value = GlobalRegistryPaths(
                root=registry_root, live_agents_dir=registry_root / "live_agents"
            )
            svc.scan_once()

        assert svc.index.get_by_id("expired1") is None

    def test_sentinel_agent_discovered_after_former_lease_boundaries(
        self,
        tmp_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        published_at = now - timedelta(days=31)
        record = _make_record(
            agent_id="sentinel1",
            session_name="HOUMAO-alpha-sentinel1",
            published_at=published_at,
            lease_expires_at=published_at + TMUX_BACKED_REGISTRY_SENTINEL_LEASE_TTL,
        )
        registry_root = tmp_path / "registry"
        _write_record(registry_root, record)

        svc = self._make_service(tmp_path)
        with (
            patch("houmao.passive_server.discovery.global_registry_paths") as mock_paths,
            patch(
                "houmao.passive_server.discovery._get_live_tmux_session_names",
                return_value={"HOUMAO-alpha-sentinel1"},
            ),
        ):
            from houmao.agents.realm_controller.registry_storage import GlobalRegistryPaths

            mock_paths.return_value = GlobalRegistryPaths(
                root=registry_root, live_agents_dir=registry_root / "live_agents"
            )
            svc.scan_once()

        assert svc.index.get_by_id("sentinel1") is not None

    def test_dead_tmux_session_excluded(self, tmp_path: Path) -> None:
        record = _make_record(agent_id="dead1", session_name="HOUMAO-alpha-dead1")
        registry_root = tmp_path / "registry"
        _write_record(registry_root, record)

        svc = self._make_service(tmp_path)
        with (
            patch("houmao.passive_server.discovery.global_registry_paths") as mock_paths,
            patch(
                "houmao.passive_server.discovery._get_live_tmux_session_names",
                return_value=set(),  # no live sessions
            ),
        ):
            from houmao.agents.realm_controller.registry_storage import GlobalRegistryPaths

            mock_paths.return_value = GlobalRegistryPaths(
                root=registry_root, live_agents_dir=registry_root / "live_agents"
            )
            svc.scan_once()

        assert svc.index.get_by_id("dead1") is None

    def test_malformed_record_excluded(self, tmp_path: Path) -> None:
        registry_root = tmp_path / "registry"
        agent_dir = registry_root / "live_agents" / "bad1"
        agent_dir.mkdir(parents=True)
        (agent_dir / "record.json").write_text("{invalid json", encoding="utf-8")

        svc = self._make_service(tmp_path)
        with (
            patch("houmao.passive_server.discovery.global_registry_paths") as mock_paths,
            patch(
                "houmao.passive_server.discovery._get_live_tmux_session_names",
                return_value=set(),
            ),
        ):
            from houmao.agents.realm_controller.registry_storage import GlobalRegistryPaths

            mock_paths.return_value = GlobalRegistryPaths(
                root=registry_root, live_agents_dir=registry_root / "live_agents"
            )
            svc.scan_once()

        assert svc.index.list_all() == []

    def test_tmux_unavailable_results_in_empty_index(self, tmp_path: Path) -> None:
        record = _make_record(agent_id="abc123", session_name="HOUMAO-alpha-abc123")
        registry_root = tmp_path / "registry"
        _write_record(registry_root, record)

        svc = self._make_service(tmp_path)
        with patch(
            "houmao.passive_server.discovery._get_live_tmux_session_names",
            return_value=None,
        ):
            svc.scan_once()

        assert svc.index.list_all() == []

    def test_missing_live_agents_dir_results_in_empty_index(self, tmp_path: Path) -> None:
        svc = self._make_service(tmp_path)
        registry_root = tmp_path / "registry"
        with (
            patch("houmao.passive_server.discovery.global_registry_paths") as mock_paths,
            patch(
                "houmao.passive_server.discovery._get_live_tmux_session_names",
                return_value=set(),
            ),
        ):
            from houmao.agents.realm_controller.registry_storage import GlobalRegistryPaths

            mock_paths.return_value = GlobalRegistryPaths(
                root=registry_root, live_agents_dir=registry_root / "live_agents"
            )
            svc.scan_once()

        assert svc.index.list_all() == []
