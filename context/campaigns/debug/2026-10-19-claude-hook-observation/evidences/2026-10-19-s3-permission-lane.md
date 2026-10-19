# Evidence: S3 permission lane (claude 2.1.303, DeepSeek relay, manual mode)

Date: 2026-10-19. Iteration: [iteration 1](../iterations/2026-10-19-plan-1-hook-capture-matrix.md). Arm: S3 permission. Key questions: [KQ-2](../key-questions/KQ-2-delivery-semantics.md), [KQ-3](../key-questions/KQ-3-payload-catalog.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/hook-capture/s3/run-20261019T132946Z/` (tmux session `hookcap-s3-1828209`, 441 pane samples 13:29:46–13:31:25) |
| Tool | `claude` 2.1.303; **s3 lane: launcher env replicated inline, no `--dangerously-skip-permissions`, plus `--permission-mode manual`** |
| Frozen-workload deviation (prominent) | The brief's no-bypass lane boots 2.1.303 into **`auto` permission mode** (first attempt, run-20261019T132241Z, killed): the Write was auto-allowed — no modal, no `PermissionRequest`, plus an on-screen notice that auto-mode classifier billing is incompatible with api.deepseek.com. To make a genuine modal possible the lane pins `--permission-mode manual`. Prompt texts unchanged. Prior contaminated attempts: run-…132241Z (auto mode), run-…132754Z (deny key `2` = "switch to accept edits", write went through). |
| Model verification | banner `deepseek-flash[1m]` (gate passed) |
| Modal key map (verified from snapshots) | Write modal: `1` Yes / `2` switch-to-accept-edits+always-allow-/tmp / `3` No. Bash modal: `1` Yes / `2` allow reading /tmp / `3` switch to auto / `4` No. **Option count and deny key vary by tool.** |
| Collector | gen 1, started 13:29:46 UTC / monotonic 3471336.982915 (pair present) |
| Labels | 2 ranges filled (`s3-permission-allow` s000003–s000024, `s3-permission-deny` s000025–s000033) |
| Hook stream | 9 events, `events.ndjson` SHA-256 `a491e489…`; modal snapshots `notes/s3-allow-modal.txt` `62aa7d5c…`, `notes/s3-deny-modal.txt` `fed047bf…` |

## Ordered Event Sequence

| Seq | Event | received_at_utc | Notable payload fields |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:29:46 | standard + emitter stamps; `source: startup` |
| 2 | `UserPromptSubmit` | 13:29:46 | `prompt` (allow prompt, verbatim from plan), `prompt_id`, `permission_mode` (`default` on this lane) |
| 3 | `PermissionRequest` | 13:29:48 | `tool_name` (`Write`), `tool_input` (`{content, file_path}`), `permission_suggestions` (`[setMode acceptEdits, addDirectories /tmp]`), `permission_mode`, `prompt_id` — **no `tool_use_id`** (matches design) |
| 4 | `PostToolUse` | 13:29:48 | `tool_name`, `tool_use_id`, `tool_input`, `tool_response` (`{type: create, filePath, structuredPatch: [], …}`), `duration_ms` (44), `permission_mode` |
| 5 | `PermissionRequest` | 13:29:49 | second call: `tool_name` (`Bash`), `tool_input` (`{command: cat /tmp/…, description}`) — model-initiated verify step |
| 6 | `PostToolUse` | 13:29:50 | Bash response; `permission_mode` still `default` |
| 7 | `Stop` | 13:29:51 | `last_assistant_message` (`Created /tmp/houmao-hook-allow.txt containing hello.`) |
| 8 | `UserPromptSubmit` | 13:29:51 | deny prompt, new `prompt_id` |
| 9 | `PermissionRequest` | 13:29:52 | `tool_name` (`Write`), `tool_input` for the deny file — **last event of the deny turn** |

## Timing: PermissionRequest vs Modal Paint (shared time base)

- Allow leg: prompt Enter 13:29:46.00 (driver log monotonic 3471337.61) → `PermissionRequest`#3 received 13:29:48 → modal detected and snapshotted 13:29:48 (notes/s3-allow-modal.txt) → key `1` at monotonic 3471339.63. **The hook event leads or coincides with modal paint; the modal's visible dwell was under one 5 fps frame** (no `pane_snapshots` frame contains the Write modal text; only the at-detection snapshot does).
- Deny leg: prompt Enter 13:29:51 → `PermissionRequest`#9 received 13:29:52 → first modal frame s000030 at 13:29:53. Event again precedes paint by ~1 s.
- Exact lead quantification (event `received_at_utc`/`started_monotonic` vs frame `ts_utc`) is a G3/analysis-stage measurement; the paired time bases are present.

## Arm Expectation vs Observed

| Predeclared | Observed | Verdict |
| --- | --- | --- |
| `PermissionRequest` before modal paint | #3/#9 received 1–2 s after prompt, at or before modal frames | **holds** |
| Resolution event on allow | `PostToolUse` #4/#6 after each allowed call | **holds** |
| Silence on deny (design Gap 4: no `PermissionDenied`, `PostToolUseFailure` excludes denials) | After `3` (No): no `PostToolUse`, no `PostToolUseFailure`, no `PermissionDenied` — and additionally **no `Stop` within 90 s**; pane returned to idle; deny file absent | **holds, stronger than designed** |

## Design-Contract Contradictions (highlight)

1. **A denied turn emits no `Stop`.** Design section 4 maps `Stop` to "authoritative turn end". On manual-mode denial the turn silently aborts: no `Stop`, no failure event, no visible rejection text in the pane tail. A tracker that treats `Stop` as the only turn-terminal signal will hang on denials. This vindicates design 1.2's "keep the TUI `⎿ User rejected` handling" and extends it: the TUI detector must own denial-terminal state entirely.
2. **Modal option layout is tool-dependent** (3 vs 4 options; deny key `3` vs `4`); any automated modal driver must read the rendered options, not assume positions. Recorded for the driver notes.
3. **No-bypass launches default to `auto` mode** on 2.1.303: `PermissionRequest` does not fire for auto-allowed tools, and the auto-mode classifier is billing-incompatible with the deepseek gateway (provider notice on screen). A launch that wants permission-modal evidence must pin a permission mode explicitly.
4. `UserPromptSubmit.permission_mode` reads `default` on this lane (vs `bypassPermissions` on the skip-permissions lane) — useful posture signal, unlisted in design section 1.

## Gate Verdicts Informed

| Gate | Verdict | Evidence |
| --- | --- | --- |
| G2 (S3 scope) | **PASS** | `PermissionRequest` ×3, `PostToolUse` ×2, `Stop` ×1 produced; silent families named (`StopFailure`, `PreCompact`, `PostCompact`, `PostToolUseFailure` not exercised) |
| G3 (pairing) | **PASS** | 441 samples + 9-event stream + 2 labels + modal notes; collector monotonic/UTC pair present |

## Cleanup

`/tmp/houmao-hook-allow.txt` left in place as arm evidence (6 bytes, "hello"); `/tmp/houmao-hook-deny.txt` correctly absent. tmux session killed by teardown; no stray collector.
