# Role Injection

Role injection determines how a role's system prompt is delivered to an agent session. Because each agent tool (Claude, Codex, Kimi) accepts role-level instructions differently, the injection strategy is resolved per-backend at launch-plan composition time. The input to role injection is the already-composed effective launch prompt, not just the raw contents of `roles/<role>/system-prompt.md`. For current managed launches, that effective prompt is rooted at `<houmao_system_prompt>` and may contain `<managed_header>`, `<prompt_body>`, `<role_prompt>`, `<launch_profile_overlay>`, and `<launch_appendix>` sections depending on what participated in the launch.

## Injection decision tree

```mermaid
flowchart TD
    BE{backend?}

    CL["claude_headless"]
    CX["codex_headless /<br/>codex_app_server"]
    KM["kimi_headless"]
    LI["local_interactive"]
    LEG["legacy/internal REST<br/>manifest rejection"]

    NDI["native_developer_instructions<br/>-c developer_instructions flag"]
    NAS["native_append_system_prompt<br/>provider-native append"]
    NHS["native_home_system_prompt<br/>managed SYSTEM.md"]
    BM["bootstrap_message<br/>(first-turn prompt)"]
    PB["cao_profile<br/>(legacy/internal only)"]

    BE -->|claude| CL --> NAS
    BE -->|codex| CX --> NDI
    BE -->|kimi| KM --> NHS
    BE -->|local interactive| LI --> NDI
    LI --> NAS
    LI --> NHS
    BE -->|legacy REST| LEG --> PB
```

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
| `prompt` | `str` | The complete effective launch prompt after managed-header, overlay, and appendix composition |
| `bootstrap_message` | `str \| None` | First-turn message to deliver the role prompt, if the method requires it |

## RoleInjectionMethod

The `RoleInjectionMethod` type enumerates the available injection strategies:

- **`native_developer_instructions`** — the effective launch prompt is passed as a CLI flag that the tool natively supports for developer/system instructions when prompt content exists.
- **`native_append_system_prompt`** — the effective launch prompt is appended to the tool's system prompt via a native CLI flag, optionally combined with a bootstrap message, when prompt content exists.
- **`native_home_system_prompt`** — the complete effective launch prompt is projected into a provider-owned system-prompt file in the managed home and verified before provider start.
- **`bootstrap_message`** — the effective launch prompt is delivered as the first user-turn message in the session when prompt content exists.
- **`cao_profile`** — the effective launch prompt was injected via a legacy profile mechanism. Current public launch paths do not target this method.

The runtime does not ask providers to interpret those tags. Backends receive one opaque final prompt string and apply their declared native injection path or remaining provider-specific bootstrap behavior to that already-rendered prompt.

## Per-backend strategies

| Backend | Method | How it works |
|---|---|---|
| `claude_headless` | `native_append_system_prompt` | When the effective launch prompt is non-empty, Houmao passes `--append-system-prompt <prompt>` and sends one bootstrap message on the first turn. Empty effective prompts skip both. |
| `codex_headless` | `native_developer_instructions` | When the effective launch prompt is non-empty, Houmao passes `-c developer_instructions=<prompt>`. Empty effective prompts skip this startup input entirely. |
| `codex_app_server` | `native_developer_instructions` | Same semantics as `codex_headless`, but applied to the `thread/start` request payload. |
| `kimi_headless` | `native_home_system_prompt` | For Kimi Code 0.34.0 or later, Houmao writes and verifies `$KIMI_CODE_HOME/SYSTEM.md` before the first process starts. Empty effective prompts remove the file. |
| `local_interactive` | tool-dependent | Codex uses native developer instructions, Claude uses native appended system prompt, and Kimi 0.34.0 or later uses managed-home `SYSTEM.md`. Empty effective prompts suppress or remove those startup inputs. |
| `cao_rest` | `cao_profile` | Legacy/internal: retained only for old manifests and explicit rejection paths. |
| `houmao_server_rest` | `cao_profile` | Legacy/internal: retired old-server backend identity, rejected for new sessions. |

## Bootstrap message lifecycle

For backends that use `bootstrap_message` or combine native injection with a bootstrap message (`claude_headless`), the bootstrap is delivered exactly once when effective launch-prompt content exists — on the first turn of the session. The headless backend base class tracks this via the `role_bootstrap_applied` flag in `HeadlessSessionState`, ensuring the bootstrap message is not re-sent on resume.

The bootstrap message is distinct from subsequent user prompts. It establishes the agent's role context before any user-directed work begins.

## Design rationale

Role injection is intentionally backend-specific rather than using a single universal strategy because:

1. **Native injection is preferred** when available. Tools like Codex and Claude provide dedicated CLI flags for developer instructions and system prompts, respectively. Using these native mechanisms ensures the role prompt is handled by the tool's own context management, which is more reliable than conversational priming.

2. **Native home surfaces are first-class.** A provider does not need a prompt CLI flag to support native delivery. Kimi Code 0.34.0 or later loads managed `$KIMI_CODE_HOME/SYSTEM.md`, so Houmao can preserve Kimi's built-in prompt and deliver the role before the first conversational turn.

3. **Legacy backends are not public launch targets.** `cao_rest` and `houmao_server_rest` may still appear in old manifests or internal compatibility code, but new user-facing launches fail fast before relying on their profile mechanism.

Kimi's canonical file starts with `${base_prompt}`, followed by a blank line and the complete effective Houmao prompt. Houmao rejects every `${identifier}` token in authored prompt text because Kimi would expand it as a provider template variable. Before fresh headless startup, fresh TUI startup, or relaunch, Houmao rejects higher-priority agent selectors, repairs file drift atomically, and verifies prompt hashes under the provider-state lock. This contract requires `KIMI_CODE_LEGACY_FLAG=0` and supports Kimi Code from 0.34.0 onward without an upper limit.

## See also

- [Launch Plan](launch-plan.md) — where role injection plans are composed
- [Backends](backends.md) — backend implementations that execute role injection
- [Session Lifecycle](session-lifecycle.md) — how role injection fits into the session startup flow
