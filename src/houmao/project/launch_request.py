"""Typed inputs shared by project launch adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from houmao.agents.managed_launch_force import ManagedLaunchForceMode
from houmao.agents.realm_controller.agent_identity import AgentIdMode
from houmao.agents.realm_controller.backends.headless_output import (
    HeadlessDisplayDetail,
    HeadlessDisplayStyle,
)
from houmao.agents.realm_controller.gateway_models import GatewayTuiTrackingTimingOverridesV1
from houmao.agents.realm_controller.run_modes import RunMode
from houmao.execution.tmux_selection import TmuxServerMode


class ProjectLaunchRequest(BaseModel):
    """One project launch with the defaults used by both entrypoints."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    specialist: str | None = None
    profile: str | None = None
    name: str | None = None
    agent_id: str | None = None
    agent_id_mode: AgentIdMode | None = None
    auth: str | None = None
    model: str | None = None
    reasoning_level: int | None = Field(default=None, ge=0)
    session_name: str | None = None
    tmux_server: TmuxServerMode | None = None
    tmux_socket_path: str | None = None
    mode: RunMode | None = None
    headless_display_style: HeadlessDisplayStyle | None = None
    headless_display_detail: HeadlessDisplayDetail | None = None
    no_gateway: bool = False
    gateway_port: int | None = Field(default=None, ge=1, le=65535)
    gateway_background: bool = False
    gateway_admin_seed_path: Path | None = None
    gateway_tui_watch_poll_interval_seconds: float | None = Field(default=None, gt=0)
    gateway_tui_stability_threshold_seconds: float | None = Field(default=None, gt=0)
    gateway_tui_completion_stability_seconds: float | None = Field(default=None, gt=0)
    gateway_tui_unknown_to_stalled_timeout_seconds: float | None = Field(default=None, gt=0)
    gateway_tui_stale_active_recovery_seconds: float | None = Field(default=None, gt=0)
    gateway_tui_final_stable_active_recovery_seconds: float | None = Field(default=None, gt=0)
    workdir: Path | None = None
    env_set: tuple[str, ...] = ()
    runtime_set: tuple[str, ...] = ()
    mail_transport: Literal["filesystem", "email"] | None = None
    mail_root: Path | None = None
    mail_account_dir: Path | None = None
    managed_header: bool | None = None
    managed_header_section: tuple[str, ...] = ()
    reuse_home: bool = False
    force_mode: ManagedLaunchForceMode | None = None
    tool_params: str | None = None

    @field_validator("env_set", "runtime_set", "managed_header_section", mode="before")
    @classmethod
    def _repeatable_option(cls, value: object) -> object:
        """Accept JSON arrays and the empty repeatable option accepted by v1."""

        if value is None:
            return ()
        return tuple(value) if isinstance(value, list) else value

    @field_validator("no_gateway", "gateway_background", "reuse_home", mode="before")
    @classmethod
    def _optional_flag(cls, value: object) -> object:
        """Keep the previous false posture for explicit null v1 flags."""

        return False if value is None else value

    @field_validator(
        "workdir", "mail_root", "mail_account_dir", "gateway_admin_seed_path", mode="before"
    )
    @classmethod
    def _path(cls, value: object) -> object:
        """Carry owner paths without inspecting them on the submitting side."""

        return Path(value) if isinstance(value, str) else value

    def gateway_tracking_overrides(self) -> GatewayTuiTrackingTimingOverridesV1:
        """Collect the explicit gateway timing options into their shared model."""

        return GatewayTuiTrackingTimingOverridesV1(
            watch_poll_interval_seconds=self.gateway_tui_watch_poll_interval_seconds,
            stability_threshold_seconds=self.gateway_tui_stability_threshold_seconds,
            completion_stability_seconds=self.gateway_tui_completion_stability_seconds,
            unknown_to_stalled_timeout_seconds=self.gateway_tui_unknown_to_stalled_timeout_seconds,
            stale_active_recovery_seconds=self.gateway_tui_stale_active_recovery_seconds,
            final_stable_active_recovery_seconds=(
                self.gateway_tui_final_stable_active_recovery_seconds
            ),
        )

    def validate_combinations(self) -> None:
        """Reject intrinsically conflicting launch options before project setup."""

        if self.specialist is not None and self.profile is not None:
            raise ValueError("`--specialist` and `--profile` cannot be combined.")
        if self.specialist is None and self.profile is None:
            raise ValueError("Provide exactly one of `--specialist` or `--profile`.")
        if self.reuse_home and self.force_mode == "clean":
            raise ValueError(
                "`--reuse-home` is incompatible with `--force clean` because `clean` would destroy "
                "the preserved home."
            )
        if self.no_gateway and self.gateway_port is not None:
            raise ValueError("`--no-gateway` and `--gateway-port` cannot be combined.")
        if self.no_gateway and self.gateway_background:
            raise ValueError("`--no-gateway` and `--gateway-background` cannot be combined.")
        if self.no_gateway and self.gateway_tracking_overrides().has_values():
            raise ValueError("`--no-gateway` cannot be combined with gateway TUI timing overrides.")
        if self.mail_transport == "email":
            raise ValueError(
                "Mailbox transport `email` is not implemented yet for `project agents launch`."
            )
        if self.mail_transport is None and (
            self.mail_root is not None or self.mail_account_dir is not None
        ):
            raise ValueError(
                "`--mail-root` and `--mail-account-dir` require `--mail-transport filesystem`."
            )
