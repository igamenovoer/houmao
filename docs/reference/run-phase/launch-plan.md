# Launch Plan

Module: `src/houmao/agents/realm_controller/launch_plan.py` — Launch-plan composition for brain + role inputs.

The launch plan is the bridge between Houmao's build phase and run phase. It takes a built brain manifest and a role package, resolves environment variables, merges launch overrides, binds mailbox configuration, and produces a fully resolved, backend-specific plan that a session backend can execute directly.

## LaunchPlanRequest

`LaunchPlanRequest` is a frozen dataclass that captures everything needed to compose a launch plan.

| Field | Type | Description |
|---|---|---|
| `brain_manifest` | `dict[str, Any]` | Loaded brain manifest (output of the build phase) |
| `role_package` | `RolePackage` | Loaded role prompt containing `role_name`, `system_prompt`, and `path` |
| `backend` | `BackendKind` | Target backend for the session |
| `working_directory` | `Path` | Working directory for the agent process |
| `mailbox` | `MailboxResolvedConfig \| None` | Optional resolved mailbox configuration for inter-agent messaging |
| `intent` | `LaunchPolicyApplicationKind` | Launch intent; defaults to `"provider_start"` |

## build_launch_plan

```python
def build_launch_plan(request: LaunchPlanRequest) -> LaunchPlan
```

Composes a backend-specific launch plan from the given request. The function performs the following steps:

1. **Resolves allowlisted environment variables** from the brain home directory, ensuring only declared env vars are propagated to the agent process.
2. **Merges launch overrides** from the brain manifest with backend-specific typed-parameter translation (e.g., translating generic override keys into CLI flags appropriate for the target backend).
3. **Binds mailbox configuration** when inter-agent messaging is requested.
4. **Applies the role injection strategy** appropriate for the target backend (see [Role Injection](role-injection.md)).

The result is a fully resolved `LaunchPlan` that a backend can execute without further interpretation.

## LaunchPlan

`LaunchPlan` is a frozen dataclass representing the fully resolved, ready-to-execute launch configuration.

| Field | Type | Description |
|---|---|---|
| `backend` | `BackendKind` | Target backend |
| `tool` | `str` | Agent tool name (e.g., `"codex"`, `"claude"`, `"gemini"`) |
| `executable` | `str` | Resolved executable path or command |
| `args` | `list[str]` | Command-line arguments for the agent process |
| `working_directory` | `Path` | Working directory for the agent process |
| `home_env_var` | `str` | Environment variable name pointing to the runtime home (e.g., `CODEX_HOME`) |
| `home_path` | `Path` | Absolute path to the runtime home directory |
| `env` | `dict[str, str]` | Effective launch environment — contains secrets in-memory only, never persisted |
| `env_var_names` | `list[str]` | Names of environment variables set in `env` (for auditing without exposing values) |
| `role_injection` | `RoleInjectionPlan` | Backend-specific role injection plan (see [Role Injection](role-injection.md)) |
| `metadata` | `dict[str, Any]` | Additional metadata carried through from the brain manifest |
| `mailbox` | `MailboxResolvedConfig \| None` | Resolved mailbox configuration, if any |
| `launch_policy_provenance` | `LaunchPolicyProvenance \| None` | Provenance information for the applied launch policy |

### Security note

The `env` dictionary contains secret values (API keys, tokens) resolved at launch time. These values exist only in memory and are passed directly to the agent process environment. They are intentionally excluded from persisted manifests and logs.

## backend_for_tool

```python
def backend_for_tool(
    tool: str,
    prefer_cao: bool = False,
    prefer_local_interactive: bool = False,
) -> BackendKind
```

Returns the default backend for a given tool name.

**Default mapping:**

| Tool | Default Backend |
|---|---|
| `codex` | `codex_headless` |
| `claude` | `claude_headless` |
| `gemini` | `gemini_headless` |

**Override behavior:**

- When `prefer_local_interactive=True`, returns `local_interactive` for all tools. This routes the agent through a tmux-backed interactive session instead of the tool's native headless mode.
- When `prefer_cao=True`, returns `cao_rest` (legacy server-backed path).

## See also

- [Backends](backends.md) — backend implementations that execute a `LaunchPlan`
- [Role Injection](role-injection.md) — how role prompts are delivered per backend
- [Session Lifecycle](session-lifecycle.md) — how launch plans are used to start and resume sessions
