# Role Injection

Role injection determines how a role's system prompt is delivered to an agent session. Because each agent tool (Codex, Claude, Gemini) accepts role-level instructions differently, the injection strategy is resolved per-backend at launch-plan composition time.

## plan_role_injection

```python
def plan_role_injection(
    backend: BackendKind,
    tool: str,
    role_name: str,
    role_prompt: str,
) -> RoleInjectionPlan
```

Determines the injection strategy for the given backend and tool, and returns a fully resolved `RoleInjectionPlan`. This function is called internally by `build_launch_plan` (see [Launch Plan](launch-plan.md)) and does not need to be invoked directly.

## RoleInjectionPlan

`RoleInjectionPlan` is a frozen dataclass describing how and what to inject.

| Field | Type | Description |
|---|---|---|
| `method` | `RoleInjectionMethod` | The injection strategy to use |
| `role_name` | `str` | Name of the role being injected |
| `prompt` | `str` | The full role prompt text |
| `bootstrap_message` | `str \| None` | First-turn message to deliver the role prompt, if the method requires it |

## RoleInjectionMethod

The `RoleInjectionMethod` type enumerates the available injection strategies:

- **`native_developer_instructions`** — the role prompt is passed as a CLI flag that the tool natively supports for developer/system instructions.
- **`native_append_system_prompt`** — the role prompt is appended to the tool's system prompt via a native CLI flag, optionally combined with a bootstrap message.
- **`bootstrap_message`** — the role prompt is delivered as the first user-turn message in the session.
- **`profile_based`** — the role prompt is injected via a server-side profile mechanism (legacy backends only).

## Per-backend strategies

| Backend | Method | How it works |
|---|---|---|
| `codex_headless` | `native_developer_instructions` | Role prompt passed via `-c developer_instructions=<prompt>` flag. The prompt becomes part of Codex's developer instructions context. |
| `codex_app_server` | `native_developer_instructions` | Same mechanism as `codex_headless`. |
| `claude_headless` | `native_append_system_prompt` | Role prompt passed via `--append-system-prompt <prompt>` flag, which appends it to Claude's system prompt. Additionally, a bootstrap message is sent on the first turn to reinforce the role context. |
| `gemini_headless` | `bootstrap_message` | Role prompt is delivered as a first-turn bootstrap message. Gemini CLI does not expose a native system-prompt injection flag, so the role is established through conversational priming. |
| `local_interactive` | `bootstrap_message` | Role prompt is delivered as a first-turn bootstrap message via tmux paste-buffer. Since the agent runs as an interactive CLI process, there is no CLI-flag-based injection path. |
| `cao_rest` | `profile_based` | Legacy: role prompt is injected via the external server's profile-based mechanism. |
| `houmao_server_rest` | `profile_based` | Legacy: role prompt is injected via the server's profile-based mechanism. |

## Bootstrap message lifecycle

For backends that use `bootstrap_message` or combine native injection with a bootstrap message (`claude_headless`), the bootstrap is delivered exactly once — on the first turn of the session. The headless backend base class tracks this via the `role_bootstrap_applied` flag in `HeadlessSessionState`, ensuring the bootstrap message is not re-sent on resume.

The bootstrap message is distinct from subsequent user prompts. It establishes the agent's role context before any user-directed work begins.

## Design rationale

Role injection is intentionally backend-specific rather than using a single universal strategy because:

1. **Native injection is preferred** when available. Tools like Codex and Claude provide dedicated CLI flags for developer instructions and system prompts, respectively. Using these native mechanisms ensures the role prompt is handled by the tool's own context management, which is more reliable than conversational priming.

2. **Bootstrap messages are the fallback.** When a tool does not expose a native injection flag (Gemini, local interactive), the role prompt is sent as the first conversational turn. This is effective but less cleanly separated from user content.

3. **Legacy backends delegate entirely.** The `cao_rest` and `houmao_server_rest` backends rely on server-side profile mechanisms that are outside the local launch plan's control.

## See also

- [Launch Plan](launch-plan.md) — where role injection plans are composed
- [Backends](backends.md) — backend implementations that execute role injection
- [Session Lifecycle](session-lifecycle.md) — how role injection fits into the session startup flow
