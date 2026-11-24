"""Environment ownership for managed Kimi launches."""

from collections.abc import Iterable
from typing import Final

_CONFIG_FIELDS: Final = {
    "KIMI_MODEL_NAME": "default_model and models.<alias>.model",
    "KIMI_MODEL_PROVIDER_TYPE": "providers.<provider>.type",
    "KIMI_MODEL_BASE_URL": "providers.<provider>.base_url",
    "KIMI_MODEL_MAX_CONTEXT_SIZE": "models.<alias>.max_context_size",
    "KIMI_MODEL_MAX_OUTPUT_SIZE": "models.<alias>.max_output_size",
    "KIMI_MODEL_CAPABILITIES": "models.<alias>.capabilities",
    "KIMI_MODEL_DISPLAY_NAME": "models.<alias>.display_name",
    "KIMI_MODEL_REASONING_KEY": "models.<alias>.reasoning_key",
    "KIMI_MODEL_ADAPTIVE_THINKING": "models.<alias>.adaptive_thinking",
    "KIMI_MODEL_THINKING_EFFORT": "thinking.effort and models.<alias>.support_efforts",
    "KIMI_MODEL_THINKING_KEEP": "thinking.keep",
    "KIMI_MODEL_DEFAULT_THINKING": "thinking.enabled",
    "KIMI_MODEL_THINKING_MODE": "thinking.enabled",
    "KIMI_DISABLE_TELEMETRY": "telemetry",
    "KIMI_CODE_BASE_URL": "providers.<provider>.base_url",
    "KIMI_CODE_OAUTH_HOST": "providers.<provider>.oauth.oauth_host",
    "KIMI_OAUTH_HOST": "providers.<provider>.oauth.oauth_host",
    "KIMI_LOOP_MAX_STEPS_PER_TURN": "loop_control.max_steps_per_turn",
    "KIMI_LOOP_MAX_ATTEMPTS_PER_STEP": "loop_control.max_attempts_per_step",
    "KIMI_LOOP_MAX_RETRIES_PER_STEP": "loop_control.max_attempts_per_step",
    "KIMI_CODE_BACKGROUND_KEEP_ALIVE_ON_EXIT": "task.keep_alive_on_exit or background.keep_alive_on_exit",
    "KIMI_CODE_BACKGROUND_MAX_RUNNING_TASKS": "task.max_running_tasks or background.max_running_tasks",
    "KIMI_CODE_BACKGROUND_BASH_TASK_TIMEOUT_S": "task.bash_task_timeout_s",
    "KIMI_CODE_BACKGROUND_PRINT_BACKGROUND_MODE": "task.print_background_mode",
    "KIMI_CODE_BACKGROUND_PRINT_WAIT_CEILING_S": "task.print_wait_ceiling_s",
    "KIMI_CODE_BACKGROUND_PRINT_MAX_TURNS": "task.print_max_turns",
    "KIMI_MCP_STARTUP_TIMEOUT_MS": "mcp.startup_timeout_ms",
    "KIMI_MCP_TOOL_TIMEOUT_MS": "mcp.tool_timeout_ms",
    "KIMI_MCP_RECONNECT_INITIAL_DELAY_MS": "mcp.reconnect_initial_delay_ms",
    "KIMI_MCP_RECONNECT_MAX_DELAY_MS": "mcp.reconnect_max_delay_ms",
    "KIMI_CODE_IDENTITY_NAME": "identity.name",
    "KIMI_CODE_IDENTITY_SLUG": "identity.slug",
    "KIMI_CODE_BUILTIN_PRODUCT_SKILLS": "builtin_product_skills",
    "KIMI_IMAGE_MAX_EDGE_PX": "image.max_edge_px",
    "KIMI_IMAGE_READ_BYTE_BUDGET": "image.read_byte_budget",
    "KIMI_CODE_WATCH": "watch.enabled",
    "KIMI_CODE_GLOBAL_SEARCH": "database.global_search",
    "KIMI_CODE_SEARCH_WORKER": "database.search",
    "KIMI_CODE_PERSISTENCE_MINIDB_READMODEL": "database.base",
    "KIMI_WEB_SEARCH_BASE_URL": "services.moonshot_search.base_url",
    "KIMI_WEB_SEARCH_API_KEY": "services.moonshot_search.api_key",
    "KIMI_WEB_FETCH_BASE_URL": "services.moonshot_fetch.base_url",
    "KIMI_WEB_FETCH_API_KEY": "services.moonshot_fetch.api_key",
    "KIMI_SUBAGENT_TIMEOUT_MS": "subagent.timeout_ms",
    "KIMI_CODE_SWARM_TIMEOUT_MS": "swarm.timeout_ms",
    "KIMI_TOKEN_COUNTING_STRATEGY": "token_counting.strategy",
    "KIMI_CODE_EXPERIMENTAL_TOWER": "experimental.tower",
}

KIMI_CONFIG_ENV_NAMES: Final = frozenset(_CONFIG_FIELDS)
KIMI_API_KEY_ENV: Final = "KIMI_MODEL_API_KEY"
KIMI_PRIVATE_ENV_NAMES: Final = frozenset(
    {
        KIMI_API_KEY_ENV,
        "KIMI_MODEL_TEMPERATURE",
        "KIMI_MODEL_TOP_P",
        "KIMI_MODEL_MAX_TOKENS",
        "KIMI_MODEL_MAX_COMPLETION_TOKENS",
    }
)


def reject_kimi_config_env(env: Iterable[str], *, source: str) -> None:
    """Reject explicitly authored Kimi settings that belong in native TOML."""

    for name in env:
        field = _CONFIG_FIELDS.get(name.strip())
        if field is not None:
            raise ValueError(
                f"{source}: configure `{field}` in Kimi config.toml instead of `{name.strip()}`."
            )
