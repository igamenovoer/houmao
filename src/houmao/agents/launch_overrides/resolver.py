"""Merge and runtime resolution for launch overrides."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from houmao.agents.launch_overrides.models import (
    LaunchArgsSection,
    LaunchDefaults,
    LaunchOverrides,
    SupportedLaunchBackend,
)
from houmao.agents.launch_overrides.native import split_permission_args
from houmao.agents.tool_params import (
    get_tool_params_adapter,
    resolve_tool_params,
    validate_tool_params,
)

_RESERVED_ARGS_BY_BACKEND: Final[dict[SupportedLaunchBackend, tuple[str, ...]]] = {
    "raw_launch": (),
    "codex_headless": ("-c", "--config", "app-server", "exec", "resume", "--json", "--last"),
    "codex_app_server": ("app-server", "--listen", "--stdio"),
    "claude_headless": (
        "-p",
        "--print",
        "--append-system-prompt",
        "--output-format",
        "--input-format",
        "--resume",
        "--session-id",
        "--continue",
        "--fork-session",
        "-r",
        "-c",
    ),
    "kimi_headless": (
        "-p",
        "--prompt",
        "--output-format",
        "--session",
        "--resume",
        "--continue",
        "--skills-dir",
        "--plan",
    ),
    "kimi_acp": ("acp",),
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
    "hermes_tui": (),
    "hermes_service": (),
    "hermes_headless": (),
}
_UNSUPPORTED_OVERRIDE_BACKENDS: Final[frozenset[SupportedLaunchBackend]] = frozenset({"cao_rest"})
_KIMI_SESSION_ARGS = ("--session", "-S", "--resume", "--continue", "-c")
_KIMI_ROLE_ARGS = ("--agent", "--agent-file")
_TUI_IDENTITY_ARGS: Final[dict[str, tuple[str, ...]]] = {
    "claude": ("--session-id", "--resume", "-r", "--continue", "-c", "--fork-session"),
    "codex": ("resume", "--last"),
    "kimi": _KIMI_SESSION_ARGS,
}
_OWNED_CONFIG_BACKENDS = frozenset(
    {
        "codex_app_server",
        "kimi_acp",
        "kimi_web",
        "dsh_headless",
        "dsh_acp",
        "dsh_web",
    }
)


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
    tool_params: dict[str, Any] = field(default_factory=dict)
    tool_param_sources: dict[str, str] = field(default_factory=dict)

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
    tool_param_layers: Sequence[tuple[str, Mapping[str, Any]]] | None = None,
) -> ResolvedLaunchBehavior:
    """Resolve effective launch behavior for one backend."""

    merged = merge_launch_intent(
        adapter_defaults=adapter_defaults,
        recipe_overrides=recipe_overrides,
        direct_overrides=direct_overrides,
    )
    if tool_param_layers is not None:
        native_args, layers = _resolve_parameter_layers(
            tool=tool,
            backend=backend,
            adapter_defaults=adapter_defaults,
            recipe_overrides=recipe_overrides,
            direct_overrides=direct_overrides,
            typed_layers=tool_param_layers,
        )
        tool_params = resolve_tool_params(tool, layers)
    else:
        native_args, aliases = split_permission_args(
            tool, merged.args, source="launch args", backend=backend
        )
        _validate_reserved_args(tool, backend, native_args, source="launch args")
        layers = [("launch args", aliases), ("effective tool_params", tool_params or {})]
        if aliases:
            tool_params = resolve_tool_params(tool, layers)

    adapter = get_tool_params_adapter(tool) if tool_params is not None else None
    effective = (
        adapter.parse_effective(tool_params, source="effective tool_params")
        if adapter is not None and tool_params is not None
        else None
    )

    if backend in _UNSUPPORTED_OVERRIDE_BACKENDS:
        unsupported_fields: list[str] = []
        if native_args:
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

    args_before_policy = (*native_args, *translated_args)
    if (tool == "hermes" or backend in _OWNED_CONFIG_BACKENDS) and args_before_policy:
        raise ValueError(
            f"backend={backend!r} uses owned native configuration and rejects raw launch arguments."
        )

    sources = {}
    for source, payload in layers:
        for name, value in payload.items():
            if name == "permissions" and isinstance(value, dict):
                sources.update({f"permissions.{key}": source for key in value})
            else:
                sources[name] = source
    return ResolvedLaunchBehavior(
        merged=merged,
        translated_args=translated_args,
        args_before_policy=args_before_policy,
        tool_params=dict(tool_params or {}),
        tool_param_sources=sources,
    )


def _resolve_parameter_layers(
    *,
    tool: str,
    backend: SupportedLaunchBackend,
    adapter_defaults: LaunchDefaults,
    recipe_overrides: LaunchOverrides | None,
    direct_overrides: LaunchOverrides | None,
    typed_layers: Sequence[tuple[str, Mapping[str, Any]]],
) -> tuple[tuple[str, ...], list[tuple[str, Mapping[str, Any]]]]:
    """Validate raw inputs and normalize the selected arguments at their own layer."""

    direct = direct_overrides.args if direct_overrides else None
    preset = recipe_overrides.args if recipe_overrides else None
    selected = direct or preset
    args: list[str] = []
    supplied: dict[str, Mapping[str, Any]] = {}
    for source, original, use in (
        ("adapter", adapter_defaults.args, selected is None or selected.mode == "append"),
        ("preset", preset.values if preset else (), direct is None),
        ("direct", direct.values if direct else (), direct is not None),
    ):
        remaining, aliases = split_permission_args(
            tool, original, source=f"{source} launch args", backend=backend
        )
        _validate_reserved_args(tool, backend, remaining, source=f"{source} launch args")
        if use:
            args.extend(remaining)
            supplied[source] = validate_tool_params(tool, aliases, source=f"{source} launch args")

    layers: list[tuple[str, Mapping[str, Any]]] = []
    for source, payload in typed_layers:
        layers.append((f"{source} launch args", supplied.get(source, {})))
        layers.append((source, payload))
    return tuple(args), layers


def _validate_reserved_args(
    tool: str, backend: SupportedLaunchBackend, args: tuple[str, ...], *, source: str
) -> None:
    """Reject authored protocol controls even when another argument layer wins."""

    reserved_args = ("--", *_RESERVED_ARGS_BY_BACKEND[backend])
    if backend == "raw_launch":
        reserved_args = (*reserved_args, *_TUI_IDENTITY_ARGS.get(tool, ()))
    if tool == "kimi":
        reserved_args = (*reserved_args, *_KIMI_SESSION_ARGS, *_KIMI_ROLE_ARGS)

    conflicts = sorted(
        {
            "-c" if tool == "codex" and arg.startswith("-c") else arg.partition("=")[0]
            for arg in args
            if arg != '--config=approvals_reviewer="auto_review"'
        }.intersection(reserved_args)
    )
    if conflicts:
        joined = ", ".join(conflicts)
        raise ValueError(
            f"{source} contains backend-reserved argument(s) for backend={backend!r}: "
            f"{joined}. Houmao applies the managed startup protocol and session identity. "
            "For continuation use the Houmao relaunch session selector."
        )


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
