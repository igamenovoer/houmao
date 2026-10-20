# Evidence: S5 Esc interrupt (codex-cli 0.163.0, openlux-auto lane)

Date: 2026-10-20. Iteration: [plan 1](../iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md). Arm: S5. Key questions: [KQ-2](../key-questions/KQ-2-event-availability-payloads.md), [KQ-3](../key-questions/KQ-3-delivery-semantics.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/codex-hook-capture/s5/run-20261020T041843Z/` (tmux `codexhook-s5-2950157`, pane `%180`) |
| Lane | `openlux-auto` |
| Flags | `--dangerously-bypass-hook-trust` |
| Collector | gen 1, port 36439 |
| Recording | 71 samples at 0.2 s, non-empty, not tainted |
| Labels | `s5-generation`, `s5-post-escape` filled with digests |

Command:

```bash
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s5
```

## Ordered Event Sequence

| Seq | Event | received_at_utc | turn_id | Key fields |
| --- | --- | --- | --- | --- |
| 1 | `SessionStart` | 04:18:50.209 | - | `source: startup`, `model: gpt-6.1-sol`, `permission_mode: bypassPermissions` |
| 2 | `UserPromptSubmit` | 04:18:50.256 | `01a15788-9092-70c1-bc8b-5872ffa34613` | essay prompt |
| 3 | `Interrupt` | 04:18:53.183 | `01a15788-9092…` (same) | no reason field |
| 4 | `SessionEnd` | 04:18:59.144 | - | `reason: "other"` |

No `Stop` arrived for the aborted turn (count before Escape = 0, after the 5 s settle = 0). No `PreToolUse`/`PostToolUse` (no tool call before the abort).

## Timing and TUI Behavior

- Prompt Enter 04:18:50.128; `UserPromptSubmit` 128 ms later.
- Busy visible from s000030 (`Working (0s … esc to interrupt)`); Escape sent 04:18:53.135, 2.5 s after the busy marker and before any assistant text rendered.
- `Interrupt` delivered 48 ms after Escape. The same turn_id as the prompt.
- Pane at s000050 (04:18:54): `■ Conversation interrupted - use /feedback if something went wrong`, with the user prompt still in history and an **empty composer**. The draft prompt was **not** restored into the composer on 0.163.0; the exit path is clean because the composer holds no text (the runner still sends `C-u` before `/quit`).
- `/quit` Enter 04:18:59.100; `SessionEnd` 44 ms later.

## Field Inventory vs Generated Schema

Schema `interrupt.command.input.schema.json` requires: `cwd`, `hook_event_name`, `model`, `permission_mode`, `session_id`, `transcript_path`, `turn_id`.

Live payload contains exactly those seven fields. There is **no** `reason` field (unlike Claude's interrupt payload), no `last_assistant_message`, and no `stop_hook_active`. `transcript_path` is a non-null string; `permission_mode` is `bypassPermissions`.

## KQ Verdicts

- **KQ-2:** `Interrupt` is live and carries only the common turn fields plus no reason. The schema matches the live payload exactly.
- **KQ-3:** Esc produces `Interrupt` and **not** `Stop`; latency is 48 ms. The turn is terminal for the reducer at `Interrupt`. The post-Esc composer is empty, so the Claude-lane draft-restore exit flaw does not reproduce here.
