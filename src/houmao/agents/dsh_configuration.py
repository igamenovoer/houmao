"""Validate explicit DSH model routes and prepare isolated native ACP profiles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import SplitResult, urlsplit

import yaml

_RESERVED_ENVIRONMENT_REFERENCES = frozenset(
    {
        "HOME",
        "PATH",
        "TMUX",
        "TMUX_PANE",
        "TMUX_TMPDIR",
        "DSH_HOME",
        "DSH_AGENTS_HOME",
        "DSH_PERMISSION_MODE",
        "DSH_BUNDLED_SKILL_DIR",
    }
)


class DshConfigurationError(ValueError):
    """Identify an invalid explicit DSH launch configuration without secret values."""


@dataclass(frozen=True)
class DshModel:
    """Carry qualified exact-model capacities and declared reasoning support."""

    id: str
    context_window: int
    max_output_tokens: int
    reasoning: Mapping[str, str] | None


@dataclass(frozen=True)
class DshSetup:
    """Describe one explicit provider route independently of resolved credentials."""

    adapter: str
    protocol: str
    route: str
    base_url_env: str
    api_key_env: str
    models: tuple[DshModel, ...]
    selected_model: str
    skill_roots: tuple[Path, ...]
    mcp_servers: tuple[dict[str, Any], ...]

    @classmethod
    def from_file(cls, path: Path) -> DshSetup:
        """Read the tool-owned YAML or JSON setup document."""

        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            raise DshConfigurationError("Cannot read the DSH setup document") from error
        return cls.from_mapping(data)

    @classmethod
    def from_mapping(cls, data: object) -> DshSetup:
        """Reject ambiguous routes, missing capacities, and implicit reasoning defaults."""

        document = _mapping(data, "setup")
        _fields(
            document,
            {
                "version",
                "provider",
                "models",
                "selected_model",
                "skill_roots",
                "mcp_servers",
                "hmr",
            },
            "setup",
        )
        if document.get("version") != 1 or isinstance(document.get("version"), bool):
            raise DshConfigurationError("DSH setup requires version: 1")
        if document.get("hmr", False) is not False:
            raise DshConfigurationError(
                "Managed DSH supports startup-only configuration; hmr must be false"
            )
        provider = _mapping(document.get("provider"), "provider")
        _fields(
            provider, {"adapter", "protocol", "route", "base_url_env", "api_key_env"}, "provider"
        )
        adapter = _text(provider.get("adapter"), "provider.adapter")
        protocol = _text(provider.get("protocol"), "provider.protocol")
        route = _text(provider.get("route"), "provider.route")
        if (adapter, protocol) not in {("deepseek", "messages"), ("pi-ai", "openai-completions")}:
            raise DshConfigurationError(
                "DSH adapter/protocol must be deepseek/messages or pi-ai/openai-completions"
            )
        if not re.fullmatch(r"[a-z][a-z0-9-]*", route):
            raise DshConfigurationError("DSH provider.route must be a lowercase route identifier")
        if adapter == "deepseek" and route != "deepseek-official":
            raise DshConfigurationError(
                "The native DeepSeek adapter requires route deepseek-official"
            )
        if adapter == "pi-ai" and route == "deepseek-official":
            raise DshConfigurationError("The native DeepSeek route cannot use the pi-ai adapter")
        base_ref = _env_ref(provider.get("base_url_env"), "provider.base_url_env")
        key_ref = _env_ref(provider.get("api_key_env"), "provider.api_key_env")
        if base_ref == key_ref:
            raise DshConfigurationError("DSH endpoint and API key require distinct references")
        models_input = document.get("models")
        if not isinstance(models_input, list) or not models_input:
            raise DshConfigurationError("DSH setup requires an explicit nonempty model catalog")
        models = []
        for index, value in enumerate(models_input):
            model = _mapping(value, f"models[{index}]")
            _fields(model, {"id", "context_window", "max_output_tokens", "reasoning"}, "model")
            identifier = _text(model.get("id"), "model.id")
            context = _positive_int(model.get("context_window"), "model.context_window")
            output = _positive_int(model.get("max_output_tokens"), "model.max_output_tokens")
            if output > context:
                raise DshConfigurationError("DSH model.max_output_tokens exceeds context_window")
            raw_reasoning = model.get("reasoning")
            if raw_reasoning is False:
                reasoning = None
            elif isinstance(raw_reasoning, dict) and raw_reasoning:
                reasoning = {
                    _text(key, "reasoning level"): _text(value, "native reasoning effort")
                    for key, value in raw_reasoning.items()
                }
                if any(not level.isdigit() or str(int(level)) != level for level in reasoning):
                    raise DshConfigurationError(
                        "DSH reasoning keys must be canonical numbered presets"
                    )
                positives = sorted(int(level) for level in reasoning if int(level) > 0)
                if not positives or positives != list(range(1, len(positives) + 1)):
                    raise DshConfigurationError(
                        "DSH positive reasoning presets must be consecutive from 1"
                    )
                if "0" in reasoning and reasoning["0"] != "off":
                    raise DshConfigurationError(
                        "DSH reasoning preset 0 must explicitly disable reasoning"
                    )
                if any(reasoning[str(level)] == "off" for level in positives):
                    raise DshConfigurationError(
                        "DSH positive reasoning presets must enable reasoning"
                    )
                if adapter == "deepseek" and any(
                    value not in {"off", "low", "high", "max"} for value in reasoning.values()
                ):
                    raise DshConfigurationError(
                        "The native DeepSeek reasoning effort is unsupported"
                    )
                if adapter == "pi-ai" and any(
                    value not in {"off", "minimal", "low", "medium", "high", "xhigh", "max"}
                    for value in reasoning.values()
                ):
                    raise DshConfigurationError("The pi-ai native reasoning effort is unsupported")
            else:
                raise DshConfigurationError(
                    "DSH model.reasoning must explicitly be false or a nonempty effort mapping"
                )
            models.append(DshModel(identifier, context, output, reasoning))
        if len({model.id for model in models}) != len(models):
            raise DshConfigurationError("DSH model IDs must be unique")
        selected = _text(document.get("selected_model"), "selected_model")
        if selected not in {model.id for model in models}:
            raise DshConfigurationError("DSH selected_model must identify a declared exact model")
        roots = document.get("skill_roots", [])
        if not isinstance(roots, list):
            raise DshConfigurationError("DSH skill_roots must be a list of absolute directories")
        parsed_roots = tuple(Path(_text(root, "skill root")) for root in roots)
        if any(not root.is_absolute() for root in parsed_roots):
            raise DshConfigurationError("DSH skill_roots must be absolute")
        servers = document.get("mcp_servers", [])
        if not isinstance(servers, list):
            raise DshConfigurationError("DSH mcp_servers must be a list")
        parsed_servers = tuple(_parse_mcp_server(server) for server in servers)
        if len({server["name"] for server in parsed_servers}) != len(parsed_servers):
            raise DshConfigurationError("DSH MCP server names must be unique")
        return cls(
            adapter,
            protocol,
            route,
            base_ref,
            key_ref,
            tuple(models),
            selected,
            parsed_roots,
            parsed_servers,
        )

    def select_model(
        self, model_name: str | None = None, reasoning_level: str | None = None
    ) -> tuple[DshModel, str | None]:
        """Validate common launch selections against the exact declared model catalog."""

        selected = model_name if model_name is not None else self.selected_model
        model = next((model for model in self.models if model.id == selected), None)
        if model is None:
            raise DshConfigurationError(
                "Requested DSH model is not in the configured exact catalog"
            )
        if reasoning_level is None:
            return model, None
        if model.reasoning is None or reasoning_level not in model.reasoning:
            raise DshConfigurationError(
                "Requested DSH reasoning level is not declared for the selected model"
            )
        return model, model.reasoning[reasoning_level]


@dataclass(frozen=True)
class DshPreparedHome:
    """Return private launch inputs separately from public, credential-free provenance."""

    patch_path: Path
    role_path: Path
    persistence_root: Path
    agents_home: Path
    environment: dict[str, str]
    model: str
    provider: str
    metadata: dict[str, Any]
    mcp_servers: tuple[dict[str, Any], ...]


def prepare_dsh_home(
    home_path: Path,
    setup: DshSetup,
    environment: Mapping[str, str],
    role_prompt: str,
    *,
    selected_model: str | None = None,
    reasoning_level: str | None = None,
    skill_roots: Sequence[Path] = (),
    operator_prompt_mode: str = "unattended",
) -> DshPreparedHome:
    """Project an isolated native profile and literal role without installing software.

    Parameters
    ----------
    home_path:
        Managed agent home containing its generated configuration and journal root.
    setup:
        Validated route, exact model catalog, and explicit skill/MCP declarations.
    environment:
        Selected credential environment. Public metadata retains reference names only.
    role_prompt:
        Complete effective native system section, preserved as literal text.
    selected_model, reasoning_level:
        Optional common launch overrides resolved against the exact setup catalog.
    skill_roots:
        Additional existing skill directories selected by managed brain construction.
    operator_prompt_mode:
        ``unattended`` applies the qualified no-question permissions. ``as_is``
        preserves native permission defaults without adding unattended overrides.

    Returns
    -------
    DshPreparedHome
        Private subprocess inputs and credential-free public provenance.

    Raises
    ------
    DshConfigurationError
        Required selected inputs or supported native configuration are invalid.
    """

    if operator_prompt_mode not in {"unattended", "as_is"}:
        raise DshConfigurationError("DSH operator prompt mode must be unattended or as_is")
    model, effort = setup.select_model(selected_model, reasoning_level)
    if effort is None and model.reasoning is not None:
        default_level = "0" if "0" in model.reasoning else min(model.reasoning, key=int)
        effort = model.reasoning[default_level]
    endpoint = environment.get(setup.base_url_env, "").strip()
    key = environment.get(setup.api_key_env, "")
    if not endpoint:
        raise DshConfigurationError(f"DSH launch requires endpoint reference {setup.base_url_env}")
    if not key.strip():
        raise DshConfigurationError(f"DSH launch requires credential reference {setup.api_key_env}")
    parsed = _http_url(endpoint, field="endpoint")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise DshConfigurationError(
            "DSH endpoint cannot contain credentials, query parameters, or fragments"
        )
    home = home_path.resolve()
    roots = tuple(dict.fromkeys([*setup.skill_roots, *(path.resolve() for path in skill_roots)]))
    if any(not root.is_dir() for root in roots):
        raise DshConfigurationError("Every selected DSH skill root must exist as a directory")
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    home.chmod(0o700)
    agents_home = home / "shared-agents"
    agents_home.mkdir(exist_ok=True, mode=0o700)
    persistence = home / "sessions"
    persistence.mkdir(exist_ok=True, mode=0o700)
    role_path = home / "houmao-role.txt"
    _write_private(role_path, role_prompt)
    credentials_path = home / "houmao-empty-credentials.yaml"
    _write_private(credentials_path, "{}\n")
    model_catalog: list[dict[str, Any]] = []
    for entry in setup.models:
        catalog_entry: dict[str, Any] = {
            "id": entry.id,
            "contextWindow": entry.context_window,
            "maxTokens": entry.max_output_tokens,
            "inputModalities": ["text"],
        }
        if setup.adapter == "pi-ai":
            catalog_entry["reasoningEfforts"] = (
                {effort: effort for effort in entry.reasoning.values()}
                if entry.reasoning
                else False
            )
        model_catalog.append(catalog_entry)
    patch: list[dict[str, Any]] = [
        {
            "id": "session-persistence-jsonl",
            "config": {"root": str(persistence), "compression": "none"},
        },
        {"id": "credentials", "config": {"path": str(credentials_path), "watch": False}},
        {
            "id": "skill-filesystem",
            "config": {
                "includeDefaultRoots": False,
                "dshHome": str(home),
                "agentsHome": str(agents_home),
                "customSkillDirs": [str(root) for root in roots],
                "watch": False,
            },
        },
        {"id": "hmr", "disabled": True},
        {"id": "goal-round-driver", "disabled": True},
        {"id": "llm-deepseek-account", "disabled": True},
        {
            "id": "acp",
            "config": {"provider": setup.route, "model": model.id},
        },
    ]
    if operator_prompt_mode == "unattended":
        patch.extend(
            [
                {"id": "approval", "config": {"policy": "never"}},
                {"id": "sandbox-policy", "config": {"mode": "workspace-write"}},
            ]
        )
    if setup.adapter == "deepseek":
        config: dict[str, Any] = {
            "baseURL": endpoint,
            "apiKeyEnv": setup.api_key_env,
            "maxTokens": model.max_output_tokens,
            "defaultContextWindow": model.context_window,
            "models": model_catalog,
        }
        if model.reasoning is None:
            config.update({"thinking": "disabled", "reasoningEffort": "off"})
        elif effort is not None:
            config["reasoningEffort"] = effort
        patch.extend(
            [
                {"id": "llm-deepseek", "config": config},
                {"id": "llm-pi-ai", "config": {"providers": {}}},
            ]
        )
    else:
        provider: dict[str, Any] = {
            "api": "openai-completions",
            "baseURL": endpoint,
            "apiKeyEnv": setup.api_key_env,
            "models": model_catalog,
            "defaultContextWindow": model.context_window,
            "defaultMaxTokens": model.max_output_tokens,
        }
        if effort is not None:
            provider["reasoning"] = effort
        patch.extend(
            [
                {"id": "llm-deepseek", "disabled": True},
                {"id": "llm-pi-ai", "config": {"providers": {setup.route: provider}}},
            ]
        )
    patch_path = home / "houmao-profile.patch.json"
    _write_private(patch_path, json.dumps(patch, ensure_ascii=False, indent=2) + "\n")
    private_env = {
        name: value
        for name, value in environment.items()
        if name
        not in {"DSH_HOME", "DSH_AGENTS_HOME", "DSH_PERMISSION_MODE", "DSH_BUNDLED_SKILL_DIR"}
        and not re.search(r"API_KEY|TOKEN|SECRET|PASSWORD|ACCESS_KEY|BASE_URL", name)
    }
    private_env.update(
        {
            "DSH_HOME": str(home),
            "DSH_AGENTS_HOME": str(agents_home),
            setup.api_key_env: key,
            setup.base_url_env: endpoint,
        }
    )
    metadata: dict[str, Any] = {
        "adapter": setup.adapter,
        "protocol": setup.protocol,
        "provider": setup.route,
        "model": model.id,
        "context_window": model.context_window,
        "max_output_tokens": model.max_output_tokens,
        "base_url_env": setup.base_url_env,
        "api_key_env": setup.api_key_env,
        "reasoning_effort": effort,
        "role_sha256": hashlib.sha256(role_prompt.encode()).hexdigest(),
        "activation": "startup-only",
        "operator_prompt_mode": operator_prompt_mode,
        "journal_format": 4,
        "journal_compression": "none",
    }
    return DshPreparedHome(
        patch_path,
        role_path,
        persistence,
        agents_home,
        private_env,
        model.id,
        setup.route,
        metadata,
        setup.mcp_servers,
    )


def _mapping(value: object, field: str) -> dict[str, Any]:
    """Require a string-keyed configuration object."""

    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise DshConfigurationError(f"DSH {field} must be an object")
    return value


def _fields(value: Mapping[str, Any], allowed: set[str], field: str) -> None:
    """Reject unsupported fields without copying their potentially private values."""

    if set(value) - allowed:
        raise DshConfigurationError(f"DSH {field} contains unsupported fields")


def _text(value: object, field: str) -> str:
    """Require an explicit nonempty text input."""

    if not isinstance(value, str) or not value.strip():
        raise DshConfigurationError(f"DSH {field} must be a nonempty string")
    return value


def _positive_int(value: object, field: str) -> int:
    """Reject absent or inherited model capacities, including booleans."""

    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise DshConfigurationError(f"DSH {field} must be an explicit positive integer")
    return value


def _env_ref(value: object, field: str) -> str:
    """Accept credential names rather than embedded values."""

    result = _text(value, field)
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", result):
        raise DshConfigurationError(f"DSH {field} must name an environment reference")
    if result in _RESERVED_ENVIRONMENT_REFERENCES:
        raise DshConfigurationError(
            f"DSH {field} cannot replace native isolation or process settings"
        )
    return result


def _http_url(value: str, *, field: str) -> SplitResult:
    """Validate routing syntax without including a potentially private URL in errors."""

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise DshConfigurationError(f"DSH {field} must be an absolute HTTP(S) URL") from None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or (port is not None and port == 0)
        or any(ord(character) < 33 or ord(character) == 127 for character in value)
    ):
        raise DshConfigurationError(f"DSH {field} must be an absolute HTTP(S) URL")
    return parsed


def _parse_mcp_server(value: object) -> dict[str, Any]:
    """Validate only the stdio and HTTP transports supported by the pinned ACP build."""

    server = _mapping(value, "MCP server")
    name = _text(server.get("name"), "MCP server.name")
    if any(ord(character) < 32 or ord(character) == 127 for character in name):
        raise DshConfigurationError("DSH MCP server.name contains control characters")
    if "type" not in server:
        _fields(server, {"name", "command", "args", "env"}, "stdio MCP server")
        command = _text(server.get("command"), "MCP server.command")
        if not Path(command).is_absolute() or "\x00" in command:
            raise DshConfigurationError("DSH stdio MCP command must be an absolute path")
        arguments = server.get("args", [])
        if not isinstance(arguments, list) or any(
            not isinstance(argument, str) or "\x00" in argument for argument in arguments
        ):
            raise DshConfigurationError("DSH stdio MCP args must be a list of strings")
        return {
            "name": name,
            "command": command,
            "args": list(arguments),
            "env": _mcp_entries(server.get("env", []), kind="environment"),
        }
    if server["type"] != "http":
        raise DshConfigurationError("DSH MCP supports only ACP stdio or http transports")
    _fields(server, {"name", "type", "url", "headers"}, "HTTP MCP server")
    url = _text(server.get("url"), "MCP server.url")
    _http_url(url, field="HTTP MCP URL")
    return {
        "name": name,
        "type": "http",
        "url": url,
        "headers": _mcp_entries(server.get("headers", []), kind="header"),
    }


def _mcp_entries(value: object, *, kind: str) -> list[dict[str, str]]:
    """Validate ordered ACP environment/header entries without disclosing their values."""

    if not isinstance(value, list):
        raise DshConfigurationError(f"DSH MCP {kind} entries must be a list")
    result: list[dict[str, str]] = []
    names: set[str] = set()
    for raw in value:
        entry = _mapping(raw, f"MCP {kind} entry")
        _fields(entry, {"name", "value"}, f"MCP {kind} entry")
        name = _text(entry.get("name"), f"MCP {kind} entry.name")
        content = entry.get("value")
        if not isinstance(content, str):
            raise DshConfigurationError(f"DSH MCP {kind} entry.value must be a string")
        if kind == "header":
            if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name) or any(
                ord(character) > 255
                or ord(character) == 127
                or (ord(character) < 32 and character != "\t")
                for character in content
            ):
                raise DshConfigurationError("DSH MCP contains an invalid header entry")
        elif "=" in name or "\x00" in name or "\x00" in content:
            raise DshConfigurationError("DSH MCP contains an invalid environment entry")
        identity = name.lower() if kind == "header" else name
        if identity in names:
            raise DshConfigurationError(f"DSH MCP {kind} entries contain duplicate names")
        names.add(identity)
        result.append({"name": name, "value": content})
    return result


def _write_private(path: Path, text: str) -> None:
    """Replace Houmao-owned generated state with owner-only permissions."""

    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
