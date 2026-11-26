"""Tests for ``AgentTuiObserver`` and ``TuiObservationService``."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from houmao.agents.realm_controller.backends.tmux_runtime import TmuxCommandError, TmuxPaneRecord
from houmao.agents.realm_controller.native_surface import TerminalNativeSurfaceV1
from houmao.execution.tmux import TmuxCommandResult, TmuxServer, tmux_server_scope
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import (
    DiscoveredAgent,
    RegistryDiscoveryService,
    _summary_from_record,
)
from houmao.passive_server.models import (
    AgentTuiDetailResponse,
    AgentTuiHistoryResponse,
    AgentTuiStateResponse,
)
from houmao.passive_server.observation import (
    AgentTuiObserver,
    TuiObservationService,
)
from houmao.server.models import HoumaoErrorDetail, HoumaoParsedSurface
from houmao.server.tui.parser import OfficialParseResult
from houmao.server.tui.process import PaneProcessInspection
from houmao.server.tui.transport import ResolvedTmuxTarget
from tests.unit.passive_server.test_discovery import _make_record


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_observer(
    *,
    agent_id: str = "abc123",
    agent_name: str = "HOUMAO-alpha",
    tool: str = "claude",
    session_name: str = "HOUMAO-alpha-abc123",
    observed_version: str | None = "2.1.296 (Claude Code)",
    tmux_socket_path: str | None = "/example/owner.sock",
) -> AgentTuiObserver:
    """Create an observer for testing."""

    return AgentTuiObserver(
        agent_id=agent_id,
        agent_name=agent_name,
        tool=tool,
        session_name=session_name,
        observed_version=observed_version,
        tmux_socket_path=tmux_socket_path,
    )


def _stub_tmux_target() -> ResolvedTmuxTarget:
    """Create a minimal resolved tmux target."""

    pane = TmuxPaneRecord(
        session_name="HOUMAO-alpha-abc123",
        window_id="@0",
        window_index="0",
        window_name="main",
        pane_index="0",
        pane_id="%0",
        pane_pid=12345,
        pane_active=True,
        pane_dead=False,
    )
    return ResolvedTmuxTarget(pane=pane)


def _stub_process_up() -> PaneProcessInspection:
    """Process inspection: TUI is up."""

    return PaneProcessInspection(
        process_state="tui_up",
        matched_process_names=("claude",),
        matched_processes=(),
    )


def _stub_process_down() -> PaneProcessInspection:
    """Process inspection: TUI is down."""

    return PaneProcessInspection(
        process_state="tui_down",
        matched_process_names=(),
        matched_processes=(),
    )


def _stub_parsed_surface() -> HoumaoParsedSurface:
    """Minimal valid parsed surface."""

    return HoumaoParsedSurface(
        parser_family="claude",
        availability="available",
        business_state="ready_for_input",
        input_mode="accepting",
        ui_context="main",
        normalized_projection_text="$",
        dialog_text="$",
        dialog_head="$",
        dialog_tail="$",
    )


def _stub_parse_result_ok() -> OfficialParseResult:
    """Parse result: success."""

    return OfficialParseResult(
        parsed_surface=_stub_parsed_surface(),
        parse_error=None,
    )


def _stub_parse_result_error() -> OfficialParseResult:
    """Parse result: error."""

    return OfficialParseResult(
        parsed_surface=None,
        parse_error=HoumaoErrorDetail(kind="parse_error", message="Bad parse"),
    )


def _agent(
    agent_id: str = "abc123",
    agent_name: str = "HOUMAO-alpha",
    session_name: str = "HOUMAO-alpha-abc123",
) -> DiscoveredAgent:
    """Create a DiscoveredAgent for test injection."""

    record = _make_record(
        agent_id=agent_id,
        agent_name=agent_name,
        session_name=session_name,
        backend="local_interactive",
        native_surface=TerminalNativeSurfaceV1(tmux_session_name=session_name, pane_id="%4"),
    )
    return DiscoveredAgent(record=record, summary=_summary_from_record(record))


# ===========================================================================
# AgentTuiObserver tests
# ===========================================================================


class TestObserverSuccessfulPollCycle:
    """Successful poll cycle produces parsed state."""

    def test_diagnostics_available_after_successful_poll(self) -> None:
        obs = _make_observer()
        with (
            patch("houmao.passive_server.observation.tmux_session_exists", return_value=True),
            patch.object(
                obs.m_transport_resolver, "resolve_target", return_value=_stub_tmux_target()
            ),
            patch.object(obs.m_process_inspector, "inspect", return_value=_stub_process_up()),
            patch.object(
                obs.m_transport_resolver, "capture_text", return_value="$ prompt text here"
            ),
            patch.object(obs.m_parser_adapter, "supports_tool", return_value=True),
            patch.object(obs.m_parser_adapter, "capture_baseline", return_value=0),
            patch.object(obs.m_parser_adapter, "parse", return_value=_stub_parse_result_ok()),
        ):
            obs.poll_cycle()

        state = obs.current_state()
        assert state.diagnostics.availability == "available"
        assert state.diagnostics.transport_state == "tmux_up"
        assert state.diagnostics.process_state == "tui_up"
        assert state.diagnostics.parse_status == "parsed"

    def test_detail_includes_probe_and_parsed_surface(self) -> None:
        obs = _make_observer()
        with (
            patch("houmao.passive_server.observation.tmux_session_exists", return_value=True),
            patch.object(
                obs.m_transport_resolver, "resolve_target", return_value=_stub_tmux_target()
            ),
            patch.object(obs.m_process_inspector, "inspect", return_value=_stub_process_up()),
            patch.object(obs.m_transport_resolver, "capture_text", return_value="$ prompt text"),
            patch.object(obs.m_parser_adapter, "supports_tool", return_value=True),
            patch.object(obs.m_parser_adapter, "capture_baseline", return_value=0),
            patch.object(obs.m_parser_adapter, "parse", return_value=_stub_parse_result_ok()),
        ):
            obs.poll_cycle()

        detail = obs.current_detail()
        assert detail.probe_snapshot is not None
        assert detail.parsed_surface is not None
        assert detail.parsed_surface.parser_family == "claude"

    @pytest.mark.parametrize(
        ("observed_version", "qualified"),
        [("2.0.99", False), (None, False), ("dev-build", False), ("2.1.1", True), ("9.0.0", True)],
    )
    def test_poll_applies_discovered_version_to_parser(
        self, observed_version: str | None, qualified: bool
    ) -> None:
        """Passive polling shares parse provenance and retains its early version gate."""

        observer = _make_observer(tool="kimi", observed_version=observed_version)
        with (
            patch(
                "houmao.passive_server.observation.tmux_session_exists", return_value=True
            ) as probe,
            patch.object(
                observer.m_transport_resolver, "resolve_target", return_value=_stub_tmux_target()
            ),
            patch.object(observer.m_process_inspector, "inspect", return_value=_stub_process_up()),
            patch.object(observer.m_transport_resolver, "capture_text", return_value=""),
            patch.object(
                observer.m_parser_adapter, "parse", wraps=observer.m_parser_adapter.parse
            ) as parse,
        ):
            observer.poll_cycle()

        detail = observer.current_detail()
        if qualified:
            assert detail.diagnostics.availability == "available"
            assert detail.parsed_surface is not None
            assert detail.parsed_surface.parser_preset_version == "2.1.x"
            parse.assert_called_once_with(
                tool="kimi", output_text="", baseline_pos=0, detector_version="2.1.x"
            )
        else:
            assert detail.diagnostics.parse_error is not None
            assert detail.diagnostics.parse_error.kind == "unsupported_tool_version"
            assert detail.parsed_surface is None
            probe.assert_not_called()
            parse.assert_not_called()


class TestObserverTmuxMissing:
    """Poll cycle with dead tmux session records transport error."""

    def test_records_tmux_missing(self) -> None:
        obs = _make_observer()
        with patch("houmao.passive_server.observation.tmux_session_exists", return_value=False):
            obs.poll_cycle()

        state = obs.current_state()
        assert state.diagnostics.availability == "unavailable"
        assert state.diagnostics.transport_state == "tmux_missing"

    @pytest.mark.parametrize("stderr", ["", "Permission denied"])
    def test_checked_preflight_failure_records_error_and_retries(
        self, monkeypatch: pytest.MonkeyPatch, stderr: str
    ) -> None:
        obs = _make_observer()
        replies = iter([(23, stderr), (1, "no server running on /example/owner.sock")])

        def _command(
            server: TmuxServer,
            args: Sequence[str],
            *,
            sensitive: bool = False,
            no_start: bool = False,
        ) -> TmuxCommandResult:
            assert server.socket_path == "/example/owner.sock"
            assert tuple(args) == ("list-sessions", "-F", "#{session_name}")
            status, message = next(replies)
            return TmuxCommandResult(tuple(args), status, "", message)

        monkeypatch.setattr(TmuxServer, "command", _command)
        obs.poll_cycle()

        diagnostics = obs.current_state().diagnostics
        assert obs.observed_at_utc is not None
        assert diagnostics.availability == "unavailable"
        assert diagnostics.transport_state == "probe_error"
        assert diagnostics.probe_error is not None
        assert "status 23" in diagnostics.probe_error.message
        obs.poll_cycle()

        diagnostics = obs.current_state().diagnostics
        assert diagnostics.transport_state == "tmux_missing"
        assert diagnostics.probe_error is None

    def test_missing_socket_does_not_probe_enclosing_server(self) -> None:
        obs = _make_observer(tmux_socket_path=None)
        with (
            tmux_server_scope("/example/enclosing.sock"),
            patch("houmao.passive_server.observation.tmux_session_exists") as probe,
        ):
            obs.poll_cycle()

        probe.assert_not_called()
        diagnostics = obs.current_state().diagnostics
        assert diagnostics.transport_state == "probe_error"
        assert diagnostics.probe_error is not None
        assert "saved tmux socket" in diagnostics.probe_error.message

    def test_tmux_resolve_error(self) -> None:
        obs = _make_observer()
        with (
            patch("houmao.passive_server.observation.tmux_session_exists", return_value=True),
            patch.object(
                obs.m_transport_resolver,
                "resolve_target",
                side_effect=TmuxCommandError("no panes"),
            ),
        ):
            obs.poll_cycle()

        state = obs.current_state()
        assert state.diagnostics.availability == "unavailable"
        assert state.diagnostics.transport_state == "probe_error"


class TestObserverProcessDown:
    """Poll cycle with TUI process down records process state."""

    def test_records_tui_down(self) -> None:
        obs = _make_observer()
        with (
            patch("houmao.passive_server.observation.tmux_session_exists", return_value=True),
            patch.object(
                obs.m_transport_resolver, "resolve_target", return_value=_stub_tmux_target()
            ),
            patch.object(obs.m_process_inspector, "inspect", return_value=_stub_process_down()),
        ):
            obs.poll_cycle()

        state = obs.current_state()
        assert state.diagnostics.availability == "tui_down"
        assert state.diagnostics.process_state == "tui_down"
        assert state.diagnostics.parse_status == "skipped_tui_down"


class TestObserverParseError:
    """Poll cycle with parse error records parse status."""

    def test_records_parse_error(self) -> None:
        obs = _make_observer()
        with (
            patch("houmao.passive_server.observation.tmux_session_exists", return_value=True),
            patch.object(
                obs.m_transport_resolver, "resolve_target", return_value=_stub_tmux_target()
            ),
            patch.object(obs.m_process_inspector, "inspect", return_value=_stub_process_up()),
            patch.object(obs.m_transport_resolver, "capture_text", return_value="some text"),
            patch.object(obs.m_parser_adapter, "supports_tool", return_value=True),
            patch.object(obs.m_parser_adapter, "capture_baseline", return_value=0),
            patch.object(obs.m_parser_adapter, "parse", return_value=_stub_parse_result_error()),
        ):
            obs.poll_cycle()

        state = obs.current_state()
        assert state.diagnostics.parse_status == "parse_error"
        detail = obs.current_detail()
        assert detail.diagnostics.parse_error is not None


class TestObserverStateAccessors:
    """current_state, current_detail, and history accessors."""

    def test_current_state_returns_compact(self) -> None:
        obs = _make_observer()
        state = obs.current_state()
        assert isinstance(state, AgentTuiStateResponse)
        assert state.agent_id == "abc123"
        assert state.agent_name == "HOUMAO-alpha"
        assert state.diagnostics is not None
        assert state.surface is not None
        assert state.turn is not None
        assert state.last_turn is not None
        assert state.stability is not None

    def test_current_detail_returns_full(self) -> None:
        obs = _make_observer()
        detail = obs.current_detail()
        assert isinstance(detail, AgentTuiDetailResponse)
        assert detail.agent_id == "abc123"
        # Before any poll cycle, probe_snapshot and parsed_surface are None
        assert detail.probe_snapshot is None
        assert detail.parsed_surface is None

    def test_history_empty_initially(self) -> None:
        obs = _make_observer()
        history = obs.history()
        assert isinstance(history, AgentTuiHistoryResponse)
        assert history.agent_id == "abc123"
        assert history.entries == []

    def test_history_respects_limit(self) -> None:
        obs = _make_observer()
        # Simulate multiple poll cycles to generate transitions
        with (
            patch("houmao.passive_server.observation.tmux_session_exists", return_value=True),
            patch.object(
                obs.m_transport_resolver, "resolve_target", return_value=_stub_tmux_target()
            ),
            patch.object(obs.m_process_inspector, "inspect", return_value=_stub_process_up()),
            patch.object(obs.m_transport_resolver, "capture_text", return_value="$ prompt"),
            patch.object(obs.m_parser_adapter, "supports_tool", return_value=True),
            patch.object(obs.m_parser_adapter, "capture_baseline", return_value=0),
            patch.object(obs.m_parser_adapter, "parse", return_value=_stub_parse_result_ok()),
        ):
            # Run several cycles to accumulate transitions
            for _ in range(5):
                obs.poll_cycle()

        all_history = obs.history(limit=100)
        limited_history = obs.history(limit=1)
        assert len(limited_history.entries) <= 1
        assert len(limited_history.entries) <= len(all_history.entries)

    def test_history_most_recent_first(self) -> None:
        obs = _make_observer()
        with (
            patch("houmao.passive_server.observation.tmux_session_exists", return_value=True),
            patch.object(
                obs.m_transport_resolver, "resolve_target", return_value=_stub_tmux_target()
            ),
            patch.object(obs.m_process_inspector, "inspect", return_value=_stub_process_up()),
            patch.object(obs.m_transport_resolver, "capture_text", return_value="$ prompt"),
            patch.object(obs.m_parser_adapter, "supports_tool", return_value=True),
            patch.object(obs.m_parser_adapter, "capture_baseline", return_value=0),
            patch.object(obs.m_parser_adapter, "parse", return_value=_stub_parse_result_ok()),
        ):
            for _ in range(3):
                obs.poll_cycle()

        history = obs.history()
        if len(history.entries) >= 2:
            # Most recent should be first
            assert history.entries[0].recorded_at_utc >= history.entries[-1].recorded_at_utc


# ===========================================================================
# TuiObservationService tests
# ===========================================================================


class TestObservationServiceReconciliation:
    """Observer creation/removal based on discovery index."""

    def test_creates_observer_for_discovered_agent(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(
            api_base_url="http://127.0.0.1:19891",
            runtime_root=tmp_path,
        )
        discovery = RegistryDiscoveryService(config)
        svc = TuiObservationService(discovery=discovery, config=config)

        agent = _agent(agent_id="abc123")
        discovery.m_index.replace({"abc123": agent})

        svc._reconcile_observers(discovery.index.list_all())
        assert svc.get_observer("abc123") is not None

    def test_removes_observer_when_agent_disappears(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(
            api_base_url="http://127.0.0.1:19891",
            runtime_root=tmp_path,
        )
        discovery = RegistryDiscoveryService(config)
        svc = TuiObservationService(discovery=discovery, config=config)

        agent = _agent(agent_id="abc123")
        discovery.m_index.replace({"abc123": agent})
        svc._reconcile_observers(discovery.index.list_all())
        assert svc.get_observer("abc123") is not None

        # Agent disappears
        discovery.m_index.replace({})
        svc._reconcile_observers(discovery.index.list_all())
        assert svc.get_observer("abc123") is None

    def test_keeps_existing_observer(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(
            api_base_url="http://127.0.0.1:19891",
            runtime_root=tmp_path,
        )
        discovery = RegistryDiscoveryService(config)
        svc = TuiObservationService(discovery=discovery, config=config)

        agent = _agent(agent_id="abc123")
        discovery.m_index.replace({"abc123": agent})
        svc._reconcile_observers(discovery.index.list_all())
        observer_ref = svc.get_observer("abc123")

        # Reconcile again — same agent should keep same observer
        svc._reconcile_observers(discovery.index.list_all())
        assert svc.get_observer("abc123") is observer_ref

    def test_selects_tracker_using_discovered_tool_version(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(runtime_root=tmp_path)
        svc = TuiObservationService(discovery=RegistryDiscoveryService(config), config=config)
        agent = replace(_agent(), observed_tool_version="2.1.296")

        svc._reconcile_observers([agent])

        observer = svc.get_observer(agent.record.agent_id)
        assert observer is not None
        assert observer.m_tracker_session is not None
        assert observer.m_tracker_session.detector_version == "2.1.x"

    def test_replaces_tracker_for_new_generation_of_same_agent(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(runtime_root=tmp_path)
        svc = TuiObservationService(discovery=RegistryDiscoveryService(config), config=config)
        agent = _agent()
        svc._reconcile_observers([agent])
        old = svc.get_observer(agent.record.agent_id, generation_id=agent.record.generation_id)
        assert old is not None
        record = agent.record.model_copy(update={"generation_id": "replaced"})
        svc._reconcile_observers(
            [DiscoveredAgent(record=record, summary=_summary_from_record(record))]
        )
        assert svc.get_observer(record.agent_id, generation_id=agent.record.generation_id) is None
        new = svc.get_observer(record.agent_id, generation_id="replaced")
        assert new is not None and new is not old

    def test_replaces_tracker_when_saved_version_evidence_changes(self, tmp_path: Path) -> None:
        """The same observed generation uses its latest recorded version evidence."""

        config = PassiveServerConfig(runtime_root=tmp_path)
        service = TuiObservationService(discovery=RegistryDiscoveryService(config), config=config)
        agent = replace(_agent(), observed_tool_version="2.1.296")
        service._reconcile_observers([agent])
        before = service.get_observer(
            agent.record.agent_id, generation_id=agent.record.generation_id
        )
        assert before is not None and before.m_tracker_session is not None

        service._reconcile_observers([replace(agent, observed_tool_version="2.1.295")])

        after = service.get_observer(
            agent.record.agent_id, generation_id=agent.record.generation_id
        )
        assert after is not None and after is not before
        diagnostics = after.current_detail().diagnostics
        assert diagnostics.parse_error is not None
        assert diagnostics.parse_error.kind == "unsupported_tool_version"

    def test_replaces_tracker_when_saved_socket_changes(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(runtime_root=tmp_path)
        svc = TuiObservationService(discovery=RegistryDiscoveryService(config), config=config)
        agent = _agent()
        agent.record.terminal.socket_path = "/example/old.sock"
        svc._reconcile_observers([agent])
        old = svc.get_observer(agent.record.agent_id)
        assert old is not None

        record = agent.record.model_copy(deep=True)
        record.terminal.socket_path = "/example/new.sock"
        svc._reconcile_observers(
            [DiscoveredAgent(record=record, summary=_summary_from_record(record))]
        )

        new = svc.get_observer(record.agent_id, generation_id=agent.record.generation_id)
        assert new is not None and new is not old
        assert new.m_tmux_socket_path == "/example/new.sock"


class TestObservationServicePollLoop:
    """Polling loop exception isolation."""

    def test_poll_loop_survives_observer_failure(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(
            api_base_url="http://127.0.0.1:19891",
            runtime_root=tmp_path,
        )
        discovery = RegistryDiscoveryService(config)
        svc = TuiObservationService(discovery=discovery, config=config)

        # Create two agents and their observers
        a1 = _agent(agent_id="a1", agent_name="HOUMAO-alpha", session_name="s1")
        a2 = _agent(agent_id="a2", agent_name="HOUMAO-beta", session_name="s2")
        discovery.m_index.replace({"a1": a1, "a2": a2})
        svc._reconcile_observers(discovery.index.list_all())

        obs1 = svc.get_observer("a1")
        obs2 = svc.get_observer("a2")
        assert obs1 is not None
        assert obs2 is not None

        # Make observer a1 raise, but a2 should still be polled
        with (
            patch.object(obs1, "poll_cycle", side_effect=RuntimeError("boom")),
            patch.object(obs2, "poll_cycle") as mock_poll_2,
        ):
            svc._poll_all_observers()  # should not raise

        mock_poll_2.assert_called_once()

    def test_get_observer_returns_none_for_unknown(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(
            api_base_url="http://127.0.0.1:19891",
            runtime_root=tmp_path,
        )
        discovery = RegistryDiscoveryService(config)
        svc = TuiObservationService(discovery=discovery, config=config)
        assert svc.get_observer("nonexistent") is None


# ===========================================================================
# Service-level agent_state / agent_state_detail / agent_history tests
# ===========================================================================


class TestAgentStateServiceMethod:
    """agent_state() service method."""

    def test_success_returns_compact_state(self, tmp_path: Path) -> None:
        from houmao.passive_server.service import PassiveServerService

        svc = PassiveServerService(
            config=PassiveServerConfig(
                api_base_url="http://127.0.0.1:19891",
                runtime_root=tmp_path,
            )
        )
        agent = _agent(agent_id="abc123")
        svc.m_discovery.m_index.replace({"abc123": agent})

        # Create an observer via reconciliation
        svc.m_observation._reconcile_observers(svc.m_discovery.index.list_all())

        result = svc.agent_state("abc123")
        assert isinstance(result, AgentTuiStateResponse)
        assert result.agent_id == "abc123"

    def test_not_found_returns_404(self, tmp_path: Path) -> None:
        from houmao.passive_server.service import PassiveServerService

        svc = PassiveServerService(
            config=PassiveServerConfig(
                api_base_url="http://127.0.0.1:19891",
                runtime_root=tmp_path,
            )
        )
        result = svc.agent_state("nonexistent")
        assert isinstance(result, tuple)
        assert result[0] == 404

    def test_no_observer_returns_503(self, tmp_path: Path) -> None:
        from houmao.passive_server.service import PassiveServerService

        svc = PassiveServerService(
            config=PassiveServerConfig(
                api_base_url="http://127.0.0.1:19891",
                runtime_root=tmp_path,
            )
        )
        agent = _agent(agent_id="abc123")
        svc.m_discovery.m_index.replace({"abc123": agent})
        # Don't reconcile — no observer exists

        result = svc.agent_state("abc123")
        assert isinstance(result, tuple)
        assert result[0] == 503


class TestAgentStateDetailServiceMethod:
    """agent_state_detail() service method."""

    def test_success_returns_detail(self, tmp_path: Path) -> None:
        from houmao.passive_server.service import PassiveServerService

        svc = PassiveServerService(
            config=PassiveServerConfig(
                api_base_url="http://127.0.0.1:19891",
                runtime_root=tmp_path,
            )
        )
        agent = _agent(agent_id="abc123")
        svc.m_discovery.m_index.replace({"abc123": agent})
        svc.m_observation._reconcile_observers(svc.m_discovery.index.list_all())

        result = svc.agent_state_detail("abc123")
        assert isinstance(result, AgentTuiDetailResponse)

    def test_not_found_returns_404(self, tmp_path: Path) -> None:
        from houmao.passive_server.service import PassiveServerService

        svc = PassiveServerService(
            config=PassiveServerConfig(
                api_base_url="http://127.0.0.1:19891",
                runtime_root=tmp_path,
            )
        )
        result = svc.agent_state_detail("nonexistent")
        assert isinstance(result, tuple)
        assert result[0] == 404


class TestAgentHistoryServiceMethod:
    """agent_history() service method."""

    def test_success_returns_history(self, tmp_path: Path) -> None:
        from houmao.passive_server.service import PassiveServerService

        svc = PassiveServerService(
            config=PassiveServerConfig(
                api_base_url="http://127.0.0.1:19891",
                runtime_root=tmp_path,
            )
        )
        agent = _agent(agent_id="abc123")
        svc.m_discovery.m_index.replace({"abc123": agent})
        svc.m_observation._reconcile_observers(svc.m_discovery.index.list_all())

        result = svc.agent_history("abc123")
        assert isinstance(result, AgentTuiHistoryResponse)
        assert result.agent_id == "abc123"

    def test_not_found_returns_404(self, tmp_path: Path) -> None:
        from houmao.passive_server.service import PassiveServerService

        svc = PassiveServerService(
            config=PassiveServerConfig(
                api_base_url="http://127.0.0.1:19891",
                runtime_root=tmp_path,
            )
        )
        result = svc.agent_history("nonexistent")
        assert isinstance(result, tuple)
        assert result[0] == 404

    def test_no_observer_returns_503(self, tmp_path: Path) -> None:
        from houmao.passive_server.service import PassiveServerService

        svc = PassiveServerService(
            config=PassiveServerConfig(
                api_base_url="http://127.0.0.1:19891",
                runtime_root=tmp_path,
            )
        )
        agent = _agent(agent_id="abc123")
        svc.m_discovery.m_index.replace({"abc123": agent})

        result = svc.agent_history("abc123")
        assert isinstance(result, tuple)
        assert result[0] == 503
