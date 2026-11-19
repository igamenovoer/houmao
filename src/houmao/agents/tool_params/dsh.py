"""Typed DSH authoring layers and effective model and provider selection."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import re
from typing import Literal, Self
from urllib.parse import SplitResult, urlsplit

from pydantic import (
    AliasGenerator,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel
import yaml

from houmao.agents.dsh_credentials import validate_dsh_env_name
from houmao.agents.tool_params.base import StrictToolParams, ToolParamsAdapter

MATERIALIZED_DSH_TOOL_PARAMS = "houmao-tool-params.yaml"

DSH_THINKING_LEVELS = ("off", "minimal", "low", "medium", "high", "xhigh", "max")
_DEEPSEEK_EFFORTS = {"off", "low", "high", "max"}
_PI_AI_PROTOCOLS = {
    "openai-completions",
    "openai-responses",
    "anthropic-messages",
    "google-generative-ai",
}
_MAX_TIMER_DELAY_MS = 2_147_483_647
_MAX_SAFE_INTEGER = 9_007_199_254_740_991
DshProtocol = Literal[
    "messages",
    "openai-completions",
    "openai-responses",
    "anthropic-messages",
    "google-generative-ai",
]
DshSandboxMode = Literal["read-only", "workspace-write", "danger-full-access"]
DshApprovalPolicy = Literal["ask", "never"]

_COMPAT_FIELDS = {
    "openai-completions": frozenset(
        {
            "supports_store",
            "supports_developer_role",
            "supports_reasoning_effort",
            "supports_usage_in_streaming",
            "supports_finish_reason",
            "max_tokens_field",
            "requires_tool_result_name",
            "requires_assistant_after_tool_result",
            "requires_thinking_as_text",
            "requires_reasoning_content_on_assistant_messages",
            "thinking_format",
            "chat_template_kwargs",
            "chat_template_args",
            "supports_thinking_token_budget",
            "thinking_token_budget_field",
            "vllm_priority",
            "supports_strict_mode",
            "cache_control_format",
            "supports_long_cache_retention",
        }
    ),
    "openai-responses": frozenset(
        {
            "supports_developer_role",
            "supports_max_output_tokens",
            "supports_strict_mode",
            "supports_long_cache_retention",
        }
    ),
    "anthropic-messages": frozenset(
        {
            "supports_eager_tool_input_streaming",
            "supports_long_cache_retention",
            "supports_cache_control_on_tools",
            "supports_temperature",
            "force_adaptive_thinking",
            "allow_empty_signature",
            "supports_strict_tools",
        }
    ),
}


class DshConfigurationError(ValueError):
    """Report an invalid DSH launch configuration without secret values."""


def _nonempty(value: str | None) -> str | None:
    """Require a nonblank string when a partial value is present."""

    if value is not None and not value.strip():
        raise ValueError("must be nonempty")
    return value


def _env_ref(value: str | None) -> str | None:
    """Accept an environment reference outside reserved process settings."""

    if value is not None:
        validate_dsh_env_name(value)
    return value


def validate_http_url(value: str, *, field: str) -> SplitResult:
    """Validate routing syntax without including a potentially private URL in errors."""

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise DshConfigurationError(f"DSH {field} must be an absolute HTTP(S) URL") from None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or port == 0
        or any(ord(character) < 33 or ord(character) == 127 for character in value)
    ):
        raise DshConfigurationError(f"DSH {field} must be an absolute HTTP(S) URL")
    return parsed


class _DshNativeOptions(StrictToolParams):
    """Accept snake_case authoring fields and provide native alias serialization."""

    model_config = ConfigDict(
        allow_inf_nan=False,
        alias_generator=AliasGenerator(serialization_alias=to_camel),
    )


class _DshTemplateVariable(_DshNativeOptions):
    """Refer to a DSH request's current reasoning state in template parameters."""

    model_config = ConfigDict(validate_by_name=True)

    variable: Literal["thinking.enabled", "thinking.effort", "thinking.budget"] = Field(
        alias="$var"
    )
    omit_when_off: bool | None = None


DshTemplateValue = str | int | float | bool | _DshTemplateVariable | None
_TEMPLATE_ARGUMENTS = TypeAdapter(
    dict[str, DshTemplateValue], config=ConfigDict(strict=True, allow_inf_nan=False)
)


class DshCompat(_DshNativeOptions):
    """Represent the authored subset of compatibility options exposed by DSH."""

    supports_store: bool | None = None
    supports_developer_role: bool | None = None
    supports_reasoning_effort: bool | None = None
    supports_usage_in_streaming: bool | None = None
    supports_finish_reason: bool | None = None
    max_tokens_field: Literal["max_completion_tokens", "max_tokens"] | None = None
    requires_tool_result_name: bool | None = None
    requires_assistant_after_tool_result: bool | None = None
    requires_thinking_as_text: bool | None = None
    requires_reasoning_content_on_assistant_messages: bool | None = None
    thinking_format: (
        Literal[
            "openai",
            "deepseek",
            "openrouter",
            "together",
            "baseten",
            "zai",
            "qwen",
            "chat-template",
            "qwen-chat-template",
            "string-thinking",
            "ant-ling",
        ]
        | None
    ) = None
    chat_template_kwargs: dict[str, DshTemplateValue] | None = None
    chat_template_args: dict[str, DshTemplateValue] | None = None
    supports_thinking_token_budget: bool | None = None
    thinking_token_budget_field: (
        Literal["thinking_token_budget", "thinking_budget", "thinking_budget_tokens"] | None
    ) = None
    vllm_priority: int | None = None
    supports_strict_mode: bool | None = None
    cache_control_format: Literal["anthropic"] | None = None
    supports_long_cache_retention: bool | None = None
    supports_max_output_tokens: bool | None = None
    supports_eager_tool_input_streaming: bool | None = None
    supports_cache_control_on_tools: bool | None = None
    supports_temperature: bool | None = None
    force_adaptive_thinking: bool | None = None
    allow_empty_signature: bool | None = None
    supports_strict_tools: bool | None = None

    @field_validator("chat_template_kwargs", "chat_template_args", mode="before")
    @classmethod
    def _validate_template_arguments(cls, value: object) -> object:
        """Keep user-supplied dictionary keys out of validation diagnostics."""

        if value is None:
            return None
        try:
            return _TEMPLATE_ARGUMENTS.validate_python(value)
        except ValidationError:
            raise ValueError(
                "requires a mapping of scalars or native thinking references"
            ) from None

    def validate_protocol(self, protocol: str, *, field: str) -> None:
        """Restrict compatibility options to those configurable on the protocol."""

        if protocol == "messages":
            raise ValueError(f"{field} is unsupported for DeepSeek Messages")
        configured = self.model_dump(exclude_none=True).keys()
        unsupported = configured - _COMPAT_FIELDS.get(protocol, frozenset())
        if unsupported:
            field_name = sorted(unsupported)[0]
            raise ValueError(f"{field}.{field_name} is unsupported for {protocol}")


class DshRetryBackoff(_DshNativeOptions):
    """Describe optional native request retry delay overrides."""

    initial_delay_ms: float | None = Field(default=None, gt=0, le=_MAX_TIMER_DELAY_MS)
    max_delay_ms: float | None = Field(default=None, gt=0, le=_MAX_TIMER_DELAY_MS)
    jitter_ratio: float | None = Field(default=None, ge=0, le=1)


class DshRetryPolicy(_DshNativeOptions):
    """Describe layered normal or unconditional native retry options."""

    mode: Literal["normal", "always"] | None = None
    max_retries: int | None = Field(default=None, ge=0, le=_MAX_SAFE_INTEGER)
    retryable_codes: list[str] | None = Field(default=None, min_length=1)
    backoff: DshRetryBackoff | None = None

    @field_validator("retryable_codes")
    @classmethod
    def _validate_retryable_codes(cls, value: list[str] | None) -> list[str] | None:
        """Reject blank retry codes."""

        if value is not None and any(not code.strip() for code in value):
            raise ValueError("retryable_codes must contain nonempty codes")
        return value

    def validate_effective(self) -> None:
        """Check cross-field bounds after the provider layers have merged."""

        if self.mode is None:
            raise ValueError("provider.retry_policy.mode is required")
        if self.backoff is not None and (
            (self.backoff.initial_delay_ms or 500) > (self.backoff.max_delay_ms or 10_000)
        ):
            raise ValueError("provider.retry_policy.backoff.initial_delay_ms exceeds max_delay_ms")


class DshPartialProvider(StrictToolParams):
    """Represent a partial provider layer."""

    adapter: Literal["deepseek", "pi-ai"] | None = None
    protocol: DshProtocol | None = None
    route: str | None = None
    base_url_env: str | None = None
    api_key_env: str | None = None
    compat: DshCompat | None = None
    retry_policy: DshRetryPolicy | None = None

    _validate_refs = field_validator("base_url_env", "api_key_env")(_env_ref)

    @field_validator("route")
    @classmethod
    def _validate_route(cls, value: str | None) -> str | None:
        """Validate a declared route name."""

        if value is not None and not re.fullmatch(r"[a-z][a-z0-9-]*", value):
            raise ValueError("must be a lowercase route identifier")
        return value


class DshProvider(DshPartialProvider):
    """Describe the complete credential references and native provider route."""

    adapter: Literal["deepseek", "pi-ai"]
    protocol: DshProtocol
    route: str
    base_url_env: str
    api_key_env: str | None = "OPENAI_API_KEY"

    @model_validator(mode="after")
    def _validate_pair(self) -> Self:
        """Require a qualified protocol, route, and credential configuration."""

        if (self.adapter == "deepseek" and self.protocol != "messages") or (
            self.adapter == "pi-ai" and self.protocol not in _PI_AI_PROTOCOLS
        ):
            raise ValueError("provider adapter/protocol must match a supported DSH route")
        if (self.adapter == "deepseek") != (self.route == "deepseek-official"):
            raise ValueError("route deepseek-official is required for the native DeepSeek adapter")
        if self.adapter == "deepseek" and "api_key_env" not in self.model_fields_set:
            raise ValueError("provider.api_key_env is required for DeepSeek Messages")
        if self.api_key_env is None and self.protocol != "openai-completions":
            raise ValueError("provider.api_key_env: null requires pi-ai/openai-completions")
        if self.base_url_env == self.api_key_env:
            raise ValueError("endpoint and API key require distinct references")
        if self.compat is not None:
            self.compat.validate_protocol(self.protocol, field="provider.compat")
        if self.retry_policy is not None:
            self.retry_policy.validate_effective()
        return self


class DshPartialModel(StrictToolParams):
    """Identify an exact model and optionally patch its declared capabilities."""

    id: str
    context_window: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    reasoning_efforts: Literal[False] | dict[str, str | None] | None = None
    name: str | None = None
    input_modalities: list[Literal["text", "image"]] | None = Field(default=None, min_length=1)
    compat: DshCompat | None = None

    _validate_id = field_validator("id", "name")(_nonempty)

    @model_validator(mode="before")
    @classmethod
    def _reject_numbered_reasoning(cls, value: object) -> object:
        """Name the replacement field when an old per-index ladder is supplied."""

        if isinstance(value, dict) and "reasoning" in value:
            raise ValueError("use models[].reasoning_efforts with native thinking slots")
        return value

    @field_validator("reasoning_efforts", mode="before")
    @classmethod
    def _validate_reasoning_form(cls, value: object) -> object:
        """Require the exact false literal or a mapping of native thinking slots."""

        if value is not None and value is not False and not isinstance(value, dict):
            raise ValueError("must be false or a mapping of native thinking slots")
        return value

    @field_validator("reasoning_efforts")
    @classmethod
    def _validate_reasoning(
        cls, value: Literal[False] | dict[str, str | None] | None
    ) -> Literal[False] | dict[str, str | None] | None:
        """Validate native slot names and require a wire value for each positive slot."""

        if isinstance(value, dict) and any(
            slot not in DSH_THINKING_LEVELS
            or (wire is None and slot != "off")
            or (wire is not None and not wire.strip())
            for slot, wire in value.items()
        ):
            raise ValueError(
                "requires native thinking slots and nonempty wire strings for positive slots"
            )
        return value

    @field_validator("input_modalities")
    @classmethod
    def _validate_modalities(cls, value: list[str] | None) -> list[str] | None:
        """Reject repeated native modality names."""

        if value is not None and len(value) != len(set(value)):
            raise ValueError("input_modalities must be unique")
        return value


class DshModel(DshPartialModel):
    """Carry exact-model capacities and complete reasoning support."""

    context_window: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    reasoning_efforts: Literal[False] | dict[str, str | None]

    @property
    def reasoning_slots(self) -> tuple[str, ...]:
        """Return the declared slots in native escalation order."""

        if self.reasoning_efforts is False:
            return ()
        return tuple(slot for slot in DSH_THINKING_LEVELS if slot in self.reasoning_efforts)

    @model_validator(mode="after")
    def _validate_capabilities(self) -> Self:
        """Check capacity bounds and require a positive slot on reasoning models."""

        if self.max_output_tokens > self.context_window:
            raise ValueError("max_output_tokens exceeds context_window")
        if self.reasoning_efforts is not False and not any(
            slot != "off" for slot in self.reasoning_slots
        ):
            raise ValueError("reasoning_efforts requires at least one positive thinking slot")
        return self

    def validate_route(self, provider: DshProvider, *, index: int) -> None:
        """Check protocol-specific compatibility and DeepSeek effort spellings."""

        if self.compat is not None:
            self.compat.validate_protocol(provider.protocol, field=f"models.{index}.compat")
        if provider.adapter != "deepseek" or self.reasoning_efforts is False:
            return
        if any(
            slot not in _DEEPSEEK_EFFORTS or (wire != slot and (slot != "off" or wire is not None))
            for slot, wire in self.reasoning_efforts.items()
        ):
            raise ValueError(
                f"models.{index}.reasoning_efforts must use native DeepSeek wire values"
            )


class DshMcpValue(StrictToolParams):
    """Refer to a complete header or environment value in the private credential bundle."""

    name: str
    env_ref: str

    _validate_ref = field_validator("env_ref")(_env_ref)
    _validate_name = field_validator("name")(_nonempty)


class DshPartialMcpServer(StrictToolParams):
    """Identify an MCP server and optionally patch its transport inputs."""

    name: str
    type: Literal["http"] | None = None
    command: str | None = None
    args: list[str] | None = None
    env: list[DshMcpValue] | None = None
    url: str | None = None
    headers: list[DshMcpValue] | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        """Refuse blank names and control characters."""

        if not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("must be a nonblank MCP name without control characters")
        return value

    @field_validator("command")
    @classmethod
    def _validate_command(cls, value: str | None) -> str | None:
        """Require absolute stdio executable paths."""

        if value is not None and (not Path(value).is_absolute() or "\x00" in value):
            raise ValueError("MCP command must be an absolute path")
        return value

    @field_validator("args")
    @classmethod
    def _validate_args(cls, value: list[str] | None) -> list[str] | None:
        """Reject NUL bytes in process arguments."""

        if value is not None and any("\x00" in argument for argument in value):
            raise ValueError("MCP args cannot contain NUL bytes")
        return value

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str | None) -> str | None:
        """Validate the MCP URL as credential-free HTTP(S) routing metadata."""

        if value is not None:
            parsed = validate_http_url(value, field="MCP URL")
            if parsed.username is not None or parsed.password is not None:
                raise ValueError("MCP URL credentials must use header references")
        return value

    @field_validator("headers", "env")
    @classmethod
    def _validate_entries(
        cls, value: list[DshMcpValue] | None, info: ValidationInfo
    ) -> list[DshMcpValue] | None:
        """Validate native entry names and reject duplicates."""

        if value is None:
            return None
        is_header = info.field_name == "headers"
        names = set()
        for entry in value:
            if is_header:
                if not re.fullmatch(r"[!#$%&'*+.^_\x60|~0-9A-Za-z-]+", entry.name):
                    raise ValueError("MCP headers require valid field names")
            elif not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", entry.name):
                raise ValueError("MCP environment entries require valid variable names")
            identity = entry.name.lower() if is_header else entry.name
            if identity in names:
                raise ValueError("MCP entries contain duplicate names")
            names.add(identity)
        return value


class DshMcpServer(DshPartialMcpServer):
    """Carry one complete MCP declaration without the referenced private values."""

    @model_validator(mode="after")
    def _validate_transport(self) -> Self:
        """Keep HTTP and stdio fields distinct."""

        if self.type == "http":
            if (
                self.url is None
                or self.command is not None
                or self.args is not None
                or self.env is not None
            ):
                raise ValueError("HTTP MCP requires url and accepts only HTTP fields")
        elif self.command is None or self.url is not None or self.headers is not None:
            raise ValueError("stdio MCP requires command and accepts only stdio fields")
        return self


class DshPermissionParams(StrictToolParams):
    """Describe independent authored sandbox and approval fields."""

    sandbox: DshSandboxMode | None = Field(default=None, exclude_if=lambda value: value is None)
    approval: DshApprovalPolicy | None = Field(default=None, exclude_if=lambda value: value is None)

    @field_validator("sandbox", "approval")
    @classmethod
    def _reject_null(cls, value: str | None) -> str:
        """Require a supported native value when the author supplies a field."""

        if value is None:
            raise ValueError("omit the field to use the applicable launch default")
        return value


class DshPartialToolParams(StrictToolParams):
    """Represent one secret-free, partially specified DSH configuration layer."""

    provider: DshPartialProvider | None = None
    models: Sequence[DshPartialModel] | None = None
    skill_roots: list[str] | None = None
    mcp_servers: Sequence[DshPartialMcpServer] | None = None
    permissions: DshPermissionParams = Field(default_factory=DshPermissionParams)

    @model_validator(mode="before")
    @classmethod
    def _reject_legacy_and_reserved_fields(cls, value: object) -> object:
        """Identify retired setup syntax and the managed activation boundary."""

        if isinstance(value, dict) and ("version" in value or "selected_model" in value):
            raise ValueError("use tool_params with model.name instead of legacy dsh-setup.yaml")
        if isinstance(value, dict) and "hmr" in value:
            raise ValueError(
                "DSH reserves hmr for startup-only configuration. "
                "Omit it and use Houmao refresh or relaunch to activate native changes."
            )
        return value

    @field_validator("skill_roots")
    @classmethod
    def _validate_roots(cls, value: list[str] | None) -> list[str] | None:
        """Require absolute skill paths."""

        if value is not None and any(not Path(root).is_absolute() for root in value):
            raise ValueError("must be a list of absolute directories")
        return value

    @model_validator(mode="after")
    def _validate_identities(self) -> Self:
        """Reject repeated identities even within a single partial layer."""

        if self.models is not None and len({model.id for model in self.models}) != len(self.models):
            raise ValueError("DSH model IDs must be unique")
        if self.mcp_servers is not None and len({s.name for s in self.mcp_servers}) != len(
            self.mcp_servers
        ):
            raise ValueError("DSH MCP server names must be unique")
        return self


class DshEffectiveToolParams(DshPartialToolParams):
    """Describe a complete provider route, native MCP declarations, and exact-model catalog."""

    provider: DshProvider
    models: list[DshModel] = Field(min_length=1)
    skill_roots: list[str] = Field(default_factory=list)
    mcp_servers: list[DshMcpServer] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_models(self) -> Self:
        """Validate each model against the effective provider route."""

        for index, model in enumerate(self.models):
            model.validate_route(self.provider, index=index)
        return self

    @property
    def adapter(self) -> str:
        """Return the selected adapter."""

        return self.provider.adapter

    @property
    def protocol(self) -> str:
        """Return the selected wire protocol."""

        return self.provider.protocol

    @property
    def route(self) -> str:
        """Return the selected native provider route."""

        return self.provider.route

    @property
    def base_url_env(self) -> str:
        """Return the selected endpoint reference."""

        return self.provider.base_url_env

    @property
    def api_key_env(self) -> str | None:
        """Return the selected API-key reference."""

        return self.provider.api_key_env

    @property
    def mcp_env_refs(self) -> frozenset[str]:
        """Return credential names referenced by MCP without exposing their values."""

        return frozenset(
            entry.env_ref
            for server in self.mcp_servers
            for entry in (server.headers or []) + (server.env or [])
        )

    @classmethod
    def from_file(cls, path: Path) -> Self:
        """Read current, effective tool parameters from the managed home."""

        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError):
            raise DshConfigurationError(f"Cannot read DSH {MATERIALIZED_DSH_TOOL_PARAMS}") from None
        if (
            path.name == MATERIALIZED_DSH_TOOL_PARAMS
            and isinstance(data, dict)
            and data.get("hmr") is False
        ):
            # Earlier Houmao versions recorded this derived flag in the runtime projection.
            data.pop("hmr")
        return cls.from_mapping(data)

    @classmethod
    def from_mapping(cls, data: object) -> Self:
        """Validate the effective schema with value-free diagnostics."""

        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            diagnostics = exc.errors(include_url=False, include_context=False, include_input=False)
            error = diagnostics[0]
            path = ".".join(
                str(part)
                if isinstance(part, int)
                or part in cls.model_fields
                or part
                in {
                    "adapter",
                    "protocol",
                    "route",
                    "base_url_env",
                    "api_key_env",
                    "id",
                    "context_window",
                    "max_output_tokens",
                    "reasoning_efforts",
                    "input_modalities",
                    "retry_policy",
                    "initial_delay_ms",
                    "max_delay_ms",
                    "jitter_ratio",
                    "backoff",
                    "max_retries",
                    "retryable_codes",
                    "mode",
                    "compat",
                    "type",
                    "name",
                    "env_ref",
                    "args",
                    "env",
                    "headers",
                    "command",
                    "url",
                    "sandbox",
                    "approval",
                }
                | DshCompat.model_fields.keys()
                else "<field>"
                for part in error["loc"]
            )
            raise DshConfigurationError(
                f"DSH tool_params {path or 'schema'}: {error['msg']}"
            ) from None

    def select_model(
        self, model_name: str | None = None, reasoning_level: str | None = None
    ) -> tuple[DshModel, str | None]:
        """Select the explicit name or infer the only catalog entry."""

        if model_name is None and len(self.models) == 1:
            model_name = self.models[0].id
        if model_name is None:
            raise DshConfigurationError(
                "DSH model.name is required for a catalog with multiple models"
            )
        model = next((model for model in self.models if model.id == model_name), None)
        if model is None:
            raise DshConfigurationError(
                "Requested DSH model is not in the configured exact catalog"
            )
        if reasoning_level is None:
            return model, None
        if reasoning_level not in model.reasoning_slots:
            raise DshConfigurationError(
                "Requested DSH reasoning level is not declared for the selected model"
            )
        return model, reasoning_level


class DshToolParamsAdapter(ToolParamsAdapter[DshPartialToolParams, DshEffectiveToolParams]):
    """Merge DSH authoring layers and validate supported launch surfaces."""

    partial_model = DshPartialToolParams
    effective_model = DshEffectiveToolParams
    keyed_lists = {"models": "id", "mcp_servers": "name"}

    def prepare_launch(self, effective: DshEffectiveToolParams, *, backend: str) -> tuple[str, ...]:
        """Validate the backend before native configuration is applied."""

        if backend not in {"raw_launch", "dsh_headless", "dsh_acp", "dsh_web"}:
            raise DshConfigurationError("DSH tool_params require a DSH launch backend")
        if backend == "dsh_headless" and effective.mcp_servers:
            declarations = ", ".join(
                f"{server.name!r} ({server.type or 'stdio'})" for server in effective.mcp_servers
            )
            raise DshConfigurationError(
                f"DSH headless cannot project ACP MCP declarations {declarations} to the native CLI."
            )
        if backend == "dsh_web" and effective.mcp_servers:
            raise DshConfigurationError(
                f"DSH tool_params MCP declarations are unsupported by backend {backend!r}."
            )
        return ()
