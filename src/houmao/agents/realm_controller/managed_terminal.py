"""Managed primary surface selection from an owner-bound tmux observation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from houmao.agents.realm_controller.boundary_models import SessionManifestTmuxSectionV1
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.execution.tmux import TmuxPaneRecord, TmuxServer

PrimaryTmuxState = Literal[
    "valid",
    "stale_handles",
    "missing_session",
    "missing_window",
    "dead_pane",
    "ambiguous_pane",
]


@dataclass(frozen=True)
class PrimaryTmuxObservation:
    """Classify the primary binding and expose the observed evidence without changing it."""

    state: PrimaryTmuxState
    session_exists: bool
    primary_window_exists: bool = False
    primary_pane_exists: bool = False
    primary_window_handle_valid: bool | None = None
    primary_pane_handle_valid: bool | None = None
    pane: TmuxPaneRecord | None = None
    replacement: TmuxPaneRecord | None = None


def observe_primary_tmux(binding: SessionManifestTmuxSectionV1) -> PrimaryTmuxObservation:
    """Inspect the recorded owner socket and select the managed primary surface."""

    if binding.socket_path is None:
        raise SessionManifestError("Managed terminal observation requires a saved tmux socket")
    panes = TmuxServer(binding.socket_path).observe_session(binding.session_name)
    return select_primary_tmux_surface(binding, panes)


def select_primary_tmux_surface(
    binding: SessionManifestTmuxSectionV1,
    panes: tuple[TmuxPaneRecord, ...] | None,
) -> PrimaryTmuxObservation:
    """Resolve window zero and its pane from one checked session-wide observation."""

    if binding.primary_window_index != "0":
        raise SessionManifestError("Managed terminal binding requires primary window index 0")
    candidates = tuple(
        pane
        for pane in panes or ()
        if pane.session_name == binding.session_name and pane.window_index == "0"
    )
    saved_window_id = binding.primary_window_id
    saved_pane_id = binding.primary_pane_id
    saved_window_valid = (
        any(pane.window_id == saved_window_id for pane in candidates)
        if saved_window_id is not None
        else None
    )
    saved_panes = tuple(pane for pane in candidates if pane.pane_id == saved_pane_id)
    exact = next(
        (pane for pane in saved_panes if pane.window_id == saved_window_id),
        None,
    )
    live = tuple(pane for pane in candidates if not pane.pane_dead)
    replacement: TmuxPaneRecord | None = None
    state: PrimaryTmuxState
    if exact is not None:
        state = "dead_pane" if exact.pane_dead else "valid"
    elif panes is None:
        state = "missing_session"
    elif not candidates:
        state = "missing_window"
    elif not live:
        state = "dead_pane"
    elif len(live) == 1:
        state = "stale_handles"
        replacement = live[0]
    else:
        state = "ambiguous_pane"
    return PrimaryTmuxObservation(
        state=state,
        session_exists=panes is not None,
        primary_window_exists=bool(candidates),
        primary_pane_exists=bool(candidates),
        primary_window_handle_valid=saved_window_valid,
        primary_pane_handle_valid=bool(saved_panes) if saved_pane_id is not None else None,
        pane=exact,
        replacement=replacement,
    )
