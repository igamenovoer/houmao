# Evidence: S5 background work (claude 2.1.303, DeepSeek relay, deepseek-flash[1m])

Date: 2026-10-19. Iteration: [iteration 1](../iterations/2026-10-19-plan-1-hook-capture-matrix.md). Arm: S5 background. Key question: [KQ-4](../key-questions/KQ-4-background-work.md) (what, if anything, fires at background-task completion).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/hook-capture/s5/run-20261019T134126Z/` (tmux `hookcap-s5-1849527`, 682 pane samples 13:41:26–13:43:59) |
| Tool | `claude` 2.1.303, skip-permissions lane |
| Collector | gen 1, started 13:41:26 UTC / monotonic 3472036.956833 (pair present) |
| Labels | 2 ranges filled (`s5-background-turn` s000002–s000009, `s5-idle-wait` s000010–s000409) |
| Hook stream | 6 events, `events.ndjson` SHA-256 `a785f5d9…` |

## Ordered Event Sequence (everything that arrived, 13:41:26 → 13:43:59)

| Seq | Event | received_at_utc | Notable payload fields |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:41:26 | standard |
| 2 | `UserPromptSubmit` | 13:41:26 | frozen prompt verbatim; `prompt_id b8a59290` |
| 3 | `PostToolUse` | 13:41:28 | `tool_name: Bash`, `tool_input {command: "sleep 90", description: "Sleep for 90 seconds in background", run_in_background: true}`, `tool_response {backgroundTaskId: "byx3d0ps2", interrupted: false, …}` |
| 4 | `Stop` | 13:41:29 | **`background_tasks: [{command, description, id: "byx3d0ps2", status: "running", type: "shell"}]`** (non-empty, exact shape); `last_assistant_message: "DONE"` (model answered immediately, before the sleep finished); `session_crons: []` |
| 5 | `UserPromptSubmit` | 13:42:58 | **GHOST TURN** — no driver input; `prompt` is a provider-authored `<task-notification>` XML block (`<task-id>byx3d0ps2</task-id>`, `<tool-use-id>…`, `<status>completed</status>`, `<summary>Background command "Sleep for 90 seconds in background" completed (exit code 0)</summary>`); **new `prompt_id 403e2f45`** |
| 6 | `Stop` | 13:43:00 | `background_tasks: []` (task drained); `last_assistant_message: "DONE"` |

Nothing else arrived during the 150 s idle window: no `Notification`, no task-lifecycle event, no `StopFailure`. Complete post-Stop event list: `['UserPromptSubmit', 'Stop']` (from `run-summary.json`).

## Timing

- Background task start (PostToolUse#3): 13:41:28. Task completion → ghost `UserPromptSubmit`#5: 13:42:58 — **≈90.0 s**, exactly the sleep duration.
- Ghost turn duration: UPS#5 13:42:58 → Stop#6 13:43:00 (≈2 s).
- Driver input during 13:41:29→13:43:59: none (input log shows only waits).

## Pane Corroboration (P4.5)

- During the idle window the pane shows a running-background indicator: dock `✻ Cogitated for 2s · done 9:41 PM · 1 shell still running` and footer `⏵⏵ bypass permissions on · 1 shell · ↓ to manage` (first at s000010 13:41:28, sample s000300).
- At completion the indicator clears and the transcript renders `● Background command "Sleep for 90 seconds in background" completed (exit code 0)` (s000410 13:42:58), followed by the ghost generation (`esc to interrupt` footer returns during it).

## Arm Expectation vs Observed

| Predeclared | Observed | Verdict |
| --- | --- | --- |
| `Stop` with `background_tasks` | Non-empty `[{id, command, description, status: running, type: shell}]` at turn end; drained to `[]` after completion | **holds** |
| Whatever fires at sleep completion, recorded | A full provider-initiated turn: `UserPromptSubmit` carrying the `<task-notification>` + its `Stop` | **holds — and this answers KQ-4** |
| Model compliance | `run_in_background: true` honored; but the model replied `DONE` immediately at turn 1 (before the sleep finished), then again at the ghost turn. Model-behavior nuance, recorded; no rewording needed (background behavior occurred) | noted |

## KQ-4 Answer (evidence-backed)

Background completion **is** visible on the hook channel: the provider synthesizes a user turn whose `UserPromptSubmit.prompt` is a `<task-notification>` XML document identifying the task (`task-id`, `tool-use-id`, `status`, `summary`). A tracker can detect background completion as a **ghost `UserPromptSubmit`** (turn-start fact, no human origin — exactly design 1.1's caveat) followed by a normal `Stop`. No dedicated task/notification event exists in the v1 subscribed set; the payload-mirror fallback is **not** needed as the v1 limit.

## Design-Contract Notes

- `Stop.background_tasks` shape recorded for the KQ-3 catalog: `[{command, description, id, status, type}]`.
- The TUI visibly surfaces hook execution during turns: spinner text `(running UserPromptSubmit hook · 0s)` observed (s000002) — hook latency is user-visible on this build.
- Design 1.1's warning is directly exercised: `UserPromptSubmit` fired with zero human input; prompt text is a machine notification, so prompt-content heuristics must exclude `<task-notification>` sources.

## Gate Verdicts

| Gate | Verdict |
| --- | --- |
| G2 (S5 scope) | **PASS** — exercised families all produced events; `StopFailure`/`PermissionRequest`/`PreCompact`/`PostCompact`/`PostToolUseFailure` not exercised (named) |
| G3 (pairing) | **PASS** — 682 samples + 6-event stream + 2 labels; monotonic/UTC pair present |

## Cleanup

tmux killed by teardown; collector SIGTERMed; no leftovers.
