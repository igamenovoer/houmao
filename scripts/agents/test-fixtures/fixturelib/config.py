"""Resolve secret-free fixture descriptors and explicit local value references."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
from typing import Any, Literal, Mapping
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError
import yaml

from houmao.agents.dsh_configuration import DshEffectiveToolParams
from houmao.agents.realm_controller.errors import LaunchPlanError
from houmao.agents.realm_controller.run_modes import RunMode, RunModeSelection, resolve_run_mode

Client = Literal["claude", "codex", "kimi", "dsh"]
Surface = Literal["raw", "manager", "passive-server"]
Protocol = Literal["anthropic_messages", "openai_responses", "openai_chat", "google_generative_ai"]
DshProtocol = Literal[
    "messages",
    "anthropic-messages",
    "openai-responses",
    "openai-completions",
    "google-generative-ai",
]
DSH_ENDPOINT_PROTOCOL: dict[DshProtocol, Protocol] = {
    "messages": "anthropic_messages",
    "anthropic-messages": "anthropic_messages",
    "openai-responses": "openai_responses",
    "openai-completions": "openai_chat",
    "google-generative-ai": "google_generative_ai",
}
REPO_ROOT = Path(__file__).resolve().parents[4]
CLIENT_PROTOCOL: dict[Client, Protocol] = {
    "claude": "anthropic_messages",
    "codex": "openai_responses",
    "kimi": "openai_chat",
    "dsh": "anthropic_messages",
}
HOME_VARIABLE = {
    "claude": "CLAUDE_CONFIG_DIR",
    "codex": "CODEX_HOME",
    "kimi": "KIMI_CODE_HOME",
    "dsh": "DSH_HOME",
}
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


class FixtureError(ValueError):
    """A fixture input cannot be represented safely or completely."""


class EndpointReference(BaseModel):
    """Name the environment reference supplying a protocol's client base URL."""

    model_config = ConfigDict(extra="forbid", strict=True)
    base_url_env: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")


class MetadataReferences(BaseModel):
    """Describe optional model metadata references without model-specific defaults."""

    model_config = ConfigDict(extra="forbid", strict=True)
    context_window_env: str | None = None
    max_output_tokens_env: str | None = None
    dsh_reasoning_env: str | None = None
    dsh_compat_env: str | None = None
    capabilities_env: str | None = None
    reasoning_key_env: str | None = None
    reasoning_effort_env: str | None = None


class CaseDescriptor(BaseModel):
    """Versioned generic API case descriptor."""

    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1]
    case: Literal["self-hosted", "cloud-api"]
    service: str | None = None
    model_env: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    api_key_env: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    endpoints: dict[Protocol, EndpointReference]
    metadata: MetadataReferences = Field(default_factory=MetadataReferences)
    dsh: DshRoute | None = None


class DshRoute(BaseModel):
    """Declare the exact DSH adapter, protocol, and provider route for a case."""

    model_config = ConfigDict(extra="forbid", strict=True)
    adapter: Literal["deepseek", "pi-ai"]
    protocol: DshProtocol
    route: str

    @property
    def base_url_env(self) -> str:
        """Return the native endpoint role used by fixture bundles."""

        return "DEEPSEEK_BASE_URL_ANTHROPIC" if self.adapter == "deepseek" else "OPENAI_BASE_URL"

    @property
    def api_key_env(self) -> str:
        """Return the native API-key role used by authenticated fixture bundles."""

        return "DEEPSEEK_API_KEY" if self.adapter == "deepseek" else "OPENAI_API_KEY"


class ModelOptions(BaseModel):
    """Explicit model settings that can be projected into supported clients."""

    model_config = ConfigDict(extra="forbid", strict=True)
    context_window: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    dsh_reasoning: dict[str, str | None] | Literal[False] | None = None
    dsh_compat: dict[str, Any] | None = None
    capabilities: list[Literal["tool_use", "thinking", "image_in"]] = Field(
        default_factory=lambda: ["tool_use"]
    )
    reasoning_key: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    reasoning_effort: str | None = Field(default=None, min_length=1)
    support_efforts: list[str] = Field(default_factory=list)

    @property
    def kimi_effort_catalog(self) -> list[str]:
        """Return the effort order used by the generated native Kimi config."""

        if self.support_efforts:
            return self.support_efforts
        return [self.reasoning_effort] if self.reasoning_effort else []


class ResolvedConfig(BaseModel):
    """Selected launch inputs, keeping secret values out of serialization."""

    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    case: Literal["self-hosted", "cloud-api"] | None = None
    client: Client
    mode: RunMode
    surface: Surface
    operator_prompt_mode: Literal["unattended", "as_is"] = "unattended"
    system_skill_policy: Literal["default", "none"] = "default"
    auth_method: Literal["api-key", "endpoint-only", "native-login"] = "api-key"
    model: str | None = None
    protocol: Protocol | None = None
    base_url: str | None = None
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(""), exclude=True)
    model_options: ModelOptions = Field(default_factory=ModelOptions)
    reasoning_level: int | None = Field(default=None, ge=0)
    native_bundle: Path | None = Field(default=None, exclude=True)
    dsh: DshRoute | None = None

    def summary(self) -> dict[str, object]:
        """Return a serializable description without credential values or files."""

        return self.model_dump(mode="json", exclude={"api_key", "native_bundle"})

    def selection(self) -> RunModeSelection:
        """Resolve the selected fixture mode through the runtime support matrix."""

        return fixture_run_mode(self.client, self.mode, self.surface)

    def dsh_tool_params(self) -> dict[str, Any]:
        """Return the native-aligned tool parameters shared by raw and managed runs."""

        if self.dsh is None:
            raise FixtureError("DSH fixtures require an explicit adapter and protocol")
        model = {
            "id": self.model,
            "context_window": self.model_options.context_window,
            "max_output_tokens": self.model_options.max_output_tokens,
            "reasoning_efforts": self.model_options.dsh_reasoning,
        }
        if self.model_options.dsh_compat is not None:
            model["compat"] = self.model_options.dsh_compat
        return {
            "provider": {
                "adapter": self.dsh.adapter,
                "protocol": self.dsh.protocol,
                "route": self.dsh.route,
                "base_url_env": self.dsh.base_url_env,
                "api_key_env": None
                if self.auth_method == "endpoint-only"
                else self.dsh.api_key_env,
            },
            "models": [model],
        }


def read_env_file(path: Path | None) -> dict[str, str]:
    """Read literal env assignments without expansion or shell execution."""

    if path is None:
        return {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise FixtureError("Cannot read the selected env file") from exc
    result: dict[str, str] = {}
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].lstrip()
        name, separator, raw = stripped.partition("=")
        name = name.strip()
        if not separator or not _ENV_NAME.fullmatch(name):
            raise FixtureError(f"Unsupported env assignment at line {number}")
        if any(marker in raw for marker in ("$(", "`", "${", "\x00")):
            raise FixtureError(f"Unsupported env syntax at line {number} for {name}")
        try:
            values = shlex.split(raw.strip(), comments=True, posix=True)
        except ValueError as exc:
            raise FixtureError(f"Invalid env quoting at line {number} for {name}") from exc
        if len(values) > 1:
            raise FixtureError(f"Quote whitespace in env value at line {number} for {name}")
        result[name] = values[0] if values else ""
    return result


def load_descriptor(path: Path) -> CaseDescriptor:
    """Validate the current descriptor shape without including input values in errors."""

    try:
        result = CaseDescriptor.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, yaml.YAMLError, ValidationError) as exc:
        raise FixtureError("Invalid case descriptor; check its fields and schema version") from exc
    for name in result.metadata.model_dump().values():
        if name is not None and not _ENV_NAME.fullmatch(name):
            raise FixtureError("Invalid model metadata environment reference")
    return result


def _base_url(value: str, protocol: Protocol, client: Client) -> str:
    """Validate a client base URL while preserving its configured version prefix."""

    parts = urlsplit(value)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
        or any(char.isspace() for char in value)
    ):
        raise FixtureError("Endpoint must be an HTTP(S) base URL without credentials or query")
    if parts.path.rstrip("/").endswith(("/messages", "/responses", "/chat/completions")):
        raise FixtureError("Supply a client base URL, not a complete API request URL")
    if (
        client == "claude"
        and protocol == "anthropic_messages"
        and parts.path.rstrip("/").endswith("/v1")
    ):
        raise FixtureError("Claude base URL must be the root before its appended /v1/messages")
    return value.rstrip("/")


def fixture_run_mode(client: Client, mode: RunMode | None, surface: Surface) -> RunModeSelection:
    """Resolve a fixture lane and enforce the passive endpoint's headless mode."""

    if surface == "passive-server" and mode not in {None, "headless"}:
        raise FixtureError(
            "Passive-server birth supports headless mode; use manager for other modes"
        )
    if surface == "raw" and mode == "service":
        raise FixtureError("Persistent service fixtures require the manager surface")
    if surface == "raw" and client == "kimi" and mode == "web":
        raise FixtureError("Kimi Web fixtures require the manager surface")
    if mode is None and surface != "passive-server":
        mode = "web" if client == "dsh" else "headless"
    try:
        return resolve_run_mode(
            client,
            mode=mode,
            entrypoint="passive_headless" if surface == "passive-server" else "project",
        )
    except LaunchPlanError as exc:
        raise FixtureError(str(exc)) from exc


def validate_reasoning_level(
    config: ResolvedConfig,
    *,
    dsh_tool_params: DshEffectiveToolParams | None = None,
) -> None:
    """Require an exact manager preset before preparation allocates a run."""

    from houmao.agents.kimi_configuration import load_kimi_config
    from houmao.agents.model_mapping_policy import resolve_reasoning_mapping

    level = config.reasoning_level
    if level is None:
        return
    if config.surface != "manager":
        raise FixtureError("--reasoning-level requires --surface manager")
    if config.client == "dsh" and config.model_options.dsh_reasoning is False:
        raise FixtureError("--reasoning-level requires declared DSH reasoning slots")

    kimi_config = None
    try:
        if config.client == "kimi":
            if config.native_bundle is not None:
                kimi_config = load_kimi_config(config.native_bundle / "files/config.toml")
            else:
                kimi_config = {
                    "default_model": config.model,
                    "models": {
                        config.model: {
                            "capabilities": config.model_options.capabilities,
                            "support_efforts": config.model_options.kimi_effort_catalog,
                        }
                    },
                }
        mapping = resolve_reasoning_mapping(
            tool=config.client,
            requested_level=level,
            model_name=config.model,
            kimi_config=kimi_config,
            dsh_tool_params=dsh_tool_params,
        )
    except ValueError:
        raise FixtureError(
            f"--reasoning-level {level} is unavailable for the selected {config.client} model; "
            "check its declared reasoning presets"
        ) from None
    if mapping["saturated"]:
        raise FixtureError(
            f"--reasoning-level {level} exceeds the highest {config.client} preset "
            f"({mapping['effective_level']}) for the selected model"
        )


def resolve_config(
    *,
    case: str,
    client: Client,
    mode: RunMode | None = None,
    surface: Surface = "manager",
    operator_prompt_mode: Literal["unattended", "as_is"] = "unattended",
    system_skill_policy: Literal["default", "none"] = "default",
    model: str | None = None,
    base_url: str | None = None,
    env_file: Path | None = None,
    process_env: Mapping[str, str] | None = None,
    descriptor_path: Path | None = None,
    context_window: int | None = None,
    max_output_tokens: int | None = None,
    dsh_reasoning: str | None = None,
    dsh_compat: str | None = None,
    dsh_protocol: DshProtocol | None = None,
    capabilities: list[str] | None = None,
    reasoning_key: str | None = None,
    reasoning_effort: str | None = None,
    support_efforts: list[str] | None = None,
    reasoning_level: int | None = None,
) -> ResolvedConfig:
    """Resolve one explicit API configuration for raw or managed preparation."""

    if case not in {"self-hosted", "cloud-api"}:
        raise FixtureError("Select case self-hosted or cloud-api")
    if support_efforts is not None and client != "kimi":
        raise FixtureError("--support-effort requires --client kimi")
    if reasoning_level is not None and surface != "manager":
        raise FixtureError("--reasoning-level requires --surface manager")
    if reasoning_level is not None and reasoning_level < 0:
        raise FixtureError("--reasoning-level must be nonnegative")
    if client == "dsh" and env_file is None and process_env is None and case == "cloud-api":
        raise FixtureError("Cloud DSH requires an explicitly selected --env-file")
    selection = fixture_run_mode(client, mode, surface)
    descriptor = load_descriptor(
        descriptor_path or REPO_ROOT / "tests/fixtures/agent-launch" / f"{case}.yaml"
    )
    if descriptor.case != case:
        raise FixtureError("Descriptor case does not match the selected case")
    # DSH never discovers ambient credentials. Explicit synthetic process inputs
    # remain available to hermetic callers; other clients retain their precedence.
    inherited = (
        {}
        if client == "dsh" and process_env is None
        else dict(os.environ if process_env is None else process_env)
    )
    if client == "dsh" and env_file is not None and env_file.resolve().is_relative_to(REPO_ROOT):
        raise FixtureError("DSH credential env files must remain outside the checkout")
    env = {**read_env_file(env_file), **inherited}
    selected_model = model if model is not None else env.get(descriptor.model_env)
    if not selected_model or not selected_model.strip():
        raise FixtureError(f"Supply --model or {descriptor.model_env}")
    if "\n" in selected_model or "\x00" in selected_model:
        raise FixtureError("Model must be a nonempty single-line identifier")
    dsh_route = descriptor.dsh if client == "dsh" else None
    if client == "dsh" and dsh_route is None:
        raise FixtureError("Selected case must explicitly declare its DSH adapter/protocol/route")
    if dsh_route is not None and dsh_protocol is not None:
        dsh_route = dsh_route.model_copy(update={"protocol": dsh_protocol})
    protocol = DSH_ENDPOINT_PROTOCOL[dsh_route.protocol] if dsh_route else CLIENT_PROTOCOL[client]
    endpoint = descriptor.endpoints.get(protocol)
    if endpoint is None and base_url is None:
        raise FixtureError(f"Selected case does not declare required protocol {protocol}")
    url = base_url if base_url is not None else env.get(endpoint.base_url_env) if endpoint else None
    if not url:
        assert endpoint is not None
        raise FixtureError(f"Supply --base-url or {endpoint.base_url_env} for {protocol}")
    key = env.get(descriptor.api_key_env, "")
    endpoint_only = (
        case == "self-hosted"
        and dsh_route is not None
        and dsh_route.adapter == "pi-ai"
        and dsh_route.protocol == "openai-completions"
        and not key.strip()
    )
    if not key.strip() and (case == "cloud-api" or (dsh_route is not None and not endpoint_only)):
        raise FixtureError(f"Supply nonempty {descriptor.api_key_env}")
    if any(char in key for char in ("\n", "\r", "\x00")):
        raise FixtureError(f"Credential reference {descriptor.api_key_env} must be single-line")

    def metadata(name: str) -> str | None:
        """Read one explicitly declared model metadata reference."""

        reference = getattr(descriptor.metadata, name + "_env")
        return (env.get(reference) or None) if reference else None

    raw_context = metadata("context_window")
    raw_output = metadata("max_output_tokens")
    raw_reasoning = dsh_reasoning if dsh_reasoning is not None else metadata("dsh_reasoning")
    raw_compat = dsh_compat if dsh_compat is not None else metadata("dsh_compat")
    selected_effort = (
        reasoning_effort if reasoning_effort is not None else metadata("reasoning_effort")
    )
    if selected_effort is not None and (
        not selected_effort.strip()
        or (client != "kimi" and not re.fullmatch(r"[A-Za-z0-9_-]+", selected_effort))
    ):
        raise FixtureError("Invalid model metadata; check the reasoning effort label")
    try:
        selected_context = (
            context_window
            if context_window is not None
            else (int(raw_context) if raw_context else None)
        )
        options = ModelOptions.model_validate(
            {
                "context_window": selected_context,
                "max_output_tokens": max_output_tokens
                if max_output_tokens is not None
                else (int(raw_output) if raw_output else None),
                "dsh_reasoning": json.loads(raw_reasoning) if raw_reasoning is not None else None,
                "dsh_compat": json.loads(raw_compat) if raw_compat is not None else None,
                "capabilities": capabilities
                if capabilities is not None
                else (
                    metadata("capabilities").split(",")
                    if metadata("capabilities")
                    else ["tool_use"]
                ),
                "reasoning_key": reasoning_key
                if reasoning_key is not None
                else metadata("reasoning_key"),
                "reasoning_effort": selected_effort,
                "support_efforts": support_efforts or [],
            }
        )
    except (ValueError, ValidationError) as exc:
        raise FixtureError(
            "Invalid model metadata; check capacity, capabilities, reasoning, and DSH compat"
        ) from exc
    if client == "kimi" and options.context_window is None:
        raise FixtureError(
            "Kimi requires --context-window or its configured context-window reference"
        )
    if client == "kimi":
        efforts = options.support_efforts
        if any(not effort.strip() for effort in efforts) or len(set(efforts)) != len(efforts):
            raise FixtureError("Kimi --support-effort labels must be nonempty and unique")
        if efforts and options.reasoning_effort and options.reasoning_effort not in efforts:
            raise FixtureError("Kimi --reasoning-effort must appear in the ordered effort catalog")
    result = ResolvedConfig(
        case=case,
        client=client,
        mode=selection.mode,
        surface=surface,
        operator_prompt_mode=operator_prompt_mode,
        system_skill_policy=system_skill_policy,
        auth_method="endpoint-only" if endpoint_only else "api-key",
        model=selected_model,
        protocol=protocol,
        base_url=_base_url(url, protocol, client),
        api_key=SecretStr(key or ("" if endpoint_only else "EMPTY")),
        model_options=options,
        reasoning_level=reasoning_level,
        dsh=dsh_route,
    )
    dsh_tool_params = None
    if client == "dsh":
        if (
            options.context_window is None
            or options.max_output_tokens is None
            or options.dsh_reasoning is None
        ):
            raise FixtureError(
                "DSH requires explicit --context-window, --max-output-tokens, and --dsh-reasoning "
                "or the case's declared metadata references"
            )
        try:
            dsh_tool_params = DshEffectiveToolParams.from_mapping(result.dsh_tool_params())
        except ValueError as exc:
            raise FixtureError("Invalid explicit DSH route or model metadata") from exc
    validate_reasoning_level(result, dsh_tool_params=dsh_tool_params)
    return result
