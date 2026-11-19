"""Merge and runtime resolution for launch overrides."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from houmao.agents.launch_overrides.models import (
    LaunchArgsSection,
    LaunchDefaults,
    LaunchOverrides,
    SupportedLaunchBackend,
)
from houmao.agents.tool_params import get_tool_params_adapter

_RESERVED_ARGS_BY_BACKEND: Final[dict[SupportedLaunchBackend, tuple[str, ...]]] = {
    "raw_launch": (),
    "codex_headless": ("-c", "app-server", "exec", "resume", "--json"),
    "codex_app_server": ("app-server",),
    "claude_headless": ("-p", "--append-system-prompt", "--output-format", "--resume"),
    "kimi_headless": (
        "-p",
        "--prompt",
        "--output-format",
        "--session",
        "--resume",
        "--continue",
        "--skills-dir",
        "--auto",
        "--yolo",
        "--plan",
    ),
    "kimi_acp": (),
    "kimi_web": ("web", "--host", "--port", "--no-open"),
    "cao_rest": (),
    "dsh_headless": (
        "--profile",
        "--config",
        "--patch",
        "--json",
        "--session-id",
        "web",
        "headless",
    ),
    "dsh_acp": ("--profile", "--config", "--patch", "web", "headless"),
    "dsh_web": (
        "--profile",
        "--config",
        "--patch",
        "--host",
        "--port",
        "--open",
        "--no-open",
        "web",
        "headless",
        "--tui",
        "--no-tui",
    ),
}
_UNSUPPORTED_OVERRIDE_BACKENDS: Final[frozenset[SupportedLaunchBackend]] = frozenset({"cao_rest"})


@dataclass(frozen=True)
class MergedLaunchIntent:
    """Merged launch intent before backend resolution."""

    args: tuple[str, ...]
    selected_args_section: LaunchArgsSection | None

    def to_payload(self) -> dict[str, object]:
        """Serialize merged launch intent."""

        payload: dict[str, object] = {
            "args": list(self.args),
        }
        if self.selected_args_section is not None:
            payload["selected_args_section"] = self.selected_args_section.to_payload()
        return payload


@dataclass(frozen=True)
class ResolvedLaunchBehavior:
    """Backend-aware launch behavior before policy and protocol injection."""

    merged: MergedLaunchIntent
    translated_args: tuple[str, ...]
    args_before_policy: tuple[str, ...]

    def to_payload(
        self,
        *,
        adapter_defaults: LaunchDefaults,
        recipe_overrides: LaunchOverrides | None,
        direct_overrides: LaunchOverrides | None,
        construction_provenance: dict[str, object] | None,
        backend: SupportedLaunchBackend,
    ) -> dict[str, object]:
        """Serialize runtime launch provenance."""

        payload: dict[str, object] = {
            "adapter_defaults": adapter_defaults.to_payload(),
            "requested_overrides": {
                "recipe": recipe_overrides.to_payload() if recipe_overrides is not None else None,
                "direct": direct_overrides.to_payload() if direct_overrides is not None else None,
            },
            "merged_request": self.merged.to_payload(),
            "backend_resolution": {
                "backend": backend,
                "translated_args": list(self.translated_args),
                "args_before_launch_policy": list(self.args_before_policy),
                "protocol_reserved_args": list(_RESERVED_ARGS_BY_BACKEND[backend]),
            },
        }
        if construction_provenance is not None:
            payload["construction_provenance"] = dict(construction_provenance)
        return payload


def helper_launch_args(
    *,
    adapter_defaults: LaunchDefaults,
    recipe_overrides: LaunchOverrides | None,
    direct_overrides: LaunchOverrides | None,
) -> list[str]:
    """Resolve raw helper args without backend-specific typed-param translation."""

    return list(
        merge_launch_intent(
            adapter_defaults=adapter_defaults,
            recipe_overrides=recipe_overrides,
            direct_overrides=direct_overrides,
        ).args
    )


def merge_launch_intent(
    *,
    adapter_defaults: LaunchDefaults,
    recipe_overrides: LaunchOverrides | None,
    direct_overrides: LaunchOverrides | None,
) -> MergedLaunchIntent:
    """Merge adapter defaults with recipe and direct launch overrides."""

    selected_args_section = _select_args_section(
        recipe_overrides=recipe_overrides,
        direct_overrides=direct_overrides,
    )
    if selected_args_section is None:
        effective_args = adapter_defaults.args
    elif selected_args_section.mode == "append":
        effective_args = (*adapter_defaults.args, *selected_args_section.values)
    else:
        effective_args = selected_args_section.values

    return MergedLaunchIntent(
        args=effective_args,
        selected_args_section=selected_args_section,
    )


def resolve_launch_behavior(
    *,
    tool: str,
    backend: SupportedLaunchBackend,
    adapter_defaults: LaunchDefaults,
    recipe_overrides: LaunchOverrides | None,
    direct_overrides: LaunchOverrides | None,
    tool_params: Mapping[str, Any] | None = None,
) -> ResolvedLaunchBehavior:
    """Resolve effective launch behavior for one backend."""

    merged = merge_launch_intent(
        adapter_defaults=adapter_defaults,
        recipe_overrides=recipe_overrides,
        direct_overrides=direct_overrides,
    )
    adapter = get_tool_params_adapter(tool) if tool_params is not None else None
    effective = (
        adapter.parse_effective(tool_params, source="effective tool_params")
        if adapter is not None and tool_params is not None
        else None
    )

    if backend in _UNSUPPORTED_OVERRIDE_BACKENDS:
        unsupported_fields: list[str] = []
        if merged.args:
            unsupported_fields.append("args")
        if effective is not None and effective.model_dump(exclude_defaults=True):
            unsupported_fields.append("tool_params")
        if unsupported_fields:
            joined = ", ".join(unsupported_fields)
            raise ValueError(
                f"backend={backend!r} cannot honor launch overrides for `{joined}`. "
                "Use a native backend or rebuild without recipe-owned launch overrides."
            )
        return ResolvedLaunchBehavior(
            merged=merged,
            translated_args=(),
            args_before_policy=(),
        )

    translated_args: tuple[str, ...] = ()
    if adapter is not None and effective is not None:
        translated_args = adapter.prepare_launch(effective, backend=backend)

    args_before_policy = (*merged.args, *translated_args)
    conflicts = _find_reserved_arg_conflicts(
        args=list(args_before_policy),
        reserved_args=_RESERVED_ARGS_BY_BACKEND[backend],
    )
    if conflicts:
        joined = ", ".join(conflicts)
        raise ValueError(
            "Launch overrides contain backend-reserved argument(s): "
            f"{joined}. Remove those from adapter defaults or launch overrides; the backend "
            "injects them automatically."
        )

    return ResolvedLaunchBehavior(
        merged=merged,
        translated_args=translated_args,
        args_before_policy=args_before_policy,
    )


def _find_reserved_arg_conflicts(*, args: list[str], reserved_args: tuple[str, ...]) -> list[str]:
    """Return reserved args that conflict with the requested launch behavior."""

    conflicts: set[str] = set()
    for arg in args:
        for reserved in reserved_args:
            if arg == reserved or arg.startswith(f"{reserved}="):
                conflicts.add(reserved)
    return sorted(conflicts)


def _select_args_section(
    *,
    recipe_overrides: LaunchOverrides | None,
    direct_overrides: LaunchOverrides | None,
) -> LaunchArgsSection | None:
    """Select the winning args section under precedence rules."""

    if direct_overrides is not None and direct_overrides.args is not None:
        return direct_overrides.args
    if recipe_overrides is not None:
        return recipe_overrides.args
    return None
