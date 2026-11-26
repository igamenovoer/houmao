"""Tests for ``DiscoveredAgentIndex`` and ``RegistryDiscoveryService``."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from houmao.agents.launch_policy.models import LaunchPolicyProvenance
from houmao.agents.realm_controller.run_modes import mode_for_backend
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.native_surface import NativeSurfaceV1, TerminalNativeSurfaceV1
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import (
    DiscoveredAgent,
    DiscoveredAgentIndex,
    RegistryDiscoveryService,
    _summary_from_record,
)
from houmao.agents.realm_controller.registry_models import (
    ManagedAgentRegistryRecordV3,
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryMailboxesV1,
    RegistryMailboxSlotV1,
    RegistryIdentityV1,
    RegistryRuntimeV1,
    RegistryTerminalV2,
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
    native_surface: NativeSurfaceV1 | None = None,
    session_name: str = "HOUMAO-alpha-abc123",
    manifest_path: str = "/tmp/manifest.json",
    session_root: str = "/tmp/session",
    published_at: datetime | None = None,
    lease_expires_at: datetime | None = None,
) -> ManagedAgentRegistryRecordV3:
    """Create a minimal valid registry record for testing."""

    now = datetime.now(UTC)
    return ManagedAgentRegistryRecordV3(
        agent_id=agent_id,
        agent_name=agent_name,
        generation_id=generation_id,
        lifecycle=RegistryLifecycleV1(
            state="active",
            relaunchable=True,
            state_updated_at=(published_at or now).isoformat(timespec="seconds"),
        ),
        liveness=RegistryLivenessV1(
            published_at=(published_at or now).isoformat(timespec="seconds"),
            lease_expires_at=(lease_expires_at or now + timedelta(hours=24)).isoformat(
                timespec="seconds"
            ),
        ),
        mailboxes=RegistryMailboxesV1(
            offline=RegistryMailboxSlotV1(revision="offline-0", binding=None),
            online=RegistryMailboxSlotV1(revision="online-0", binding=None),
        ),
        canonical_mail_identity=None,
        mode=mode_for_backend(backend),
        native_surface=native_surface,
        identity=RegistryIdentityV1(backend=backend, tool=tool),
        runtime=RegistryRuntimeV1(manifest_path=manifest_path, session_root=session_root),
        terminal=RegistryTerminalV2(
            current_session_name=session_name, last_session_name=session_name
        ),
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


def _write_record(
    registry_root: Path,
    record: ManagedAgentRegistryRecordV3,
    *,
    observed_tool_version: str | None = None,
) -> None:
    """Persist a record to the test registry directory."""

    agent_dir = registry_root / "live_agents" / record.agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = agent_dir / "manifest.json"
    record.runtime.manifest_path = str(manifest_path)
    plan = LaunchPlan(
        backend=record.identity.backend,
        tool=record.identity.tool,
        executable="claude",
        args=["-p"],
        working_directory=agent_dir,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=agent_dir / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_append_system_prompt", role_name="demo", prompt=""
        ),
        launch_policy_provenance=(
            LaunchPolicyProvenance(
                requested_operator_prompt_mode="unattended",
                detected_tool_version=observed_tool_version,
                selected_strategy_id="test",
                selection_source="registry",
            )
            if observed_tool_version is not None
            else None
        ),
    )
    write_session_manifest(
        manifest_path,
        build_session_manifest_payload(
            SessionManifestRequest(
                launch_plan=plan,
                role_name="demo",
                brain_manifest_path=agent_dir / "brain.json",
                backend_state={},
                agent_id=record.agent_id,
                agent_name=record.agent_name,
                tmux_session_name=record.terminal.session_name,
                registry_generation_id=record.generation_id,
            )
        ),
    )
    (agent_dir / "record.json").write_text(
        json.dumps(record.model_dump(mode="json"), indent=2), encoding="utf-8"
    )


class TestRegistryDiscoveryScan:
    """Tests for the scan logic."""

    def _make_service(
        self,
        tmp_path: Path,
        *,
        registry_root: Path | None = None,
    ) -> RegistryDiscoveryService:
        """Create a service pointing at a tmp registry root."""

        config = PassiveServerConfig(
            runtime_root=tmp_path / "runtime",
            registry_root=registry_root or tmp_path / "registry",
        )
        return RegistryDiscoveryService(config)

    def test_fresh_live_agent_is_discovered(self, tmp_path: Path) -> None:
        record = _make_record(agent_id="abc123", session_name="HOUMAO-alpha-abc123")
        registry_root = tmp_path / "registry"
        _write_record(registry_root, record, observed_tool_version="2.1.296")

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

        discovered = svc.index.get_by_id("abc123")
        assert discovered is not None
        assert discovered.summary.mode == "headless"
        assert discovered.observed_tool_version == "2.1.296"

    def test_manifest_mode_mismatch_excludes_live_record(self, tmp_path: Path) -> None:
        record = _make_record()
        registry_root = tmp_path / "registry"
        _write_record(registry_root, record)
        path = registry_root / "live_agents" / record.agent_id / "record.json"
        payload = json.loads(path.read_text())
        payload.update(mode="tui", identity={"backend": "local_interactive", "tool": "claude"})
        path.write_text(json.dumps(payload))
        svc = self._make_service(tmp_path)
        with patch(
            "houmao.passive_server.discovery._get_live_tmux_session_names",
            return_value={record.terminal.session_name},
        ):
            svc.scan_once()
        assert svc.index.get_by_id(record.agent_id) is None

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

    def test_hermes_discovery_does_not_require_a_live_tmux_view(self, tmp_path: Path) -> None:
        """Keep exact published daemon control discoverable after the TUI exits."""

        record = _make_record(
            agent_id="hermes-agent",
            agent_name="HOUMAO-hermes",
            session_name="HOUMAO-hermes-pane",
            tool="hermes",
            backend="hermes_tui",
            native_surface=TerminalNativeSurfaceV1(tmux_session_name="HOUMAO-hermes-pane"),
        )
        _write_record(tmp_path / "registry", record)
        svc = self._make_service(tmp_path)
        with patch("houmao.passive_server.discovery._get_live_tmux_session_names") as tmux:
            svc.scan_once()

        tmux.assert_not_called()
        assert svc.index.get_by_id("hermes-agent") is not None

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

    def test_custom_registry_root_controls_discovery(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        configured_registry_root = tmp_path / "configured-registry"
        ambient_registry_root = tmp_path / "ambient-registry"
        monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(ambient_registry_root))
        configured_record = _make_record(
            agent_id="configured1",
            agent_name="HOUMAO-configured",
            session_name="HOUMAO-configured-configured1",
        )
        ambient_record = _make_record(
            agent_id="ambient1",
            agent_name="HOUMAO-ambient",
            session_name="HOUMAO-ambient-ambient1",
        )
        _write_record(configured_registry_root, configured_record)
        _write_record(ambient_registry_root, ambient_record)
        svc = self._make_service(tmp_path, registry_root=configured_registry_root)

        with patch(
            "houmao.passive_server.discovery._get_live_tmux_session_names",
            return_value={
                "HOUMAO-configured-configured1",
                "HOUMAO-ambient-ambient1",
            },
        ):
            svc.scan_once()

        assert svc.index.get_by_id("configured1") is not None
        assert svc.index.get_by_id("ambient1") is None

    def test_each_record_uses_its_saved_socket_when_default_is_unavailable(
        self, tmp_path: Path
    ) -> None:
        """A default-server failure cannot hide an agent on its explicit server."""

        registry_root = tmp_path / "registry"
        live = _make_record(agent_id="owner1", session_name="same-name")
        live.terminal.socket_path = "/owner/first.sock"
        absent = _make_record(agent_id="owner2", session_name="same-name")
        absent.terminal.socket_path = "/owner/second.sock"
        _write_record(registry_root, live)
        _write_record(registry_root, absent)
        calls: list[str | None] = []

        def sessions(socket_path: str | None = None) -> set[str] | None:
            """Return independent native liveness for each server."""

            calls.append(socket_path)
            if socket_path is None:
                return None
            return {"same-name"} if socket_path == "/owner/first.sock" else set()

        svc = self._make_service(tmp_path)
        with patch(
            "houmao.passive_server.discovery._get_live_tmux_session_names", side_effect=sessions
        ):
            svc.scan_once()
        assert svc.index.get_by_id("owner1") is not None
        assert svc.index.get_by_id("owner2") is None
        assert calls == ["/owner/first.sock", "/owner/second.sock"]
