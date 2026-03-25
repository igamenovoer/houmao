"""Merge and runtime resolution for launch overrides."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from houmao.agents.launch_overrides.models import (
    JsonValue,
    LaunchArgsSection,
    LaunchDefaults,
    LaunchOverrides,
    SupportedLaunchBackend,
    ToolLaunchMetadata,
    clone_json_mapping,
)

_RESERVED_ARGS_BY_BACKEND: Final[dict[SupportedLaunchBackend, tuple[str, ...]]] = {
    "raw_launch": (),
    "codex_headless": ("-c", "app-server", "exec", "resume", "--json"),
    "codex_app_server": ("app-server",),
    "claude_headless": ("-p", "--append-system-prompt", "--output-format", "--resume"),
    "gemini_headless": ("-p", "--output-format", "--resume"),
    "cao_rest": (),
    "houmao_server_rest": (),
}
_UNSUPPORTED_OVERRIDE_BACKENDS: Final[frozenset[SupportedLaunchBackend]] = frozenset(
    {"cao_rest", "houmao_server_rest"}
)


@dataclass(frozen=True)
class MergedLaunchIntent:
    """Merged launch intent before backend resolution."""

    args: tuple[str, ...]
    tool_params: dict[str, JsonValue]
    selected_args_section: LaunchArgsSection | None

    def to_payload(self) -> dict[str, object]:
        """Serialize merged launch intent."""

        payload: dict[str, object] = {
            "args": list(self.args),
            "tool_params": clone_json_mapping(self.tool_params),
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

    merged_tool_params = clone_json_mapping(adapter_defaults.tool_params)
    if recipe_overrides is not None:
        merged_tool_params.update(clone_json_mapping(recipe_overrides.tool_params))
    if direct_overrides is not None:
        merged_tool_params.update(clone_json_mapping(direct_overrides.tool_params))

    return MergedLaunchIntent(
        args=effective_args,
        tool_params=merged_tool_params,
        selected_args_section=selected_args_section,
    )


def resolve_launch_behavior(
    *,
    tool: str,
    backend: SupportedLaunchBackend,
    adapter_defaults: LaunchDefaults,
    recipe_overrides: LaunchOverrides | None,
    direct_overrides: LaunchOverrides | None,
    metadata: ToolLaunchMetadata,
) -> ResolvedLaunchBehavior:
    """Resolve effective launch behavior for one backend."""

    merged = merge_launch_intent(
        adapter_defaults=adapter_defaults,
        recipe_overrides=recipe_overrides,
        direct_overrides=direct_overrides,
    )

    if backend in _UNSUPPORTED_OVERRIDE_BACKENDS:
        unsupported_fields: list[str] = []
        if merged.args:
            unsupported_fields.append("args")
        unsupported_fields.extend(f"tool_params.{key}" for key in sorted(merged.tool_params))
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

    metadata.validate_requested_tool_params(
        tool=tool,
        tool_params=merged.tool_params,
        source="merged launch_overrides.tool_params",
    )

    translated_args: list[str] = []
    for key in sorted(merged.tool_params):
        definition = metadata.tool_params[key]
        projection = definition.backends.get(backend)
        if projection is None:
            raise ValueError(
                f"`launch_overrides.tool_params.{key}` is unsupported for backend={backend!r}"
            )
        translated_args.extend(
            projection.project(
                merged.tool_params[key],
                source=f"launch_overrides.tool_params.{key}",
            )
        )

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
        translated_args=tuple(translated_args),
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
