"""Managed runtime policy exercised at the shared tmux adapter boundary."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxBackedAuthorityHealth,
    attach_tmux_session,
    capture_tmux_pane,
    create_tmux_session,
    has_tmux_session,
    list_tmux_sessions,
    overlay_tmux_rich_color_environment,
    prepare_headless_agent_window,
    probe_tmux_backed_authority,
    read_tmux_session_environment_value,
    resolve_primary_tmux_surface,
    resolve_tmux_pane,
    set_tmux_session_environment,
    show_tmux_environment,
)
from houmao.execution.tmux import (
    TmuxCommandError,
    TmuxCommandResult,
    TmuxObservationUnavailable,
    TmuxPaneRecord,
    TmuxServer,
    tmux_server_scope,
)

_SESSION_NAME = "HOUMAO-gpu"
_SOCKET_PATH = "/tmp/houmao-tmux-runtime-unit.sock"


@pytest.fixture(autouse=True)
def _isolate_tmux(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep unit tests inside an inert scope and forbid real terminal calls."""

    def _unexpected(*args: object, **kwargs: object) -> None:
        raise AssertionError("Unexpected live tmux operation in a unit test")

    for name in ("command", "observe_session", "start"):
        monkeypatch.setattr(TmuxServer, name, _unexpected)
    with tmux_server_scope(_SOCKET_PATH):
        yield


def _result(
    args: Sequence[str], *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> TmuxCommandResult:
    """Construct a checked-adapter result for a test operation."""

    return TmuxCommandResult(tuple(args), returncode, stdout, stderr)


def _stub_commands(
    monkeypatch: pytest.MonkeyPatch,
    response: Callable[[Sequence[str]], TmuxCommandResult] = _result,
) -> list[list[str]]:
    """Capture adapter requests and supply test-local command results."""

    calls: list[list[str]] = []

    def _command(
        self: TmuxServer, args: Sequence[str], *, sensitive: bool = False, no_start: bool = False
    ) -> TmuxCommandResult:
        assert self.socket_path == _SOCKET_PATH
        calls.append(list(args))
        return response(args)

    monkeypatch.setattr(TmuxServer, "command", _command)
    return calls


def _stub_start(
    monkeypatch: pytest.MonkeyPatch, *, returncode: int = 0
) -> list[tuple[list[str], dict[str, str]]]:
    """Capture the launch arguments and child environment at native startup."""

    calls: list[tuple[list[str], dict[str, str]]] = []

    def _start(
        self: TmuxServer, args: Sequence[str], *, environment: Mapping[str, str]
    ) -> TmuxCommandResult:
        assert self.socket_path == _SOCKET_PATH
        calls.append((list(args), dict(environment)))
        return _result(args, returncode=returncode)

    monkeypatch.setattr(TmuxServer, "start", _start)
    return calls


def _stub_observations(
    monkeypatch: pytest.MonkeyPatch, *observations: tuple[TmuxPaneRecord, ...] | None
) -> None:
    """Provide a sequence of exact session-wide observations."""

    remaining = iter(observations)

    def _observe(self: TmuxServer, session_name: str) -> tuple[TmuxPaneRecord, ...] | None:
        assert self.socket_path == _SOCKET_PATH
        assert session_name == _SESSION_NAME
        return next(remaining)

    monkeypatch.setattr(TmuxServer, "observe_session", _observe)


def _pane(
    *,
    pane_id: str = "%1",
    window_id: str = "@1",
    window_index: str = "0",
    window_name: str = "agent",
    pane_index: str = "0",
    active: bool = True,
) -> TmuxPaneRecord:
    """Build one observed pane in the managed test session."""

    return TmuxPaneRecord(
        pane_id=pane_id,
        session_name=_SESSION_NAME,
        session_id="$1",
        window_id=window_id,
        window_index=window_index,
        window_name=window_name,
        pane_index=pane_index,
        pane_active=active,
        pane_pid=1234,
    )


def test_has_tmux_session_uses_an_exact_target(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_commands(monkeypatch)

    result = has_tmux_session(session_name=_SESSION_NAME)

    assert result.returncode == 0
    assert calls == [["has-session", "-t", f"={_SESSION_NAME}"]]


def test_show_tmux_environment_uses_an_exact_target(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_commands(
        monkeypatch, lambda args: _result(args, stdout="HOUMAO_MANIFEST_PATH=/tmp/x.json\n")
    )

    result = show_tmux_environment(
        session_name=_SESSION_NAME,
        variable_name="HOUMAO_MANIFEST_PATH",
    )

    assert result.stdout == "HOUMAO_MANIFEST_PATH=/tmp/x.json\n"
    assert calls == [["show-environment", "-t", f"={_SESSION_NAME}", "HOUMAO_MANIFEST_PATH"]]


def test_list_tmux_sessions_allows_missing_server(monkeypatch: pytest.MonkeyPatch) -> None:
    def _list(self: TmuxServer, *, allow_missing_server: bool) -> set[str]:
        assert self.socket_path == _SOCKET_PATH
        assert allow_missing_server
        return set()

    monkeypatch.setattr(TmuxServer, "list_sessions", _list)
    assert list_tmux_sessions() == set()


def test_create_tmux_session_surfaces_a_silent_start_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    starts = _stub_start(monkeypatch, returncode=23)
    commands = _stub_commands(monkeypatch)

    with pytest.raises(TmuxCommandError, match="Failed to create.*exited with status 23"):
        create_tmux_session(session_name=_SESSION_NAME, working_directory=tmp_path)

    assert len(starts) == 1
    assert commands == []


@pytest.mark.parametrize("config_enabled", [True, False])
def test_create_tmux_session_applies_config_policy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, config_enabled: bool
) -> None:
    if config_enabled:
        monkeypatch.delenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", raising=False)
    else:
        monkeypatch.setenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", "0")
    monkeypatch.setenv("EXAMPLE_PRIVATE_TOKEN", "runtime-unit-secret")
    starts = _stub_start(monkeypatch)
    commands = _stub_commands(monkeypatch)

    create_tmux_session(session_name=_SESSION_NAME, working_directory=tmp_path)

    [(args, environment)] = starts
    assert args == ["new-session", "-d", "-E", "-s", _SESSION_NAME, "-c", str(tmp_path)]
    assert "EXAMPLE_PRIVATE_TOKEN" not in environment
    assert "TMUX" not in environment
    assert "TMUX_PANE" not in environment
    if config_enabled:
        session = f"={_SESSION_NAME}:"
        assert commands == [
            ["set-option", "-t", session, "mouse", "on"],
            ["set-option", "-t", session, "default-terminal", "tmux-256color"],
            ["set-option", "-at", session, "terminal-overrides", ",*256col*:Tc"],
            ["set-environment", "-t", session, "TERM", "tmux-256color"],
            ["set-environment", "-t", session, "COLORTERM", "truecolor"],
            ["set-environment", "-t", session, "-r", "NO_COLOR"],
        ]
    else:
        assert commands == []


def test_create_tmux_session_cleans_up_and_guides_when_injection_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", raising=False)
    _stub_start(monkeypatch)

    def _respond(args: Sequence[str]) -> TmuxCommandResult:
        if args[0] == "set-option":
            return _result(args, returncode=1, stderr="bad option")
        return _result(args)

    calls = _stub_commands(monkeypatch, _respond)

    with pytest.raises(
        TmuxCommandError, match="tmux config injection.*HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0"
    ):
        create_tmux_session(session_name=_SESSION_NAME, working_directory=tmp_path)

    assert calls[-1] == ["kill-session", "-t", f"={_SESSION_NAME}"]


@pytest.mark.parametrize("config_enabled", [True, False])
def test_overlay_tmux_rich_color_environment(
    monkeypatch: pytest.MonkeyPatch, config_enabled: bool
) -> None:
    if config_enabled:
        monkeypatch.delenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", raising=False)
    else:
        monkeypatch.setenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", "0")
    baseline = {"NO_COLOR": "1", "TERM": "dumb", "COLORTERM": "", "EXAMPLE_TOKEN": "abc"}
    env = baseline.copy()

    overlay_tmux_rich_color_environment(env)

    if config_enabled:
        assert env == {"TERM": "tmux-256color", "COLORTERM": "truecolor", "EXAMPLE_TOKEN": "abc"}
    else:
        assert env == baseline


@pytest.mark.parametrize("initial_index", ["0", "1"])
def test_prepare_headless_agent_window_normalizes_primary_window(
    monkeypatch: pytest.MonkeyPatch, initial_index: str
) -> None:
    initial = _pane(window_name="shell", window_index=initial_index, pane_index=initial_index)
    final = replace(initial, window_name="agent", window_index="0", pane_index="0")
    _stub_observations(monkeypatch, (initial,), (final,))
    calls = _stub_commands(monkeypatch)

    observed = prepare_headless_agent_window(session_name=_SESSION_NAME, fresh_session=True)

    moves = (
        [["move-window", "-s", initial.window_id, "-t", f"={_SESSION_NAME}:0"]]
        if initial_index == "1"
        else []
    )
    assert calls == [
        *moves,
        ["set-window-option", "-t", initial.window_id, "pane-base-index", "0"],
        ["rename-window", "-t", initial.window_id, "agent"],
        ["select-window", "-t", initial.window_id],
    ]
    assert observed == final


def test_prepare_headless_agent_window_fails_closed_on_fresh_extra_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_observations(
        monkeypatch,
        (_pane(), _pane(pane_id="%2", window_id="@2", window_index="1", window_name="logs")),
    )
    calls = _stub_commands(monkeypatch)

    with pytest.raises(TmuxCommandError, match="unexpected extra windows"):
        prepare_headless_agent_window(session_name=_SESSION_NAME, fresh_session=True)

    assert calls == []


def test_resolve_primary_tmux_surface_validates_nonzero_pane_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _pane(pane_index="1")
    _stub_observations(monkeypatch, (expected,))

    result = resolve_primary_tmux_surface(session_name=_SESSION_NAME, pane_id="%1", window_id="@1")

    assert result == expected


def test_resolve_primary_tmux_surface_rejects_stale_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_observations(monkeypatch, (_pane(),))

    with pytest.raises(TmuxCommandError, match="No tmux panes matched primary selector"):
        resolve_primary_tmux_surface(session_name=_SESSION_NAME, pane_id="%missing")


def test_resolve_primary_tmux_surface_rejects_ambiguous_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_observations(monkeypatch, (_pane(), _pane(pane_id="%2", pane_index="1")))

    with pytest.raises(TmuxCommandError, match="Ambiguous tmux primary surface"):
        resolve_primary_tmux_surface(session_name=_SESSION_NAME, window_name="agent")


def test_probe_tmux_backed_authority_classifies_healthy_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = _pane(pane_id="%2", window_id="@2", window_index="1", window_name="gateway")
    _stub_observations(monkeypatch, (_pane(pane_index="1", active=False), gateway))

    assert probe_tmux_backed_authority(session_name=_SESSION_NAME) == TmuxBackedAuthorityHealth(
        state="healthy",
        session_exists=True,
        primary_window_exists=True,
        primary_pane_exists=True,
        session_id="$1",
    )


def test_probe_tmux_backed_authority_classifies_gateway_only_remnant_as_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = _pane(pane_id="%2", window_id="@2", window_index="1", window_name="gateway")
    _stub_observations(monkeypatch, (gateway,))

    assert probe_tmux_backed_authority(session_name=_SESSION_NAME) == TmuxBackedAuthorityHealth(
        state="degraded_missing_primary",
        session_exists=True,
        primary_window_exists=False,
        primary_pane_exists=False,
        session_id="$1",
    )


def test_probe_tmux_backed_authority_classifies_stale_primary_handles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_observations(monkeypatch, (_pane(),))

    result = probe_tmux_backed_authority(
        session_name=_SESSION_NAME, primary_window_id="@missing", primary_pane_id="%missing"
    )

    assert result == TmuxBackedAuthorityHealth(
        state="degraded_stale_primary_handles",
        session_exists=True,
        primary_window_exists=True,
        primary_pane_exists=True,
        primary_window_handle_valid=False,
        primary_pane_handle_valid=False,
        session_id="$1",
    )


@pytest.mark.parametrize("session_name", [_SESSION_NAME, "   "])
def test_probe_tmux_backed_authority_classifies_missing_session_as_stale(
    monkeypatch: pytest.MonkeyPatch, session_name: str
) -> None:
    if session_name.strip():
        _stub_observations(monkeypatch, None)

    assert probe_tmux_backed_authority(session_name=session_name) == TmuxBackedAuthorityHealth(
        state="stale_missing_session",
        session_exists=False,
        primary_window_exists=False,
        primary_pane_exists=False,
    )


def test_probe_tmux_backed_authority_preserves_observation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unavailable(self: TmuxServer, session_name: str) -> None:
        raise TmuxObservationUnavailable("tmux observation failed", returncode=23)

    monkeypatch.setattr(TmuxServer, "observe_session", _unavailable)

    with pytest.raises(TmuxObservationUnavailable) as error:
        probe_tmux_backed_authority(session_name=_SESSION_NAME)
    assert error.value.returncode == 23


def test_set_tmux_session_environment_surfaces_key_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _stub_commands(
        monkeypatch, lambda args: _result(args, returncode=int("HOUMAO_MANIFEST_PATH" in args))
    )

    with pytest.raises(TmuxCommandError, match="HOUMAO_MANIFEST_PATH") as error:
        set_tmux_session_environment(
            session_name=_SESSION_NAME,
            env_vars={"HOUMAO_TOOL": "codex", "HOUMAO_MANIFEST_PATH": "/tmp/session.json"},
        )

    assert "/tmp/session.json" not in str(error.value)
    assert calls == [
        ["set-environment", "-t", f"={_SESSION_NAME}", "--", "HOUMAO_TOOL", "codex"],
        [
            "set-environment",
            "-t",
            f"={_SESSION_NAME}",
            "--",
            "HOUMAO_MANIFEST_PATH",
            "/tmp/session.json",
        ],
    ]


def test_read_tmux_session_environment_value_returns_none_for_unknown_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_commands(monkeypatch, lambda args: _result(args, returncode=1, stderr="unknown variable"))

    assert (
        read_tmux_session_environment_value(session_name=_SESSION_NAME, variable_name="KEY") is None
    )


def test_read_tmux_session_environment_value_surfaces_unavailable_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_commands(monkeypatch, lambda args: _result(args, returncode=23))

    with pytest.raises(TmuxCommandError, match="KEY.*exit 23"):
        read_tmux_session_environment_value(session_name=_SESSION_NAME, variable_name="KEY")


def test_attach_tmux_session_uses_an_exact_target(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_commands(monkeypatch)

    attach_tmux_session(session_name=_SESSION_NAME)

    assert calls == [["attach-session", "-t", f"={_SESSION_NAME}"]]


@pytest.mark.parametrize("explicit_window", [True, False])
def test_resolve_tmux_pane_requires_exact_selection_for_multiple_windows(
    monkeypatch: pytest.MonkeyPatch, explicit_window: bool
) -> None:
    primary = _pane(active=False)
    gateway = _pane(pane_id="%2", window_id="@2", window_index="1", window_name="gateway")
    _stub_observations(monkeypatch, (primary, gateway))

    if explicit_window:
        assert resolve_tmux_pane(session_name=_SESSION_NAME, window_name="agent") == primary
    else:
        with pytest.raises(TmuxCommandError, match="Ambiguous tmux pane target"):
            resolve_tmux_pane(session_name=_SESSION_NAME)


def test_capture_tmux_pane_requests_normalized_escaped_scrollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _capture(self: TmuxServer, target: str, *, history: bool, escape_sequences: bool) -> str:
        assert self.socket_path == _SOCKET_PATH
        assert target == "%9"
        assert history and escape_sequences
        return "line one\nline two"

    monkeypatch.setattr(TmuxServer, "capture_pane", _capture)

    assert capture_tmux_pane(target="%9") == "line one\nline two"
