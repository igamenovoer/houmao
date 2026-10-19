# Claude Hook Adapter

## Scope

This document defines the first provider adapter for the CLI Hook Observation Channel. It covers the Claude Code event selection, observer configuration, collector transport, event normalization, version gates, trust and policy preconditions, launch integration points, and provider-specific limitations.

The adapter is observational. It never decides, blocks, modifies, or accelerates a Claude action.

## 1. Event Selection

The adapter uses four priority tiers. P0 events are the minimum viable channel. P1 events materially improve blocked and failure handling. P2 events improve activity and background-work fidelity. P3 events are diagnostics or future work.

| Tier | Event | Why it matters | Payload fields used |
| --- | --- | --- | --- |
| P0 | `SessionStart` | Binds the provider session, transcript path, model, and start source | `source`, `model`, `session_id`, `transcript_path`, `cwd` |
| P0 | `UserPromptSubmit` | Authoritative turn start, including direct TUI input | `prompt`, `prompt_id`, optional `source` |
| P0 | `Stop` | Authoritative turn end and final assistant text | `stop_hook_active`, `last_assistant_message`, `background_tasks`, `session_crons`, `prompt_id` |
| P0 | `StopFailure` | Authoritative API-failure terminal result and error class | `error`, `error_details`, `last_assistant_message` (API error text), `prompt_id` |
| P0 | `PermissionRequest` | Immediate permission-wait signal | `tool_name`, `tool_input`, `permission_suggestions`; no `tool_use_id` |
| P1 | `PreCompact` | Maintenance window start | `trigger`, `custom_instructions` |
| P1 | `PostCompact` | Maintenance window end | `trigger`, `compact_summary` |
| P1 | `PostToolUseFailure` | Tool failure and tool-level interrupt evidence | `tool_name`, `tool_use_id`, `error`, `is_interrupt`, `duration_ms` |
| P1 | `Notification` | Delayed corroboration for permission, idle, completion, and quota states | `notification_type`, `message`, `title` |
| P2 | `PostToolUse` | Tool activity completion | `tool_name`, `tool_use_id`, `tool_response`, `duration_ms` |
| P2 | `PostToolBatch` | Batch activity boundary | `tool_calls[]` |
| P2 | `SubagentStart` | Nested activity start | `agent_id`, `agent_type` |
| P2 | `SubagentStop` | Nested activity end; never parent turn end | `agent_id`, `agent_type`, `last_assistant_message`, `background_tasks` |
| P2 | `SessionEnd` | Best-effort session end reason | `reason` |
| P3 | `PreToolUse`, `PermissionDenied`, `MessageDisplay`, `PreModelSwitch`, `PostModelSwitch`, `TaskCreated`, `TaskCompleted`, `TeammateIdle`, `Elicitation`, `ElicitationResult` | Diagnostics, GUI streaming, agent-team state, future policy | Provider-specific |

### 1.1 Events Deliberately Not Used as Primary Signals

- `Notification.permission_prompt` is delayed by several seconds. Use `PermissionRequest` for the immediate blocked fact; use `Notification` as corroboration.
- `Notification.idle_prompt` is delayed by about a minute. It is not a completion signal.
- `UserPromptSubmit` also fires for turns Claude starts itself. Do not use it as proof that a human typed the prompt. Use it as a turn-start fact and correlate it with the gateway submission path when available.
- `Stop` means the response ended, not that the overall task is complete. Do not map it to a task-completion state.
- `StopFailure.last_assistant_message` is API error text, not Claude prose. Do not store it as final assistant output.

### 1.2 Events That Cannot Cover the Remaining Gaps

- There is no reliable hook for an interactive Esc interrupt. Keep the TUI temporal silent-abort detector.
- There is no reliable hook for an interactive permission denial. `PermissionDenied` is auto-mode only, and `PostToolUseFailure` excludes permission denials. Keep the TUI `⎿ User rejected` handling.
- There is no hook for provider-native queued input. Keep `surface.pending_input` from the TUI.
- There is no hook for composer readiness, draft text, or modal rendering. Keep those TUI-owned.

## 2. Observer Configuration

### 2.1 Preferred Injection: Session-Scoped `--settings`

Claude Code accepts `--settings <file-or-json>` as an additional settings source for one session. The managed launch generates a session-scoped observer settings file:

```text
<session-root>/hook-observation/claude/observer-settings.json
```

The launch appends one strategy-owned argument:

```text
--settings <absolute-observer-settings-path>
```

This keeps the observer out of the managed home's `settings.json`, the project `.claude/settings.json`, and the operator's user settings.

Rules:

- If the resolved launch args already contain a `--settings` argument, the adapter must not silently append a second source. It must either merge the observer hooks into the existing source when that source is a readable file, or follow the fallback in 2.2.
- The observer settings file is secret-free. It contains no token, credential, or raw prompt.
- The file is generated for every fresh launch and every resume or relaunch generation.

### 2.2 Fallback Injection: Managed-Home `settings.json`

Claude Code merges hooks from user, project, local, and flag settings. If the session-scoped settings source cannot be used, the adapter may merge a Houmao-owned observer block into the managed home's `settings.json`, which the launch policy already owns.

Rules:

- The merge must preserve operator-authored hook entries.
- Observer entries are identified by their command or URL marker, not by a new provider field.
- On `--reuse-home`, the adapter must ensure the observer block exists and repair stale entries.
- If neither injection path is safe, the channel is `unavailable` and the session continues TUI-only.

### 2.3 Hook Handler Layout

| Event | Handler | Reason |
| --- | --- | --- |
| `SessionStart` | `type: command` -> emitter -> collector, fallback append | HTTP hooks are not supported on `SessionStart` |
| `Setup` | `type: command` if used | HTTP hooks are not supported on `Setup` |
| `UserPromptSubmit` | `type: http` -> collector | Ordered, synchronous delivery |
| `Stop` | `type: http` -> collector | Ordered terminal delivery |
| `StopFailure` | `type: http` -> collector | Fire-and-forget; ordering is less critical |
| `PermissionRequest` | `type: http` -> collector | Must arrive before the dialog wait |
| `PreCompact`, `PostCompact` | `type: http` -> collector | Ordered maintenance boundaries |
| `PostToolUseFailure` | `type: http` -> collector | Ordered tool failure evidence |
| `PostToolUse`, `PostToolBatch` | `type: http` -> collector, or `command` with `async: true` | High frequency; choose based on measured latency |
| `SubagentStart`, `SubagentStop` | `type: http` -> collector | Ordered nested activity |
| `Notification` | `type: http` -> collector | Delayed corroboration; ordering not critical |
| `SessionEnd` | `type: http` or `type: command` | Short budget; best effort |

The adapter must not use `prompt`, `agent`, or `mcp_tool` hook handlers for observation. They add model work or external dependencies.

### 2.4 Command-Hook Contract

The command-hook path uses a small stdlib-only emitter. It must:

- read the hook JSON from stdin;
- add `received_at_utc`, a local sequence, and the channel generation;
- POST the envelope to the collector when reachable;
- append to `events.ndjson` when the collector is unreachable;
- write nothing to stdout;
- write no decision fields;
- always exit 0;
- never exit 2;
- redirect stderr to a bounded local log.

Command-hook timeouts:

- boundary events: 2 seconds;
- high-frequency events: `async: true` with a short `asyncTimeout` when supported;
- `SessionEnd`: within the provider's default 1.5-second shared budget;
- never set `onFailure: "block"` for an observer hook.

### 2.5 HTTP-Hook Contract

The HTTP handler posts the provider payload to the collector with a per-session bearer token.

```json
{
  "type": "http",
  "url": "http://127.0.0.1:<ephemeral-port>/v1/hook",
  "timeout": 2,
  "headers": {
    "Authorization": "Bearer $HOUMAO_HOOK_TOKEN"
  },
  "allowedEnvVars": ["HOUMAO_HOOK_TOKEN"]
}
```

Rules:

- The collector returns `204 No Content` with an empty body.
- The collector must enqueue and acknowledge before doing disk work that could exceed the timeout.
- The token is generated per session and never written to public state.
- The observer settings may reference the token through an allowed environment variable. The token must be present in the provider process environment.
- Do not publish the token through the tmux session environment. The current `_publish_tmux_session_environment` path publishes the whole launch environment; the adapter must keep the token out of that publication and pass it only to the provider process.
- If HTTP hooks are blocked by `allowedHttpHookUrls` or another policy, the adapter falls back to command hooks or disables the channel with `hook_http_not_allowed`.

## 3. Collector

The collector is a per-session, loopback-only HTTP process started before the provider. It is an ingress adapter: it validates, stamps, persists, and publishes into the tracker's hook `Subject`. It does not resolve turn state, and it does not decide whether a turn is active, blocked, or complete.

Responsibilities:

- validate the bearer token;
- assign `channel_generation`, `received_at_utc`, and `sequence`;
- append one envelope per event to `events.ndjson`;
- maintain `channel.json` with secret-free status;
- expose a local health and status endpoint for the tracker;
- respond within the provider hook timeout;
- stop when the session stops.

Rules:

- Bind `127.0.0.1` with an ephemeral port.
- Do not reuse a port from a previous generation unless the generation is explicitly resumed.
- Cap the accepted payload size and count oversized events instead of writing them.
- Use an append-only write discipline with a lock or single writer thread.
- Never log raw payloads. Log event name, size, sequence, and outcome.
- A collector crash must not fail the provider. The command-hook fallback continues to write the store.

The collector may be hosted inside the gateway when the gateway is guaranteed to start before the provider. Because the current gateway attach flow starts after the session, the default design uses a standalone collector and lets the gateway read or proxy its status.

## 4. Event Normalization

| Claude event | Normalized kind | Turn-state hint | Terminal hint | Notes |
| --- | --- | --- | --- | --- |
| `SessionStart` | `session_started` | `none` | `none` | `source=clear` or `fork` resets posture; `resume` and `compact` preserve the previous terminal outcome. |
| `UserPromptSubmit` | `prompt_submitted` | `active` | `none` | Treat as a turn start, not as proof of human origin. |
| `PreToolUse` | `activity` | `active` | `none` | Optional; use `PostToolUse` or `PostToolBatch` if `PreToolUse` adds too much latency. |
| `PostToolUse` | `activity` | `active` | `none` | Completion of one tool call. |
| `PostToolBatch` | `activity` | `active` | `none` | One boundary after a parallel batch. |
| `SubagentStart` | `activity` | `active` | `none` | Increment subagent count. |
| `SubagentStop` | `activity` | `active` | `none` | Decrement subagent count; never end the parent turn. |
| `PermissionRequest` | `permission_requested` | `blocked` | `none` | Record `tool_name`; no `tool_use_id`. |
| `PermissionDenied` | `permission_resolved` | `active` | `none` | Auto-mode denial; the agent may retry. |
| `PostToolUseFailure` | `activity` or `permission_resolved` | `active` | `none` | `is_interrupt=true` is tool-level interrupt evidence, not a turn interrupt. |
| `PreCompact` | `maintenance_started` | `maintenance` | `none` | Preserve the previous terminal result. |
| `PostCompact` | `maintenance_ended` | `active` or `none` | `none` | Restore the previous turn posture. |
| `Stop` | `turn_completed` | `ended` | `success` | Read `last_assistant_message`, `background_tasks`, and `session_crons`. |
| `StopFailure` | `turn_failed` | `ended` | `known_failure` | `failure_class=error`; `last_assistant_message` is error text. |
| `Notification` | `unknown` or a corroborating note | unchanged | unchanged | Never primary for blocked or completion. |
| `SessionEnd` | `session_ended` | `none` | `none` | Best effort; do not use for cleanup. |

## 5. Version and Capability Gates

The repository currently supports Claude Code 2.1.296 and later, with no upper bound. The official hook catalog evolves within that range, so the adapter uses a capability model rather than assuming every event exists.

### 5.1 Required Capabilities

The channel is viable only when all of the following are present:

- `SessionStart`, `UserPromptSubmit`, `Stop`, and `PermissionRequest`;
- a working settings injection path (`--settings` or managed-home settings);
- hook execution in the selected client mode;
- workspace trust for interactive launches.

If a required capability is missing, the channel reports `hook_version_unsupported` or `hook_channel_unavailable` and the session runs TUI-only.

### 5.2 Optional Capabilities

`StopFailure`, `PostToolBatch`, `PostCompact`, `PermissionDenied`, `SubagentStart`, and `SessionEnd` are optional. The adapter configures them when the observed version is known to support them, or when a capability probe confirms them. Absence of an optional event is not evidence about state.

### 5.3 Known Version Boundaries

- `2.1.295`: `onFailure: "block"` is available. The observer must not use it.
- `2.1.296`: maintained support floor. Core hook behavior must be verified live here.
- `2.1.299`: `UserPromptSubmit` runs before skill and slash-command expansion. Prompt text and blocking behavior differ from 2.1.296 through 2.1.298.
- `2.1.302`: concurrency limits for `prompt` and `agent` hooks. Command and HTTP observer hooks are unaffected.
- `2.1.251`: model-switch hooks and resume/fork cost fields.
- `2.1.257`: `scratchpad_dir`.

The adapter must not configure an event that the floor version does not recognize if that would invalidate the settings source. Keep the required set minimal and add optional events only after a version or capability check.

### 5.4 Capability Probe

After launch, the channel health monitor uses observed events rather than a static version map:

- `SessionStart` within the startup grace proves configuration loading and trust.
- An optional event that never appears is treated as unsupported, not as a state fact.
- An unknown event name is counted and ignored.
- A settings-validation failure that prevents all events is `hook_channel_unavailable` with the provider diagnostics.

## 6. Trust, Policy, and Client-Mode Preconditions

- Interactive Claude Code withholds hooks until the workspace is trusted. Houmao's unattended launch must seed `hasTrustDialogAccepted` and related project state before startup.
- If the workdir is not trusted, the channel reports `untrusted_workspace` and the agent still runs.
- `disableAllHooks`, `allowManagedHooksOnly`, `strictPluginOnlyCustomization`, `--safe-mode`, `--bare`, and `--restricted` can prevent the observer from running.
- `allowedHttpHookUrls` can silently block the collector. The command-hook fallback is the mitigation.
- Joined sessions run a provider that Houmao did not launch. The observer settings were not injected, so the channel reports `unavailable` unless a future join path explicitly installs it.
- Headless `-p` sessions treat the workspace as trusted and may run hooks, but async hooks are killed at teardown.

## 7. Launch and Runtime Integration Points

| Layer | Change |
| --- | --- |
| `LaunchPlanRequest` | Add an optional `session_root` so the launch plan can generate session-scoped observer artifacts. |
| `build_launch_plan` | For `tool=claude`, call the observer installer before returning the plan. Add `--settings` and observer metadata. |
| `start_runtime_session` | Pass the resolved session root into the launch plan request. Start the collector before backend session creation. |
| `resume_runtime_session` | Pass the existing session root, create a new channel generation, and install or repair observer settings. |
| `local_interactive` backend | Launch the provider with the observer settings and the collector token environment. Do not publish the token in the tmux session environment. |
| `claude_headless` backend | Optional in v1. If enabled, hooks work per `-p` process, but `stream-json` remains the primary structured channel. |
| `SingleSessionTrackingRuntime` | Publish hook observations into the tracker's hook `Subject` before or alongside each TUI capture. The stream, not the poll loop, resolves the combined state. |
| `LiveSessionTracker` | Own the merged Rx stream, apply authority rules in the reducer, and publish channel diagnostics. |
| `TuiTrackerSession` | No provider-hook dependency. It remains the TUI-only channel and the passive-server source. |
| `gateway_service` | Add hook facts to prompt admission reasons and decision payloads. |
| `passive_server/observation.py` | Read the local hook store when the observer is local; report `remote observation` otherwise. |
| Session cleanup | Stop the collector and remove or retain the session-owned hook subtree. |

## 8. Headless Considerations

- `claude -p` already emits structured `stream-json`, including result events. Hooks add permission, compaction, and subagent context, but they are not required for basic headless turn completion.
- `--include-hook-events` adds hook lifecycle messages to the headless stream. It has event-specific gaps and is not a replacement for the collector.
- Async command hooks are killed at `-p` teardown and finalized as cancelled. Do not rely on them for terminal state.
- `SessionEnd` is best effort and has a short budget.
- The first release targets `local_interactive`. Headless adoption is a follow-up after the TUI path is qualified.

## 9. Cleanup and Generation Handling

- Each provider launch gets a new `channel_generation`.
- The collector appends a generation boundary record before the provider starts.
- Old generation events are ignored by the tracker.
- On stop, the collector stops and `channel.json` records `stopped`.
- Session cleanup removes the hook subtree by default. A diagnostic retention option may preserve it.
- Managed-home fallback hooks remain installed only if the home is reused. The installer must repair or remove stale observer entries on the next launch.

## Open Questions

- Is `--settings` available and honored at the 2.1.296 floor in both TUI and `-p` modes?
- Are HTTP hooks available at the 2.1.296 floor, and does the organization allow loopback URLs?
- Which optional events can be configured at 2.1.296 without invalidating the settings source?
- Should the collector be standalone, gateway-hosted, or a Unix-socket service, provided each path publishes into the same hook `Subject`?
- Should the token be passed in the provider environment, a `0600` file, or both?
- Should `Stop.last_assistant_message` be stored in the session manifest or only in local turn evidence?
- Should a `StopFailure` snapshot be exposed on the public state surface, and with which failure-class vocabulary?
- Should the adapter install hooks for joined sessions at join time, or leave them TUI-only indefinitely?
