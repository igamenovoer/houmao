# Payload Catalog: Kimi Hook Events at 2.2.0

Date: 2026-10-20. Built from the raw `events.ndjson` / `raw-provider-payloads.ndjson` streams of iteration 1, not from memory. Sources: S0, S1, S2, S3, S4, S5, S6 (Ctrl-S canonical), S7 (two generations), S8, S9, F1, D1, T1. Values classes: str, int, float, bool, array, object, null. Structure and field names only; session-authored prompt text is quoted where it carries structure. No credential material.

Convention: collector envelope fields (`sequence`, `received_at_utc`, `received_at_monotonic`, `channel_generation`, `via`, `delivery`) sit one level above the provider payload and are excluded. The emitter does not mutate the provider payload. `client_type` is `kimi_code_cli` in every observed event and is listed once per event without repeating the value.

## Availability by Mode

| Event | Auto TUI (`--auto`) | Ask TUI (`manual`) | Headless `-p` | Observed in |
| --- | --- | --- | --- | --- |
| `SessionStart` | yes | yes | yes | all TUI arms, S8 |
| `UserPromptSubmit` | yes | yes | yes | all prompt arms, S8 |
| `TurnStarted` | yes | yes | yes | all turn arms, S8 |
| `Stop` | yes | yes | yes | all completed turns, S8; absent on interrupt/kill |
| `SessionEnd` | yes | yes | **no** | TUI clean exits; S8 process exit produced none |
| `SessionHeartbeat` | yes (60 s) | yes | not exercised | S1, S6 |
| `PreToolUse` | yes | yes | not exercised | S1, S3, S4, S9 |
| `PostToolUse` | yes | yes | not exercised | S1, S3, S4, S9 |
| `PostToolUseFailure` | not observed | yes (deny) | not exercised | S3 only |
| `PermissionRequest` | **no** | yes | **no** | S3 only |
| `PermissionResult` | **no** | yes | **no** | S3 only |
| `UserPromptQueued` | yes (Ctrl-S steer) | not exercised | not exercised | S6 |
| `Interrupt` | yes (Esc) | not exercised | not exercised | S5 |
| `PreCompact` | yes (`/compact`) | not exercised | not exercised | S4 |
| `PostCompact` | yes | not exercised | not exercised | S4 |
| `SubagentStart` | yes (Agent tool) | not exercised | not exercised | S9 |
| `SubagentStop` | yes | not exercised | not exercised | S9 |
| `StopFailure` | never observed | never observed | never observed | — |
| `TaskStarted` | **not observed** | not exercised | not exercised | S9 (Agent tool produced none) |
| `Notification` | not observed | not exercised | not exercised | — |

Permission events are absent under `--auto` in every arm, which is the positive control for P2.4. Print mode also produced none.

## SessionStart

Observed in: all 13 arms; 13 fresh (`source=startup`) + 1 resume (`source=resume`).

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | all | `SessionStart` |
| `session_id` | str | all | `session_<uuid>`; identical across S7 generations and across compaction |
| `source` | str | all | `startup` (fresh TUI/headless), `resume` (`kimi --continue`). `clear`/`fork`/`compact` not exercised |
| `model` | str | all | `kimi-code/k3-256k` (provider-qualified raw id, not the TUI's friendly `K3-256k`) |
| `profile` | str | all | `agent` |
| `cwd` | str | all | session workdir |
| `client_type` | str | all | `kimi_code_cli` |
| `session_title` | str | **S7 resume only** | present when a title already exists; absent on every fresh `SessionStart` because the title is generated after the first prompt |

No `transcript_path`. This matches the source-derived base plus `model`/`profile`.

## UserPromptSubmit

Observed in: all prompt arms; counts S1 x3, S3 x2, S4 x2, S6 x1, S7 x2, one each in S0/S5/S8/S9/F1/D1/T1.

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | all | |
| `session_id` | str | all | |
| `cwd` | str | all | |
| `client_type` | str | all | |
| `prompt` | array | all | raw `ContentPart[]`: `[{type: "text", text: "<verbatim prompt>"}]`; observed prompts are plain text only |
| `is_steer` | bool | all | `false` in every observed UPS. A Ctrl-S steered message produced `UserPromptQueued` but **no** UPS, so `is_steer=true` was never observed |
| `session_title` | str | all except S8 | first prompt's title, repeated on every later turn; absent in headless |

No `prompt_id` on this event at 2.2.0. `TurnStarted.prompt` carries the same text as a plain string.

## TurnStarted

Observed in: every turn, including the nested subagent turn (S9).

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | all | |
| `session_id` | str | all | |
| `cwd` | str | all | |
| `client_type` | str | all | |
| `turn_id` | int | all | 0-based per session/agent scope; **continues across resume** (S7 gen 2 first turn = 1; corrected 2026-10-20 by replay); **collides** across parent and subagent turns in S9 (both 0) |
| `origin_kind` | str | all | `user`; `system_trigger` for the nested subagent turn |
| `origin_name` | str | S9 only | `subagent` |
| `prompt` | str | all | plain string (not ContentPart[]); the subagent prompt includes the injected git context |
| `session_title` | str | all except S8 | absent in headless |

No `turn_id` on `Stop`, `UserPromptSubmit`, or tool events.

## Stop

Observed in: all completed turns; not emitted for S5's interrupted turn or F1's killed turn.

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | all completed turns | |
| `session_id` | str | all | |
| `cwd` | str | all | |
| `client_type` | str | all | |
| `session_title` | str | all except S8 | absent in headless |
| `stop_hook_active` | bool | all | `false` everywhere observed |

No `turn_id`, no `prompt_id`, no `last_assistant_message` (unlike Claude). Correlation to a turn is by event order (UPS/TurnStarted → Stop).

## SessionEnd

Observed in: all TUI clean exits (S0, S1, S3, S4, S5, S6, S7 x2, S9, T1, D1). Not emitted by S8 headless.

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | TUI exits | |
| `session_id` | str | TUI exits | |
| `cwd` | str | TUI exits | |
| `client_type` | str | TUI exits | |
| `session_title` | str | TUI exits | |
| `reason` | str | TUI exits | `exit` in every clean run; other reasons not exercised |

Awaited at close: S0 exit path 0.968 s; T1 with `sleep 3` 3.984 s. Headless process exit delivers no `SessionEnd`.

## SessionHeartbeat

Observed in: S1 (1), S6 (5). Fires only when the event is subscribed (it is).

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | S1, S6 | |
| `session_id` | str | S1, S6 | |
| `cwd` | str | S1, S6 | |
| `client_type` | str | S1, S6 | |
| `session_title` | str | S1, S6 | |
| `uptime_ms` | int | S1, S6 | values: 60001, 120000, 180001, 240001, 300000 (also 60000 in one run); measured from session service creation |

Cadence is the source's 60 s interval; no sub-second jitter observed. A 60 s heartbeat is a slow liveness signal: F1's 70 s silence is required to prove cessation.

## PreToolUse

Observed in: S1 (Bash), S3 (Write x2), S4 (Read), S9 (Agent).

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | S1, S3, S4, S9 | |
| `session_id` | str | same | |
| `cwd` | str | same | |
| `client_type` | str | same | |
| `session_title` | str | same | |
| `tool_name` | str | same | `Bash`, `Write`, `Read`, `Agent` |
| `tool_call_id` | str | same | `tool_<id>`; pairs with PostToolUse/Permission events |
| `tool_input` | object | same | Bash `{command}`; Write `{content, path}`; Read `{path}`; Agent `{description, prompt}` |

No `turn_id` on tool events (confirmed). The Agent tool's `tool_input.prompt` is a string.

## PostToolUse

Observed in: S1 (Bash), S3 (Write allow), S4 (Read), S9 (Agent).

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | same | |
| `session_id`, `cwd`, `client_type`, `session_title` | str | same | |
| `tool_name` | str | same | |
| `tool_call_id` | str | same | identical to the matching PreToolUse |
| `tool_input` | object | same | identical to PreToolUse |
| `tool_output` | str | same | string, not an object: `"hi\n"`, `"Wrote 6 bytes to …"`, file text for Read, agent summary for Agent |

No `duration_ms`; no structured tool response.

## PostToolUseFailure

Observed in: S3 deny path only.

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | S3 | |
| `session_id`, `cwd`, `client_type`, `session_title` | str | S3 | |
| `tool_name` | str | S3 | `Write` |
| `tool_call_id` | str | S3 | same as the rejected `PermissionRequest`/`PermissionResult` |
| `tool_input` | object | S3 | `{content, path}` |
| `error` | object | S3 | observed `{code: "internal", message: "Tool \"Write\" was not run because the user rejected the approval request.", retryable: false}` |

`error.name`, `error.details`, and `error.cause` were **absent** in the observed deny payload. No auto-mode failure was observed.

## PermissionRequest

Observed in: S3 only (2 calls, both Write).

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | S3 | |
| `session_id`, `cwd`, `client_type`, `session_title` | str | S3 | |
| `tool_name` | str | S3 | `Write` |
| `tool_input` | object | S3 | `{content, path}` |
| `tool_call_id` | str | S3 | pairs with the surrounding PreToolUse and the result |
| `turn_id` | int | S3 | 0, 1 |
| `agent_id` | str | S3 | `main` |
| `id` | str | S3 | `approval_<uuid>`; shared with the matching PermissionResult |
| `action` | str | S3 | `"Writing /tmp/…"` |
| `display` | object | S3 | `{kind: "file_io", operation: "write", path, content}` |

No `tool_use_id`; `tool_call_id` is the pairing key.

## PermissionResult

Observed in: S3 only (approved + rejected).

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | S3 | |
| `session_id`, `cwd`, `client_type`, `session_title` | str | S3 | |
| `tool_name`, `tool_input`, `tool_call_id`, `turn_id` | mixed | S3 | same as the request |
| `agent_id` | str | S3 | `main` |
| `id` | str | S3 | same approval id as the request |
| `action` | str | S3 | same as the request |
| `display` | object | S3 | same as the request |
| `decision` | str | S3 | `approved`, `rejected`; `cancelled`/`error` not exercised |
| `scope` | — | — | absent |
| `feedback` | — | — | absent (Escape deny, no feedback) |
| `selected_label` | — | — | absent; the TUI panel labels are not echoed in the payload |

Allow ordering: `PreToolUse → PermissionRequest → PostToolUse → PermissionResult → Stop` (result after tool execution). Deny ordering: `PreToolUse → PermissionRequest → PermissionResult → PostToolUseFailure → Stop`.

## PreCompact

Observed in: S4 only (`/compact`).

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name`, `session_id`, `cwd`, `client_type`, `session_title` | str | S4 | |
| `trigger` | str | S4 | `manual`; `budget`/`overflow` not exercised |
| `token_count` | int | S4 | 28513 |

No `turn_id`; `estimated_token_count` is not on this event.

## PostCompact

Observed in: S4 only.

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name`, `session_id`, `cwd`, `client_type`, `session_title` | str | S4 | |
| `trigger` | str | S4 | `manual` |
| `estimated_token_count` | int | S4 | 29056 |

Compaction window: 7.224 s. The post-compact turn starts a fresh `turn_id` (1) under the same session id.

## Interrupt

Observed in: S5 only.

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name`, `session_id`, `cwd`, `client_type`, `session_title` | str | S5 | |
| `turn_id` | int | S5 | 0, matching the interrupted TurnStarted |
| `reason` | str | S5 | `cancelled` |

No `Stop` follows the aborted turn.

## UserPromptQueued

Observed in: S6 canonical Ctrl-S run only.

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name`, `session_id`, `cwd`, `client_type`, `session_title` | str | S6 | title is the essay prompt |
| `prompt_id` | str | S6 | `msg_<id>` |
| `prompt` | array | S6 | `ContentPart[]`, same shape as UPS |
| `queue_length` | int | S6 | 1 |

No `is_steer` on this event. Plain Enter while busy did **not** emit it; the text buffered and submitted after `Stop`. Ctrl-S is the queue/steer path.

## SubagentStart

Observed in: S9 only (Agent tool, `explore`).

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name`, `session_id`, `cwd`, `client_type`, `session_title` | str | S9 | |
| `agent_name` | str | S9 | `explore` |
| `prompt` | str | S9 | full subagent prompt including injected git context |

No `agent_id`, `turn_id`, or ContentPart[].

## SubagentStop

Observed in: S9 only.

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name`, `session_id`, `cwd`, `client_type`, `session_title` | str | S9 | |
| `agent_name` | str | S9 | `explore` |
| `response` | str | S9 | `OK` |

## StopFailure

Never observed. The source promises `error_type`/`error_message`, but no forcing arm was run (KQ-4/P4.5 unresolved).

## TaskStarted

Never observed. The Agent tool at 2.2.0 produced `SubagentStart`/`SubagentStop` but **no** `TaskStarted`; no background task was created. `kind=agent` is unconfirmed live.

## Notification

Never observed. No background task status change occurred. `Notification(task.*)` is unconfirmed.

## Diff Against the Source-Derived KQ-2 Catalog

Confirmed as promised:

- Base fields `hook_event_name`, `session_id`, `cwd`, plus `client_type` on every event.
- `tool_call_id` on tool and permission events; `turn_id` on `TurnStarted`, `PermissionRequest`, `PermissionResult`, `Interrupt`, and **not** on `PreToolUse`/`PostToolUse`.
- No `transcript_path`; `model` and `profile` only on `SessionStart`.
- `UserPromptSubmit.prompt` is a raw `ContentPart[]`; `is_steer` exists on UPS.
- `Stop.stop_hook_active` always `false`.
- `SessionHeartbeat.uptime_ms`; 60 s cadence.
- `PreCompact`/`PostCompact(trigger=manual)` with `token_count` / `estimated_token_count`.
- `Interrupt(turn_id, reason=cancelled)` and no `Stop` on the aborted turn.
- `PermissionRequest`/`PermissionResult` pair by `tool_call_id`; decisions `approved`/`rejected`; no permission events under `--auto`.
- `SubagentStart`/`SubagentStop` with `agent_name` and prompt/response.
- `UserPromptQueued(prompt_id, prompt, queue_length)`.

Corrections / additions:

1. `session_title` is **not** on fresh `SessionStart` (title does not exist yet); it appears only on resume `SessionStart` and on later session events. It is absent on all headless events.
2. `turn_id` is an **integer** (0-based), not a string; it **continues across resume** (S7 gen 2 first turn = 1; corrected 2026-10-20 by replay, refuting the source-derived restart claim) and **collides across parent/subagent scopes** in S9 (both 0).
3. `PermissionRequest`/`PermissionResult` carry additional `id` (approval uuid), `action`, `display`, and `agent_id` fields. `PermissionResult`'s optional `scope`/`feedback`/`selected_label` were absent.
4. `PostToolUseFailure.error` observed only `{code, message, retryable}`; `name`, `details`, `cause` absent.
5. `PostToolUse.tool_output` is a **string**, not a structured object; no `duration_ms`.
6. `Stop` has no `turn_id`, no `prompt_id`, and no `last_assistant_message`.
7. `UserPromptSubmit` has **no `prompt_id`**; `prompt_id` exists only on `UserPromptQueued`.
8. Headless print mode emits **no `SessionEnd`** and omits `session_title` from prompt/turn/stop payloads.
9. `TaskStarted` and `Notification` did not fire in the exercised flows; `StopFailure` never fired.

## Timing Facts

| Fact | Value |
| --- | --- |
| `SessionStart` awaited at session create | 0.226–0.266 s after the creating prompt (fresh TUI); 0.796 s after resume launch (`--continue` creates at launch); 3.245 s with a `sleep 3` hook |
| `SessionEnd` awaited at close | normal TUI exit path 0.97 s; T1 with `sleep 3` 3.98 s; headless none |
| Heartbeat cadence | 60 s; `uptime_ms` 60001 at first tick, then 120000, 180001, 240001, 300000 |
| Turn wall times | short OK turns 3.5–6 s; README turn 12.8 s; essay turns 60–100 s; compaction 7.2 s |
| Tool events | `PreToolUse` → `PostToolUse` gap 62 ms (Bash), 481 ms (Write allow, includes the approval wait), 58 ms (Read), 1.339 s (Agent, includes the subagent run) |
| Permission window | request → result 0.425 s allow (includes tool execution), 0.238 s deny |
| Hook delivery | HTTP path receives events within the runner's polling granularity; collector stamps are millisecond UTC + monotonic; fallback `emitter_seq` preserves order |

Lifecycle comparison: `SessionStart` is registered on `onDidCreateSession` and awaited there. The TUI defers session creation to the first message, so the observable timing is 0.24 s after the creating prompt, before that prompt's `UserPromptSubmit`. This is distinct from the Codex 0.163 lane, which dispatched `SessionStart` lazily on the first turn; kimi's hook is awaited at create, but create itself is lazy in the TUI.
