# Evidence: S7 queue + resume (claude 2.1.303, DeepSeek relay, deepseek-flash[1m])

Date: 2026-10-19. Iteration: [iteration 1](../iterations/2026-10-19-plan-1-hook-capture-matrix.md). Arm: S7 queue + resume. Key question: [KQ-2](../key-questions/KQ-2-delivery-semantics.md) (event ordering at queue consumption; resume SessionStart source).

## Run Identity

| Component | Value |
| --- | --- |
| Run root (primary) | `tmp/hook-capture/s7/run-20261019T135815Z/` — session 1 tmux `hookcap-s7-1885631` (430 samples), resume session tmux `hookcap-s7-resume-1885631` (31 samples, `pane-recording-resume/`) |
| Prior attempts (queue+resume evidence identical; aborted on two distinct harness gate bugs, both fixed) | `run-20261019T135152Z` (picker rows matched the bare-`❯` composer marker → model gate ran on the picker), `run-20261019T135559Z` (resumed TUI does not re-render the model banner → gate could not match). Fixes: resume by explicit session id; picker-absence wait; `check_model=False` for the resume phase (same wrapper/pins as the gated gen-1 launch). |
| Tool | `claude` 2.1.303, skip-permissions lane |
| Collector | gen 1 port 33451 (13:58:15), gen 2 port 45369 (13:59:53); gen-2 `channel.json` pair present; `last_sequence` resumed across generations (no sequence collision) |
| Labels | 3 ranges filled (`s7-first-turn` s000002–s000425, `s7-queued-turn` s000426–s000428, `s7-resume` = resume recording s000001–s000031) |
| Hook stream | 6 events, `events.ndjson` SHA-256 `88b641ca…` |

## Ordered Event Sequence

| Seq | Gen | Event | received_at_utc | Notable payload fields |
| --- | --- | --- | --- | --- |
| 1 | 1 | `SessionStart` | 13:58:15 | `source: startup`, `session_id bd3c1458-…` |
| 2 | 1 | `UserPromptSubmit` | 13:58:15 | `prompt: Write a long essay about queues.`, `prompt_id 95001241` |
| 3 | 1 | `UserPromptSubmit` | 13:58:21 | `prompt: Reply with exactly: OK` — **typed while busy; fired 89 s before turn 1 ended**; carries the **in-flight turn's** `prompt_id 95001241` |
| 4 | 1 | `Stop` | 13:59:50 | essay answer; `prompt_id 95001241` |
| 5 | 1 | `Stop` | 13:59:51 | `last_assistant_message: OK`; **new `prompt_id c3142720`** — the queued turn's own id, appearing only at its Stop |
| 6 | 2 | `SessionStart` | 13:59:53 | **`source: resume`, same `session_id bd3c1458-…`** (delivered via emitter POST after the generation bump) |

## Arm Questions vs Observed

| Predeclared | Observed | Verdict |
| --- | --- | --- |
| Does the queued prompt's `UserPromptSubmit` fire at type time or consumption time? | **Type time** (13:58:21, mid-generation), with the in-flight turn's `prompt_id`; consumption produces only the second `Stop` (new `prompt_id`) | answered |
| Event ordering at queue consumption | `UserPromptSubmit, UserPromptSubmit, Stop(essay), Stop(OK)` — both UPS precede both Stops; the two Stops arrive back-to-back (~1 s) at consumption | answered |
| Resume picker appearance and shape | With bare `--resume` (attempt 1): cross-project picker with auto-generated session titles (`Background sleep 90 command`, `README.md summary`), timestamps, branch, transcript sizes, `Ctrl+A/B/W`, `Type to search`, `Esc to cancel` — saved to `notes/s7-resume-launch-surface.txt`. With explicit `--resume <session_id>` (attempt 3): **no picker at all** | answered |
| New `SessionStart` source on resume | `source: resume` (design-predicted); **same `session_id`** persists across the resume boundary | **holds** |

## prompt_id Identity Nuance (for the KQ-3 catalog)

A queued prompt's `UserPromptSubmit` is stamped with the **currently-running turn's** `prompt_id`; its own turn's identity appears only on the resulting `Stop` (fresh `prompt_id`). Correlating a queued UPS to its Stop by `prompt_id` will fail — correlate by order/adjacency instead. (Normal same-turn UPS→Stop pairs do share `prompt_id`, as in S1/S4.)

## Harness Fixes This Arm (ruff-clean)

1. `run_s7` resumes by explicit session id read from the gen-1 `SessionStart` payload (deterministic; picker path kept as fallback).
2. Fallback picker path waits for picker dismissal (`Type to search` absence) before the composer/model gate.
3. `bootstrap_session(check_model=False)` for the resume phase: the resumed TUI restores the transcript and the model banner is not visible; the launch lane (wrapper env, model pins) is byte-identical to the gen-1 launch that passed the gate.

## Gate Verdicts

| Gate | Verdict |
| --- | --- |
| G2 (S7 scope) | **PASS** — queue, double-Stop, and resume SessionStart all produced events |
| G3 (pairing) | **PASS** for session 1 (430 samples + gen-1 stream + labels) and the resume phase (31 samples + gen-2 stream + labels); both generations' monotonic/UTC pairs recorded |

## Cleanup

Both tmux sessions killed by teardown; collectors SIGTERMed per generation; no leftovers.
