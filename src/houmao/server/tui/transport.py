"""Direct tmux transport helpers for server-owned live tracking."""

from __future__ import annotations

from dataclasses import dataclass

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    TmuxPaneRecord,
    capture_tmux_pane,
    list_tmux_panes,
)


@dataclass(frozen=True)
class ResolvedTmuxTarget:
    """Resolved tmux pane target for one tracked session."""

    pane: TmuxPaneRecord


class TmuxTransportResolver:
    """Resolve tmux pane targets and pane captures for tracked sessions."""

    def resolve_target(
        self,
        *,
        session_name: str,
        window_name: str | None,
    ) -> ResolvedTmuxTarget:
        """Resolve the tracked pane for one tmux-backed session."""

        panes = list_tmux_panes(session_name=session_name)
        if not panes:
            raise TmuxCommandError(f"No tmux panes are available for `{session_name}`.")

        if window_name is not None:
            matching_panes = tuple(pane for pane in panes if pane.window_name == window_name)
            if not matching_panes:
                raise TmuxCommandError(
                    f"No tmux panes matched window `{window_name}` in `{session_name}`."
                )
            return ResolvedTmuxTarget(pane=_prefer_active_pane(matching_panes))

        return ResolvedTmuxTarget(pane=_prefer_active_pane(panes))

    def capture_text(self, *, target: ResolvedTmuxTarget) -> str:
        """Capture pane text directly from tmux."""

        return capture_tmux_pane(target=target.pane.pane_id)


def _prefer_active_pane(panes: tuple[TmuxPaneRecord, ...]) -> TmuxPaneRecord:
    """Prefer the active pane when multiple tmux panes match."""

    for pane in panes:
        if pane.pane_active:
            return pane
    return panes[0]
