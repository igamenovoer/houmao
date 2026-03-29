# Realm Controller

`houmao.agents.realm_controller` is the run-phase orchestration layer in Houmao. It takes a built brain manifest and a role, composes them into a backend-specific launch plan, and manages the full lifecycle of an interactive agent session — start, resume, prompt, and stop.

## Source Location

`src/houmao/agents/realm_controller/` — lazy public exports for realm-controller runtime helpers.

Key modules:

| Module | Responsibility |
|---|---|
| `models.py` | Canonical backend and session contracts (`BackendKind`, `InteractiveSession`, `RuntimeSessionController`) |
| `launch_plan.py` | Bridge between build-time manifest and run-time launch (`LaunchPlan`, `build_launch_plan()`) |
| `session.py` | Session lifecycle functions (`start_runtime_session()`, `resume_runtime_session()`) |
| `cli.py` | `houmao-cli` entrypoint (deprecated; prefer `houmao-mgr`) |
| `backends/` | Per-backend session implementations |

## Backend Model

Every agent session runs on a specific backend. The `BackendKind` literal type in `models.py` is the authoritative list:

```python
BackendKind = Literal[
    "local_interactive",
    "codex_headless",
    "codex_app_server",
    "claude_headless",
    "gemini_headless",
    "cao_rest",
    "houmao_server_rest",
]
```

### `local_interactive` — Primary Backend

The default and recommended backend. Launches agent CLI tools as tmux-backed interactive sessions via `LocalInteractiveSession`. This gives each agent a real terminal with full native UX, scrollback, and the ability to attach/detach at will.

All local backends (codex, claude, gemini headless modes) ultimately use the shared tmux runtime primitives.

## Model Selection (Claude Code)

Claude model selection remains environment-driven. Set `ANTHROPIC_MODEL` for the primary model, and use optional companion variables such as `ANTHROPIC_SMALL_FAST_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL`, and `ANTHROPIC_DEFAULT_*_MODEL` aliases when your local Claude profile needs explicit pins.

Houmao does not invent a second model-selection layer in the realm controller. The launch plan projects the effective runtime home and allowlisted environment, and Claude reads the selected model configuration from that environment during launch.

### `codex_headless`

Runs `codex exec --json` for non-interactive, structured prompt–response cycles. Supports resume via `resume <thread_id>`.

### `codex_app_server`

Runs Codex in `app-server` mode for persistent, server-backed sessions.

### `claude_headless`

Runs `claude -p` for non-interactive prompt–response cycles. Supports session continuation via `--continue`.

### `gemini_headless`

Runs `gemini -p` for non-interactive prompt–response cycles. Supports session continuation via `--resume latest`.

### Legacy Backends

The following backends exist for backward compatibility and are planned for removal:

- **`cao_rest`** — Delegates session lifecycle to an external CAO (CLI Agent Orchestrator) server over REST. This was the original orchestration path and carries significant complexity (~86 KB of integration code). New workflows should not target this backend.
- **`houmao_server_rest`** — A thin wrapper that routes requests through `houmao-server`, which itself delegates to `cao_rest`. Shares the same deprecation trajectory.

## Launch Plan

`LaunchPlan` is the backend-agnostic data object that bridges build-time and run-time. It is constructed by `build_launch_plan()` from a brain manifest and a role, and encapsulates everything needed to start a session:

| Field | Description |
|---|---|
| `backend` | Target `BackendKind` |
| `tool` | Agent CLI tool name (e.g., `codex`, `claude`, `gemini`) |
| `executable` | Resolved path to the tool binary |
| `args` | CLI arguments for the tool |
| `working_directory` | Working directory for the agent process |
| `home_env_var` | Environment variable name for the tool’s home directory (e.g., `CODEX_HOME`) |
| `home_path` | Resolved path to the projected runtime home |
| `env` | Merged environment variables (allowlisted vars + launch overrides) |
| `role_injection` | Backend-specific role injection payload |
| `metadata` | Freeform metadata passed through to the session |
| `mailbox` | Optional mailbox binding for inter-agent messaging |

Launch overrides from recipes and direct builds are intentionally limited to secret-free settings. Protocol-required arguments such as `claude -p`, `gemini -p`, `codex exec --json`, `resume`, and `app-server` stay backend-owned and are not exposed as overrides.

## Session Lifecycle

### The `InteractiveSession` Protocol

All backends implement the `InteractiveSession` protocol defined in `models.py`:

- **`send_prompt(prompt)`** — Send a prompt to the running agent and return the response.
- **`interrupt()`** — Send an interrupt signal to the agent process.
- **`terminate()`** — Terminate the agent session.
- **`close()`** — Clean up resources associated with the session.

### `RuntimeSessionController`

The `RuntimeSessionController` manages the full session lifecycle. It holds references to the active session, its manifest, and backend-specific state.

### Starting a Session

`start_runtime_session()` takes a `LaunchPlan` and:

1. Resolves the backend implementation from `LaunchPlan.backend`.
2. Creates the tmux session (for local backends) or connects to the remote endpoint (for REST backends).
3. Injects the role via the backend-specific injection strategy.
4. Persists the session manifest to disk.
5. Returns the active `InteractiveSession`.

### Resuming a Session

`resume_runtime_session()` reattaches to an existing session from a persisted manifest. The resume mechanism is backend-specific:

- **`local_interactive`**: Reattaches to the existing tmux session.
- **`codex_headless`**: Uses `resume <thread_id>` to continue the Codex thread.
- **`claude_headless`**: Uses `--continue` to resume the Claude session.
- **`gemini_headless`**: Uses `--resume latest` to resume the Gemini session.

### Sending Prompts

Once a session is running, `send_prompt()` delivers a user prompt to the agent and returns the response. For `local_interactive` sessions, this sends keystrokes to the tmux pane. For headless backends, this invokes the CLI tool with the prompt as an argument.

### Stopping a Session

`terminate()` stops the agent process and `close()` cleans up session resources. For tmux-backed sessions, this kills the tmux session.

## Role Injection

Role injection is backend-specific and handled during launch plan construction in `launch_plan.py`:

| Backend | Injection Strategy |
|---|---|
| `codex_headless` / `codex_app_server` | Native developer instructions when the role prompt is non-empty |
| `claude_headless` | Native appended system prompt plus a bootstrap message when the role prompt is non-empty |
| `gemini_headless` | Bootstrap message when the role prompt is non-empty |
| `local_interactive` | Tool-dependent native injection or bootstrap, skipped when the role prompt is empty |

The role content comes from the role package (`roles/<role>/system-prompt.md`) in the agent definition directory.

## Versioned Unattended Launch Policy

Unattended startup is a versioned launch policy resolved at launch time against the installed CLI version of the target tool. If the installed version does not match a known launch policy, the session fails closed rather than guessing a bootstrap strategy. This prevents silent behavioral drift when CLI tools update their interfaces.

## CLI Surface

The realm controller exposes a CLI via `houmao-cli` (the `cli.py` module) with the following commands:

- **`build-brain`** — Run the build phase and emit a brain manifest.
- **`start-session`** — Build a launch plan and start a new session.
- **`send-prompt`** — Send a prompt to a running session.
- **`gateway-send-prompt`** — Send a prompt through a gateway-attached session.
- **`send-keys`** — Send raw control input to a resumed session.
- **`gateway-interrupt`** — Submit an interrupt through an attached live gateway.
- **`stop-session`** — Stop a session.
- **`attach-gateway`** — Attach a live gateway to a running session.
- **`detach-gateway`** — Detach a live gateway without stopping the session.
- **`gateway-status`** — Read gateway status from the live gateway or stable state artifact.
- **`cleanup-registry`** — Remove stale shared-registry live-agent directories.
- **`mail`** — Run mailbox operations against a resumed session.

> **Note:** `houmao-cli` is a deprecated compatibility entrypoint. The preferred CLI surface is **`houmao-mgr`** (`src/houmao/srv_ctrl/cli.py`), which provides the same lifecycle operations along with managed agent, gateway, mailbox, and server control. See [houmao-mgr CLI reference](cli/houmao-mgr.md).
