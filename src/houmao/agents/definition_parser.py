"""Parser-owned agent-definition catalog and preset resolution helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from houmao.agents.launch_overrides import (
    LaunchDefaults,
    LaunchOverrides,
    ToolLaunchMetadata,
    parse_launch_defaults,
    parse_launch_overrides,
    parse_tool_launch_metadata,
)
from houmao.agents.launch_policy.models import OperatorPromptMode
from houmao.agents.mailbox_runtime_models import MailboxDeclarativeConfig
from houmao.agents.mailbox_runtime_support import parse_declarative_mailbox_config
from houmao.agents.realm_controller.gateway_models import BlueprintGatewayDefaults

_PRESET_FILE_SUFFIXES: tuple[str, ...] = (".yaml", ".yml")
_PRESET_TOP_LEVEL_FIELDS: frozenset[str] = frozenset(
    {"role", "tool", "setup", "skills", "auth", "launch", "mailbox", "extra"}
)


@dataclass(frozen=True)
class AuthFileMapping:
    """Projection rule for one auth-owned file."""

    source: str
    destination: str
    mode: str
    required: bool = True


@dataclass(frozen=True)
class ToolAdapter:
    """Parsed tool-adapter contract."""

    tool: str
    home_selector_env_var: str
    launch_executable: str
    launch_defaults: LaunchDefaults
    launch_metadata: ToolLaunchMetadata
    env_injection_mode: str
    env_file_in_home: str | None
    setup_destination: str
    skills_destination: str
    skills_mode: str
    auth_files_dir: str
    auth_file_mappings: list[AuthFileMapping]
    auth_env_source: str
    auth_env_allowlist: list[str]

    @property
    def config_destination(self) -> str:
        """Compatibility alias for the setup projection destination."""

        return self.setup_destination

    @property
    def credential_files_dir(self) -> str:
        """Compatibility alias for the auth files directory."""

        return self.auth_files_dir

    @property
    def credential_file_mappings(self) -> list[AuthFileMapping]:
        """Compatibility alias for auth file mappings."""

        return self.auth_file_mappings

    @property
    def credential_env_source(self) -> str:
        """Compatibility alias for the auth env source path."""

        return self.auth_env_source

    @property
    def credential_env_allowlist(self) -> list[str]:
        """Compatibility alias for auth env allowlist names."""

        return self.auth_env_allowlist


@dataclass(frozen=True)
class PresetLaunchSettings:
    """Preset-owned launch settings."""

    prompt_mode: OperatorPromptMode | None = None
    overrides: LaunchOverrides | None = None
    env_records: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentPreset:
    """Parsed named preset definition."""

    path: Path
    name: str
    role_name: str
    tool: str
    setup: str
    skills: list[str]
    auth: str | None = None
    launch: PresetLaunchSettings = field(default_factory=PresetLaunchSettings)
    mailbox: MailboxDeclarativeConfig | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    gateway_defaults: BlueprintGatewayDefaults | None = None
    default_agent_name_value: str | None = None

    @property
    def config_profile(self) -> str:
        """Compatibility alias for the selected setup."""

        return self.setup

    @property
    def credential_profile(self) -> str | None:
        """Compatibility alias for the selected auth bundle."""

        return self.auth

    @property
    def launch_overrides(self) -> LaunchOverrides | None:
        """Compatibility alias for preset launch overrides."""

        return self.launch.overrides

    @property
    def operator_prompt_mode(self) -> OperatorPromptMode | None:
        """Compatibility alias for the preset prompt mode."""

        return self.launch.prompt_mode

    @property
    def launch_env_records(self) -> dict[str, str]:
        """Return persistent preset-owned launch env records."""

        return dict(self.launch.env_records)

    @property
    def default_agent_name(self) -> str | None:
        """Compatibility alias for removed preset-owned identity."""

        return self.default_agent_name_value


@dataclass(frozen=True)
class ParsedAgentCatalog:
    """Canonical parsed agent-definition catalog."""

    agent_def_dir: Path
    skills_root: Path
    tool_adapters: dict[str, ToolAdapter]
    setups: dict[str, dict[str, Path]]
    auths: dict[str, dict[str, Path]]
    presets: dict[Path, AgentPreset]


def load_agent_catalog(agent_def_dir: Path) -> ParsedAgentCatalog:
    """Parse one agent-definition root into the canonical catalog."""

    resolved_root = agent_def_dir.resolve()
    tool_adapters: dict[str, ToolAdapter] = {}
    setups: dict[str, dict[str, Path]] = {}
    auths: dict[str, dict[str, Path]] = {}
    presets: dict[Path, AgentPreset] = {}

    tools_root = (resolved_root / "tools").resolve()
    if tools_root.is_dir():
        for tool_dir in sorted(path for path in tools_root.iterdir() if path.is_dir()):
            tool_name = tool_dir.name
            adapter_path = (tool_dir / "adapter.yaml").resolve()
            if adapter_path.is_file():
                tool_adapters[tool_name] = parse_tool_adapter(adapter_path)

            setups_root = (tool_dir / "setups").resolve()
            setups[tool_name] = {
                path.name: path.resolve()
                for path in sorted(setups_root.iterdir())
                if setups_root.is_dir() and path.is_dir()
            }

            auth_root = (tool_dir / "auth").resolve()
            auths[tool_name] = {
                path.name: path.resolve()
                for path in sorted(auth_root.iterdir())
                if auth_root.is_dir() and path.is_dir()
            }

    presets_root = (resolved_root / "presets").resolve()
    if presets_root.is_dir():
        for preset_path in sorted(path for path in presets_root.iterdir() if path.is_file()):
            if preset_path.suffix not in _PRESET_FILE_SUFFIXES:
                continue
            parsed = parse_agent_preset(preset_path)
            presets[parsed.path] = parsed

    return ParsedAgentCatalog(
        agent_def_dir=resolved_root,
        skills_root=(resolved_root / "skills").resolve(),
        tool_adapters=tool_adapters,
        setups=setups,
        auths=auths,
        presets=presets,
    )


def parse_tool_adapter(path: Path) -> ToolAdapter:
    """Parse one tool adapter from the user-facing source layout."""

    payload = _load_mapping_file(path)

    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise ValueError(f"{path}: only schema_version=1 is supported")

    home_selector = _require_mapping(payload, "home_selector", where=str(path))
    launch = _require_mapping(payload, "launch", where=str(path))
    setup_projection = _require_mapping(
        payload,
        "setup_projection",
        where=str(path),
        legacy_key="config_projection",
    )
    skills_projection = _require_mapping(payload, "skills_projection", where=str(path))
    auth_projection = _require_mapping(
        payload,
        "auth_projection",
        where=str(path),
        legacy_key="credential_projection",
    )
    auth_env = _require_mapping(auth_projection, "env", where=str(path))

    raw_launch_metadata = launch.get("metadata", {})
    if raw_launch_metadata is not None and not isinstance(raw_launch_metadata, dict):
        raise ValueError(f"{path}: launch.metadata must be a mapping when set")
    raw_default_tool_params = launch.get("default_tool_params", {})
    launch_defaults = parse_launch_defaults(
        {
            "args": _require_str_list(launch, "args", where=str(path)),
            "tool_params": raw_default_tool_params,
        },
        source=f"{path}:launch.defaults",
    )
    launch_metadata = parse_tool_launch_metadata(
        raw_launch_metadata if raw_launch_metadata is not None else {},
        source=f"{path}:launch.metadata",
    )

    env_injection = _require_mapping(launch, "env_injection", where=str(path))
    env_injection_mode = _require_str(env_injection, "mode", where=str(path))
    if env_injection_mode not in {"home_dotenv", "export_from_env_file"}:
        raise ValueError(
            f"{path}: launch.env_injection.mode must be home_dotenv or export_from_env_file"
        )

    env_file_in_home: str | None = env_injection.get("env_file_in_home")
    if env_file_in_home is not None and not isinstance(env_file_in_home, str):
        raise ValueError(f"{path}: launch.env_injection.env_file_in_home must be a string")

    file_mappings: list[AuthFileMapping] = []
    for idx, raw_mapping in enumerate(auth_projection.get("file_mappings", [])):
        if not isinstance(raw_mapping, dict):
            raise ValueError(f"{path}: file_mappings[{idx}] must be a mapping")
        required = raw_mapping.get("required", True)
        if not isinstance(required, bool):
            raise ValueError(f"{path}: file_mappings[{idx}].required must be a boolean")
        mapping = AuthFileMapping(
            required=required,
            source=_require_str(raw_mapping, "source", where=f"{path}:file_mappings[{idx}]"),
            destination=_require_str(
                raw_mapping,
                "destination",
                where=f"{path}:file_mappings[{idx}]",
            ),
            mode=_require_str(raw_mapping, "mode", where=f"{path}:file_mappings[{idx}]"),
        )
        if mapping.mode not in {"symlink", "copy"}:
            raise ValueError(
                f"{path}: file_mappings[{idx}].mode must be `symlink` or `copy`, "
                f"got {mapping.mode!r}"
            )
        file_mappings.append(mapping)

    skills_mode = _require_str(skills_projection, "mode", where=str(path))
    if skills_mode not in {"symlink", "copy"}:
        raise ValueError(f"{path}: skills_projection.mode must be `symlink` or `copy`")

    adapter = ToolAdapter(
        tool=_require_str(payload, "tool", where=str(path)),
        home_selector_env_var=_require_str(home_selector, "env_var", where=str(path)),
        launch_executable=_require_str(launch, "executable", where=str(path)),
        launch_defaults=launch_defaults,
        launch_metadata=launch_metadata,
        env_injection_mode=env_injection_mode,
        env_file_in_home=env_file_in_home,
        setup_destination=_require_str(setup_projection, "destination", where=str(path)),
        skills_destination=_require_str(skills_projection, "destination", where=str(path)),
        skills_mode=skills_mode,
        auth_files_dir=_require_str(auth_projection, "files_dir", where=str(path)),
        auth_file_mappings=file_mappings,
        auth_env_source=_require_str(auth_env, "source", where=str(path)),
        auth_env_allowlist=_require_str_list(auth_env, "allowlist", where=str(path)),
    )
    adapter.launch_metadata.validate_requested_tool_params(
        tool=adapter.tool,
        tool_params=adapter.launch_defaults.tool_params,
        source=f"{path}: launch.default_tool_params",
    )
    return adapter


def parse_agent_preset(path: Path) -> AgentPreset:
    """Parse one named preset definition."""

    resolved_path = path.resolve()
    payload = _load_mapping_file(resolved_path)
    unknown_fields = sorted(key for key in payload if key not in _PRESET_TOP_LEVEL_FIELDS)
    if unknown_fields:
        joined = ", ".join(unknown_fields)
        raise ValueError(
            f"{resolved_path}: unsupported top-level field(s): {joined}. "
            "Supported fields: role, tool, setup, skills, auth, launch, mailbox, extra."
        )

    preset_name = _preset_name_from_path(resolved_path)
    role_name = _require_str(payload, "role", where=str(resolved_path)).strip()
    tool = _require_str(payload, "tool", where=str(resolved_path)).strip()
    setup = _require_str(payload, "setup", where=str(resolved_path)).strip()
    auth = _optional_non_empty_str(payload.get("auth"), field=f"{resolved_path}:auth")
    launch = _parse_preset_launch(payload.get("launch"), source=str(resolved_path))
    mailbox = _parse_mailbox(payload.get("mailbox"), source=str(resolved_path))
    extra = _parse_extra(payload.get("extra"), source=str(resolved_path))
    gateway_defaults = _parse_gateway_defaults(extra=extra, source=str(resolved_path))

    return AgentPreset(
        path=resolved_path,
        name=preset_name,
        role_name=role_name,
        tool=tool,
        setup=setup,
        skills=_require_str_list(payload, "skills", where=str(resolved_path)),
        auth=auth,
        launch=launch,
        mailbox=mailbox,
        extra=extra,
        gateway_defaults=gateway_defaults,
    )


def resolve_agent_preset(
    *,
    catalog: ParsedAgentCatalog,
    selector: str,
    tool: str,
) -> AgentPreset:
    """Resolve one preset from selector plus tool lane."""

    stripped_selector = selector.strip()
    if not stripped_selector:
        raise ValueError("Launch selector must not be empty.")

    if _is_path_like_selector(stripped_selector):
        preset_path = _resolve_path_like_preset_path(
            selector=stripped_selector,
            agent_def_dir=catalog.agent_def_dir,
        )
    else:
        preset_path = _resolve_default_preset_path(
            catalog=catalog,
            role_name=stripped_selector,
            tool=tool,
        )
    preset = catalog.presets.get(preset_path.resolve())
    if preset is None:
        preset = parse_agent_preset(preset_path)
    return preset


def resolve_explicit_or_named_preset_path(*, agent_def_dir: Path, selector: str) -> Path:
    """Resolve one preset reference from an explicit path or bare preset name."""

    stripped_selector = selector.strip()
    if not stripped_selector:
        raise ValueError("Preset selector must not be empty.")
    if _is_path_like_selector(stripped_selector):
        return _resolve_path_like_preset_path(
            selector=stripped_selector,
            agent_def_dir=agent_def_dir,
        )
    return _resolve_named_preset_path(
        agent_def_dir=agent_def_dir,
        preset_name=stripped_selector,
    )


def _load_mapping_file(path: Path) -> dict[str, Any]:
    """Load one YAML/JSON mapping payload."""

    if not path.exists():
        raise ValueError(f"Missing file: {path}")

    text = path.read_text(encoding="utf-8")
    try:
        import yaml

        loaded = yaml.safe_load(text)
    except Exception:
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse {path} as YAML/JSON: {exc}") from exc

    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected top-level mapping in {path}")
    return loaded


def _require_mapping(
    payload: dict[str, Any],
    key: str,
    *,
    where: str,
    legacy_key: str | None = None,
) -> dict[str, Any]:
    """Require one mapping field, optionally supporting a legacy alias."""

    value = payload.get(key)
    if value is None and legacy_key is not None:
        value = payload.get(legacy_key)
    if not isinstance(value, dict):
        raise ValueError(f"{where}: missing mapping `{key}`")
    return value


def _require_str(payload: dict[str, Any], key: str, *, where: str) -> str:
    """Require one non-empty string field."""

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: missing string `{key}`")
    return value


def _require_str_list(payload: dict[str, Any], key: str, *, where: str) -> list[str]:
    """Require or default one string-list field."""

    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{where}: expected list of strings for `{key}`")
    return value


def _optional_non_empty_str(value: object, *, field: str) -> str | None:
    """Return one optional non-empty string value."""

    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: must be a non-empty string when set")
    return value.strip()


def _parse_operator_prompt_mode(raw_value: object, *, source: str) -> OperatorPromptMode | None:
    """Parse one optional prompt-mode value."""

    if raw_value is None:
        return None
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError(f"{source}: prompt_mode must be a non-empty string when set")
    value = raw_value.strip()
    if value not in {"as_is", "unattended"}:
        raise ValueError(f"{source}: prompt_mode must be `as_is` or `unattended`, got {value!r}")
    return cast(OperatorPromptMode, value)


def _parse_preset_launch(raw_value: object, *, source: str) -> PresetLaunchSettings:
    """Parse one optional preset launch object."""

    if raw_value is None:
        return PresetLaunchSettings()
    if not isinstance(raw_value, dict):
        raise ValueError(f"{source}: launch must be a mapping when set")

    unknown_fields = sorted(
        key for key in raw_value if key not in {"prompt_mode", "overrides", "env_records"}
    )
    if unknown_fields:
        joined = ", ".join(unknown_fields)
        raise ValueError(
            f"{source}: launch supports only `prompt_mode`, `overrides`, and `env_records`, got {joined}"
        )

    overrides_payload = raw_value.get("overrides")
    overrides: LaunchOverrides | None = None
    if overrides_payload is not None:
        overrides = parse_launch_overrides(
            overrides_payload,
            source=f"{source}:launch.overrides",
        )

    env_records = _parse_launch_env_records(
        raw_value.get("env_records"),
        source=f"{source}:launch.env_records",
    )

    return PresetLaunchSettings(
        prompt_mode=_parse_operator_prompt_mode(
            raw_value.get("prompt_mode"),
            source=f"{source}:launch",
        ),
        overrides=overrides,
        env_records=env_records,
    )


def _parse_launch_env_records(raw_value: object, *, source: str) -> dict[str, str]:
    """Parse one optional persistent launch env mapping."""

    if raw_value is None:
        return {}
    if not isinstance(raw_value, dict):
        raise ValueError(f"{source}: env_records must be a mapping when set")

    env_records: dict[str, str] = {}
    for raw_name, raw_value_item in raw_value.items():
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ValueError(f"{source}: env_records keys must be non-empty strings")
        if not isinstance(raw_value_item, str):
            raise ValueError(f"{source}: env_records values must be strings")
        env_records[raw_name.strip()] = raw_value_item
    return env_records


def _parse_mailbox(raw_value: object, *, source: str) -> MailboxDeclarativeConfig | None:
    """Parse one optional mailbox block."""

    try:
        return parse_declarative_mailbox_config(raw_value, source=source)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def _parse_extra(raw_value: object, *, source: str) -> dict[str, Any]:
    """Parse one optional `extra` mapping."""

    if raw_value is None:
        return {}
    if not isinstance(raw_value, dict):
        raise ValueError(f"{source}: extra must be a mapping when set")
    return dict(raw_value)


def _parse_gateway_defaults(
    *,
    extra: dict[str, Any],
    source: str,
) -> BlueprintGatewayDefaults | None:
    """Parse optional gateway defaults from `extra.gateway`."""

    raw_gateway = extra.get("gateway")
    if raw_gateway is None:
        return None
    if not isinstance(raw_gateway, dict):
        raise ValueError(f"{source}: extra.gateway must be a mapping when set")
    try:
        return BlueprintGatewayDefaults.model_validate(raw_gateway)
    except Exception as exc:
        raise ValueError(f"{source}: invalid extra.gateway: {exc}") from exc


def _preset_name_from_path(path: Path) -> str:
    """Derive the preset name from one canonical named-preset path."""

    resolved_path = path.resolve()
    if resolved_path.parent.name != "presets" or resolved_path.suffix not in _PRESET_FILE_SUFFIXES:
        raise ValueError(f"{path}: preset paths must follow presets/<name>.yaml")
    name = resolved_path.stem
    if not name:
        raise ValueError(f"{path}: preset filename stem must not be empty")
    return name


def _is_path_like_selector(selector: str) -> bool:
    """Return whether one selector should be treated as path-like."""

    return (
        "/" in selector
        or "\\" in selector
        or selector.startswith(".")
        or selector.startswith("~")
        or selector.endswith(_PRESET_FILE_SUFFIXES)
    )


def _resolve_path_like_preset_path(*, selector: str, agent_def_dir: Path) -> Path:
    """Resolve one explicit preset path selector."""

    base_path = Path(selector).expanduser()
    if not base_path.is_absolute():
        base_path = (agent_def_dir / base_path).resolve()
    else:
        base_path = base_path.resolve()

    candidates: tuple[Path, ...]
    if base_path.suffix in _PRESET_FILE_SUFFIXES:
        candidates = (base_path,)
    else:
        candidates = tuple(base_path.with_suffix(suffix) for suffix in _PRESET_FILE_SUFFIXES)

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"Could not resolve preset path from selector `{selector}`.")


def _resolve_named_preset_path(*, agent_def_dir: Path, preset_name: str) -> Path:
    """Resolve one preset by bare name under the canonical preset root."""

    presets_root = (agent_def_dir / "presets").resolve()
    base_path = (presets_root / preset_name).resolve()
    candidates: tuple[Path, ...]
    if base_path.suffix in _PRESET_FILE_SUFFIXES:
        candidates = (base_path,)
    else:
        candidates = tuple(base_path.with_suffix(suffix) for suffix in _PRESET_FILE_SUFFIXES)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"Could not resolve preset `{preset_name}` under `{presets_root}`.")


def _resolve_default_preset_path(*, catalog: ParsedAgentCatalog, role_name: str, tool: str) -> Path:
    """Resolve the unique default setup preset for one role/tool pair."""

    matches = sorted(
        preset.path
        for preset in catalog.presets.values()
        if preset.role_name == role_name and preset.tool == tool and preset.setup == "default"
    )
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        joined = ", ".join(str(path) for path in matches)
        raise ValueError(
            f"Multiple named presets matched role `{role_name}` with tool `{tool}` and "
            f"setup `default`: {joined}"
        )
    raise FileNotFoundError(
        f"Could not resolve a native preset for role `{role_name}` with tool `{tool}` "
        f"under `{(catalog.agent_def_dir / 'presets').resolve()}`."
    )
