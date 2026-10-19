# Evidence: S4 compaction (claude 2.1.303, DeepSeek relay, deepseek-flash[1m])

Date: 2026-10-19. Iteration: [iteration 1](../iterations/2026-10-19-plan-1-hook-capture-matrix.md). Arm: S4 compaction. Key questions: [KQ-2](../key-questions/KQ-2-delivery-semantics.md), [KQ-3](../key-questions/KQ-3-payload-catalog.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root (primary) | `tmp/hook-capture/s4/run-20261019T133729Z/` (tmux `hookcap-s4-1843190`, 56 pane samples 13:37:29–13:37:42) |
| First attempt | `run-20261019T133547Z/` — captured the same compaction arc but the runner's Stop wait reused occurrence 1 (harness bug, fixed) and tore down before the post-compact turn's Stop; retained as supporting evidence |
| Tool | `claude` 2.1.303 via `claude-deepseek` lane (bypass posture) |
| Observer settings | 9 v1 events incl. `PreCompact`/`PostCompact` |
| Collector | gen 1, started 13:37:29 UTC / monotonic 3471799.922919 (pair present) |
| Model verification | banner `deepseek-flash[1m]` (gate passed) |
| Labels | 3 ranges filled (`s4-readme-turn` s000002–s000015, `s4-compact` s000016–s000045, `s4-post-compact-turn` s000046–s000054) |
| Hook stream | 9 events, `events.ndjson` SHA-256 `3399786a…`; session_id constant `33082ee7-…` in every event |

## Ordered Event Sequence

| Seq | Event | received_at_utc | Notable payload fields |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:37:29 | `source: startup`, `model`, `cwd`, `transcript_path` + emitter stamps |
| 2 | `UserPromptSubmit` | 13:37:29 | `prompt` (README prompt), `prompt_id` (`a588d458-…`), `permission_mode: bypassPermissions` |
| 3 | `PostToolUse` | 13:37:31 | `tool_name: Read`, `tool_use_id`, `tool_input`, `tool_response`, `duration_ms` |
| 4 | `Stop` | 13:37:32 | `prompt_id` matches #2; `last_assistant_message` (one-sentence README summary) |
| 5 | `PreCompact` | 13:37:33 | `trigger: manual`, `custom_instructions: null`, `prompt_id` (`2d57366c-…`, the internal compaction turn), `session_id`, `cwd`, `transcript_path` |
| 6 | `SessionStart` | 13:37:39 | **`source: compact`** — second SessionStart fired by the provider mid-compaction, delivered via the emitter command hook (emitter stamps present); same `session_id` |
| 7 | `PostCompact` | 13:37:39 | `trigger: manual`, `compact_summary` (4717 chars), same envelope fields; `prompt_id` = #5's |
| 8 | `UserPromptSubmit` | 13:37:40 | OK prompt, **new** `prompt_id` (`80c5bcc4-…`) |
| 9 | `Stop` | 13:37:41 | `prompt_id` matches #8; `last_assistant_message: OK` |

## Timing

- README turn: submit 13:37:29 → Stop 13:37:32 (≈3 s).
- **Compaction window: PreCompact 13:37:33 → PostCompact 13:37:39 ≈ 6 s** (deepseek generating the 4.7 k-char summary). The compact `SessionStart` lands in the same second as `PostCompact`, immediately before it (command-hook POST vs HTTP hook ordering preserved by the collector).
- Post-compact turn: submit 13:37:40 → Stop 13:37:41 (≈1 s).

## `/compact` Submission Behavior

Typing `/compact` opens the autocomplete menu with `/compact` preselected (`❯ /compact Free up context by summarizing the…`, sample s000016). A **single Enter executes the preselected command directly** — no second Enter, no picker adaptation needed on 2.1.303. Driver logged the menu frame; no deviation required.

## Arm Expectation vs Observed

| Predeclared | Observed | Verdict |
| --- | --- | --- |
| `PreCompact`/`PostCompact` payloads | Both captured; `trigger`, `custom_instructions` (null), 4.7 k-char `compact_summary` | **holds** |
| Turn identity continuity across compaction | `session_id` identical in all 9 events; per-turn `prompt_id` pairing intact pre- and post-compaction; the compaction window carries its own internal `prompt_id` | **holds** |

## Design-Contract Notes

- Design section 4 predicts `SessionStart` with `source=compact`; **observed exactly** (and it rides the command-hook path, proving the emitter→collector POST works for mid-session starts, not just process start).
- `PreCompact.custom_instructions` is present-but-null for a bare `/compact` (no compaction instructions configured) — catalog should record it as a nullable field.
- Compaction emits **no `Stop`** for the internal compaction turn (its terminal is `PostCompact`); trackers must treat `PostCompact` as the maintenance-window end, not await a Stop.

## Gate Verdicts Informed

| Gate | Verdict | Evidence |
| --- | --- | --- |
| G2 (S4 scope) | **PASS** | every exercised family (`SessionStart`, `UserPromptSubmit`, `PostToolUse`, `Stop`, `PreCompact`, `PostCompact`) produced events; silent families named (`StopFailure`, `PermissionRequest`, `PostToolUseFailure` not exercised) |
| G3 (pairing) | **PASS** | 56 samples + 9-event stream + 3 labels; monotonic/UTC pair present |

## Cleanup

tmux session killed by teardown; collector SIGTERMed; no leftovers.
