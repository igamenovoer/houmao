# Evidence: S1 normal multi-turn (codex-cli 0.163.0, openlux-auto lane)

Date: 2026-10-20. Iteration: [plan 1](../iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md). Arm: S1. Key questions: [KQ-2](../key-questions/KQ-2-event-availability-payloads.md), [KQ-3](../key-questions/KQ-3-delivery-semantics.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/codex-hook-capture/s1/run-20261020T041527Z/` (tmux `codexhook-s1-2942706`, pane `%176`) |
| Lane | `openlux-auto`, launcher `codex-openlux-auto`, profile `openlux-auto.config.toml` |
| Flags | `--dangerously-bypass-hook-trust` |
| Hooks | `hooks.json` 14 events, sha256 `5b0c1325…` |
| Collector | gen 1, port 41955 |
| Recording | 125 samples at 0.2 s, non-empty, not tainted |
| Labels | `s1-turn-1`, `s1-turn-2`, `s1-exit` filled with digests |
| Model | payload `gpt-6.1-sol`; status line `GPT-6.1-Sol default` |

Command:

```bash
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s1
```

## Ordered Event Sequence

| Seq | Event | received_at_utc | turn_id | Other key fields |
| --- | --- | --- | --- | --- |
| 1 | `SessionStart` | 04:15:34.822 | - | `source: startup`, `model: gpt-6.1-sol`, `permission_mode: bypassPermissions`, `transcript_path` non-null |
| 2 | `UserPromptSubmit` | 04:15:34.865 | `01a15785-9567-7093-b921-201af65bd4b0` | prompt `Reply with exactly: OK` |
| 3 | `Stop` | 04:15:40.370 | `01a15785-9567…` (same) | `last_assistant_message: "OK"`, `stop_hook_active: false` |
| 4 | `UserPromptSubmit` | 04:15:40.966 | `01a15785-ad78-75e0-b940-bad4dfc80868` | tool prompt |
| 5 | `PreToolUse` | 04:15:47.899 | `01a15785-ad78…` | `tool_name: "Bash"`, `tool_use_id: exec-a78c846f-d864-46fd-b610-6d24a009b007`, `tool_input: {"command": "printf 'hello' > /tmp/houmao-codex-hook-s1.txt\necho done"}` |
| 6 | `PostToolUse` | 04:15:48.000 | `01a15785-ad78…` | same `tool_name` and `tool_use_id`, plus `tool_response: "done\n"` |
| 7 | `Stop` | 04:15:54.838 | `01a15785-ad78…` | `last_assistant_message: "Created \`/tmp/houmao-codex-hook-s1.txt\` containing \`hello\`. Output: \`done\`."` |
| 8 | `SessionEnd` | 04:15:55.435 | - | `reason: "other"` |

**Turn correlation:** `turn_id` is identical for `UserPromptSubmit` #2, `Stop` #3 (turn 1) and for `UserPromptSubmit` #4, `PreToolUse` #5, `PostToolUse` #6, `Stop` #7 (turn 2). The two turns have different UUIDv7 values with the same time prefix. This confirms `turn_id` is the per-turn correlation key.

**Tool pairing:** `PreToolUse` and `PostToolUse` share `tool_use_id` exactly (`exec-a78c846f-d864-46fd-b610-6d24a009b007`), one pair for one Bash call. The model chose **Bash** rather than `apply_patch`; `tool_input` is a JSON object with a single `command` key and `tool_response` is a plain string (`"done\n"`), not an object.

## Catalog Finding: PreModelRequest / PostModelRequest do not fire

Both counts are **0** in this two-turn session, including the turn that issued a tool call. The generated schema set contains `model-request.command.input.schema.json` (a shared `oneOf` schema for both names), but no live `PreModelRequest` or `PostModelRequest` payload was delivered, and the 0.163.0 hook review set (12 events) excludes both names. This is a catalog finding, not a harness failure: the events are declared and hashed by `hash_hook.py`, but the installed binary does not dispatch them in TUI mode. A future `codex exec` arm (S8, optional) is the remaining place to test whether another frontend emits them.

Across all six scenario runs (S1, S4, S5, S6, S7, F1), **no `SubagentStart`/`SubagentStop` and no `PermissionRequest`** appeared; no `agent_id`/`agent_type` fields were present. `PermissionRequest` is deferred to S3, which was skipped in this task.

## Field Inventory vs Generated Schemas

Every live payload contains all schema `required` fields and no unknown fields. Only the optional subagent fields are absent.

| Event | Live fields | Schema-optional fields absent | Notes |
| --- | --- | --- | --- |
| `SessionStart` | `cwd`, `hook_event_name`, `model`, `permission_mode`, `session_id`, `source`, `transcript_path` | none | `transcript_path` non-null string |
| `UserPromptSubmit` | `cwd`, `hook_event_name`, `model`, `permission_mode`, `prompt`, `session_id`, `transcript_path`, `turn_id` | `agent_id`, `agent_type` | no `source` field |
| `PreToolUse` | `cwd`, `hook_event_name`, `model`, `permission_mode`, `session_id`, `tool_input`, `tool_name`, `tool_use_id`, `transcript_path`, `turn_id` | `agent_id`, `agent_type` | `tool_input` object; `tool_use_id` string |
| `PostToolUse` | `cwd`, `hook_event_name`, `model`, `permission_mode`, `session_id`, `tool_input`, `tool_name`, `tool_response`, `tool_use_id`, `transcript_path`, `turn_id` | `agent_id`, `agent_type` | `tool_response` string |
| `Stop` | `cwd`, `hook_event_name`, `last_assistant_message`, `model`, `permission_mode`, `session_id`, `stop_hook_active`, `transcript_path`, `turn_id` | none | `stop_hook_active` boolean |
| `SessionEnd` | `cwd`, `hook_event_name`, `reason`, `session_id`, `transcript_path` | none | no `turn_id`, no `model` |

Schema source: `extern/orphan/codex/codex-rs/hooks/schema/generated/*.command.input.schema.json`.

Nullability: the schemas permit `null` for `transcript_path` and `last_assistant_message`; every live value in this run was a non-null string. `tool_input` and `tool_response` are free-form in the schema (`true`); live shapes were an object and a string respectively. `stop_hook_active` is a boolean (`false`). `reason` is the constant string `"other"` in this build.

## Delivery Latency

- Turn 1 Enter 04:15:34.757 → `UserPromptSubmit` 108 ms; `Stop` 5.61 s after Enter.
- Turn 2 Enter 04:15:40.918 → `UserPromptSubmit` 48 ms; `PreToolUse` 6.98 s later (model planning time), `PostToolUse` 101 ms after `PreToolUse`; `Stop` 13.92 s after Enter (6.8 s after the tool result).
- `/quit` Enter 04:15:55.391 → `SessionEnd` 44 ms.
- The pane shows `Working (... esc to interrupt)` from s000031 and s000058; the tool command is visible at s000090; the final answer at s000119.

## KQ Verdicts

- **KQ-2:** `PreToolUse`/`PostToolUse` are live and canonical (`tool_name: "Bash"`); `PreModelRequest`/`PostModelRequest` are absent at 0.163.0. Payloads match the schema-required field sets with only optional subagent fields omitted.
- **KQ-3:** `turn_id` correlates all events within a turn and is distinct across turns; `tool_use_id` pairs the tool events. `SessionEnd` arrives 44 ms after a clean `/quit`.
