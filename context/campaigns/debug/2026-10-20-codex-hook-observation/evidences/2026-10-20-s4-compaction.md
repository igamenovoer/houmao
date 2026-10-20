# Evidence: S4 manual compaction (codex-cli 0.163.0, openlux-auto lane)

Date: 2026-10-20. Iteration: [plan 1](../iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md). Arm: S4. Key questions: [KQ-2](../key-questions/KQ-2-event-availability-payloads.md), [KQ-3](../key-questions/KQ-3-delivery-semantics.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/codex-hook-capture/s4/run-20261020T041644Z/` (tmux `codexhook-s4-2945338`, pane `%178`) |
| Lane | `openlux-auto`, profile `openlux-auto.config.toml` |
| Flags | `--dangerously-bypass-hook-trust` |
| Workdir | contains `README.md` created by the runner |
| Collector | gen 1, port 44419 |
| Recording | 400 samples at 0.2 s, non-empty, not tainted |
| Labels | `s4-readme-turn`, `s4-compact`, `s4-post-compact-turn` filled with digests |

Command:

```bash
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s4
```

## Ordered Event Sequence

| Seq | Event | received_at_utc | turn_id | Key fields |
| --- | --- | --- | --- | --- |
| 1 | `SessionStart` | 04:16:52.054 | - | `source: startup` |
| 2 | `UserPromptSubmit` | 04:16:52.097 | `01a15786-c317-7ee3-8530-33c8c4ea359e` | README prompt |
| 3 | `PreToolUse` | 04:16:58.889 | `01a15786-c317…` | `tool_name: Bash`, `tool_input: {"command": "cat README.md"}`, `tool_use_id: exec-67118651-bf20-400d-b9d8-1e1eda6d9202` |
| 4 | `PostToolUse` | 04:16:58.976 | `01a15786-c317…` | same `tool_use_id`, `tool_response` = README text |
| 5 | `Stop` | 04:17:05.424 | `01a15786-c317…` | one-sentence README summary |
| 6 | `PreCompact` | 04:17:05.700 | `01a15786-f878-70e1-b0c7-2a64c89993c6` | `trigger: "manual"` |
| 7 | `PostCompact` | 04:17:17.271 | `01a15786-f878…` | `trigger: "manual"` |
| 8 | `SessionStart` | 04:17:17.871 | - | `source: "compact"` |
| 9 | `UserPromptSubmit` | 04:17:17.915 | `01a15787-27fd-7823-b724-1efd9ad5712a` | post-compact `OK` prompt |
| 10 | `Stop` | 04:18:14.348 | `01a15787-27fd…` | `last_assistant_message: "OK"` |
| 11 | `SessionEnd` | 04:18:14.868 | - | `reason: "other"` |

## Compaction Observations

- `/compact` Enter 04:17:05.655 → `PreCompact` 45 ms later. The TUI compaction indicator (`Compacting context (11s • esc to interrupt)` / `Making room to continue.`) appears at s000092 and clears at s000143.
- `PostCompact` arrives 11.57 s after `PreCompact`, matching the on-screen 11 s counter.
- **`turn_id` continuity is broken by compaction.** The compaction events carry their own turn_id (`01a15786-f878…`), distinct from the preceding turn (`c317…`) and the following turn (`01a15787-27fd…`). The reducer must not stitch a post-compaction turn onto the pre-compaction turn by turn_id alone; `SessionStart(source="compact")` is the boundary marker.
- **`SessionStart(source="compact")` timing:** it is queued during compaction (`session/mod.rs:4423`) and dispatched by `run_pending_session_start_hooks` at the next turn start (`session/turn.rs:340`). Empirically it arrives 52 ms after the post-compact prompt's Enter and 44 ms before that turn's `UserPromptSubmit`. Waiting for it immediately after `PostCompact`, before any new prompt, would hang. The runner was corrected to wait after submitting the post-compact prompt.
- The post-compact turn itself took 56.4 s on OpenLux, much longer than the pre-compaction turn (13.3 s from prompt to Stop); this is provider latency, not a hook delay.

## Field Inventory vs Generated Schemas

| Event | Live fields | Schema-optional absent | Notes |
| --- | --- | --- | --- |
| `PreCompact` | `cwd`, `hook_event_name`, `model`, `session_id`, `transcript_path`, `trigger`, `turn_id` | `agent_id`, `agent_type` | no `permission_mode` |
| `PostCompact` | same as `PreCompact` | `agent_id`, `agent_type` | no `permission_mode` |
| `SessionStart(compact)` | `cwd`, `hook_event_name`, `model`, `permission_mode`, `session_id`, `source`, `transcript_path` | none | no `turn_id` |
| `PreToolUse` | full schema set | `agent_id`, `agent_type` | `tool_name: "Bash"`, `tool_input.command` |
| `PostToolUse` | full schema set + `tool_response` | `agent_id`, `agent_type` | `tool_response` is a string |

All schema `required` fields were present; no unknown fields appeared. `transcript_path` was non-null throughout; `permission_mode` was `bypassPermissions` on the turn events and absent on compaction events.

## KQ Verdicts

- **KQ-2:** `PreCompact`/`PostCompact` are live with `trigger: "manual"`; `SessionStart(source="compact")` is live. Both compaction events omit `permission_mode`, matching their schemas.
- **KQ-3:** `turn_id` is turn-scoped, but compaction allocates a separate turn_id for the compaction operation. `SessionStart(compact)` is the reliable boundary and is dispatched at the next turn start, not at `PostCompact`. `SessionEnd` follows a clean `/quit`.
