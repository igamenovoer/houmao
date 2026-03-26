"""Direct tmux transport helpers for server-owned live tracking."""

from __future__ import annotations

from dataclasses import dataclass

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxPaneRecord,
    capture_tmux_pane,
    resolve_tmux_pane as resolve_tmux_pane_shared,
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
        window_index: str | None = None,
        pane_id: str | None = None,
        window_id: str | None = None,
    ) -> ResolvedTmuxTarget:
        """Resolve the tracked pane for one tmux-backed session."""

        return ResolvedTmuxTarget(
            pane=resolve_tmux_pane_shared(
                session_name=session_name,
                pane_id=pane_id,
                window_id=window_id,
                window_index=window_index,
                window_name=window_name,
            )
        )

    def capture_text(self, *, target: ResolvedTmuxTarget) -> str:
        """Capture pane text directly from tmux."""

        return capture_tmux_pane(target=target.pane.pane_id)
