# Evidence: S4 manual compaction (kimi 2.2.0)

Date: 2026-10-20. Iteration: [iteration 1](../iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md). Arm: S4. Key questions: [KQ-2](../key-questions/KQ-2-event-availability-payloads.md), [KQ-3](../key-questions/KQ-3-delivery-semantics.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/kimi-hook-capture/s4/run-20261020T133716Z/` (tmux `kimihook-s4-3901108`, pane `%228`) |
| Tool | kimi 2.2.0, `--auto`, 20 observer entries |
| Workdir | contains a small `README.md` for the first turn |
| Collector | gen 1, port 34769, 12 accepted events |
| Recording | 135 samples; labels `s4-readme-turn`, `s4-compact`, `s4-post-compact-turn` |
| Session | `session_5f455c69-fe92-4fbd-a618-4abf3d105dce`; created by the README prompt |

## Ordered Event Sequence

| Seq | Event | received_at_utc | Key fields |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:37:19.384 | `source=startup` |
| 2 | `UserPromptSubmit` | 13:37:19.482 | README prompt |
| 3 | `TurnStarted` | 13:37:19.541 | `turn_id=0` |
| 4 | `PreToolUse` | 13:37:23.460 | Read tool |
| 5 | `PostToolUse` | 13:37:23.518 | Read result |
| 6 | `Stop` | 13:37:32.308 | first turn end |
| 7 | `PreCompact` | 13:37:32.551 | `trigger=manual`, `token_count=28513` |
| 8 | `PostCompact` | 13:37:39.775 | `trigger=manual`, `estimated_token_count=29056` |
| 9 | `UserPromptSubmit` | 13:37:40.195 | post-compact `Reply with exactly: OK` |
| 10 | `TurnStarted` | 13:37:40.243 | `turn_id=1` (fresh id after compaction) |
| 11 | `Stop` | 13:37:45.200 | post-compact turn end |
| 12 | `SessionEnd` | 13:37:46.172 | `reason=exit` |

## Measurements

| Fact | Value |
| --- | --- |
| Ready composer | 2.838 s |
| `SessionStart` | 0.226 s after the README prompt |
| First turn | 13:37:19.48 → `Stop` 13:37:32.31 (12.8 s) |
| Compaction window | `PreCompact` 13:37:32.551 → `PostCompact` 13:37:39.775 = **7.224 s** |
| `PreCompact` fields | `token_count=28513`, `trigger=manual`; no `estimated_token_count`, no `turn_id` |
| `PostCompact` fields | `estimated_token_count=29056`, `trigger=manual`; no `token_count`, no `turn_id` |
| Post-compact turn | `turn_id=1` (was 0 before), same `session_id`; `Stop` 5.0 s after prompt |

No `TurnStarted`/`Stop`/`turn_id` exists for the internal compaction operation; `PreCompact`/`PostCompact` bracket it directly after the first `Stop`. Posture continuity is the `session_id` staying constant across the pair.

## Payload Observations

- `PreCompact.token_count` is an int (28513); `PostCompact.estimated_token_count` is an int (29056). The two fields are not interchangeable; each event carries only its own count.
- Neither compaction event has `turn_id` or `prompt_id`.
- The post-compact turn starts a fresh `turn_id` (1) under the same session; `Stop` has no `turn_id`.
- `session_title` stays the first prompt's title across compaction.

## Verdict

**PASS.** Real `PreCompact`/`PostCompact(trigger=manual)` with token counts, a 7.2 s maintenance window, and a clean post-compact turn with a fresh `turn_id`.

## Harness Corrections (2026-10-20)

- Scenario opening now submits the README prompt before requiring `SessionStart` (lazy session creation).

## Cleanup

`kimihook-s4-3901108` exited via `/exit`; collector stopped. Run root retained under `tmp/kimi-hook-capture/s4/`.
