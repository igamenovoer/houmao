# Evidence: S6 queued/steered input (codex-cli 0.163.0, openlux-auto lane)

Date: 2026-10-20. Iteration: [plan 1](../iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md). Arm: S6. Key question: [KQ-3](../key-questions/KQ-3-delivery-semantics.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/codex-hook-capture/s6/run-20261020T041916Z/` (tmux `codexhook-s6-2952371`, pane `%182`) |
| Lane | `openlux-auto` |
| Flags | `--dangerously-bypass-hook-trust` |
| Collector | gen 1, port 37731 |
| Recording | 576 samples at 0.2 s, non-empty, not tainted |
| Labels | `s6-first-turn`, `s6-queued-turn` filled with digests |

Command:

```bash
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s6
```

## Ordered Event Sequence

| Seq | Event | received_at_utc | turn_id | Prompt / message |
| --- | --- | --- | --- | --- |
| 1 | `SessionStart` | 04:19:23.892 | - | startup |
| 2 | `UserPromptSubmit` | 04:19:23.935 | `01a15789-143b-74d1-b93b-116f813cc99f` | `Write a long essay about queues.` |
| 3 | `UserPromptSubmit` | 04:19:29.387 | `01a15789-143b-74d1-b93b-116f813cc99f` **(same)** | `Reply with exactly: OK` |
| 4 | `Stop` | 04:19:40.172 | `01a15789-143b…` | `last_assistant_message: "OK"` |
| 5 | `SessionEnd` | 04:23:41.194 | - | `reason: "other"` after `/quit` |

No second `Stop` arrived. The runner waited the predeclared 240 s for occurrence 2 and recorded `false`; the semantic observation is that no separate turn existed at all.

## Ordering Answer (catalog-critical)

- The second prompt's Enter was at **04:19:26.493**, while the first turn was busy.
- Its `UserPromptSubmit` arrived at **04:19:29.387**, 2.9 s after Enter and **10.8 s before the first Stop**. It is therefore delivered during generation, not at consumption.
- Its `turn_id` is **identical** to the first prompt's turn_id. There is no new turn.
- The single `Stop` at 04:19:40.172 has `last_assistant_message: "OK"`: the steer redirected the running turn, so the essay was abandoned and the final answer is the OK reply.
- Pane: `› Write a long essay about queues.`, then `› Reply with exactly: OK`, then `• OK` and `Worked for 16s`, all in one turn block.

**Correction to the predeclared expectation:** the plan's "queue drain" model (second turn's Stop after the first Stop) does not apply at 0.163.0. The TUI steers the second prompt into the current turn. The correct ordering rule is: a mid-turn `UserPromptSubmit` can arrive before the current turn's `Stop`, shares the current `turn_id`, and does **not** produce a second `Stop`. A reducer that waits for a new turn after a mid-turn prompt will hang or mis-correlate.

The 2.9 s delay between Enter and the hook is the steer-acceptance path (the TUI queues the text and the core inspects it), not keystroke time; it is still well before consumption/completion.

## Payload Inventory

`UserPromptSubmit` payloads contain: `cwd`, `hook_event_name`, `model`, `permission_mode`, `prompt`, `session_id`, `transcript_path`, `turn_id`. The optional `agent_id`/`agent_type` fields are absent. Both mid-turn and turn-start prompts have the same shape; only `turn_id` distinguishes whether they belong to a fresh turn.

`Stop` contains the usual fields (`last_assistant_message`, `stop_hook_active`, `turn_id`, etc.) with `stop_hook_active: false`.

## Driver Fix

The original runner waited 240 s for a second `Stop`. After this capture answered the question, the runner was changed to wait only 15 s for the second Stop and to record the prompt/stop turn_id lists in `run-summary.json` (`run_capture.py`, `run_s6`). The capture above used the old wait, which is why the run wall time includes ~240 s of dead time after the single Stop; the hook evidence is unaffected.

## KQ Verdict

**KQ-3 ordering confirmed and corrected.** A second prompt submitted while busy is a steer: its `UserPromptSubmit` fires mid-turn, before `Stop`, with the current `turn_id`; the turn then completes once, with the steered answer. There is no queued second turn in TUI mode at 0.163.0.
