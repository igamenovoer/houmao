# Evidence: S3 permission lane — ask-mode approve and deny (kimi 2.2.0)

Date: 2026-10-20. Iteration: [iteration 1](../iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md). Arm: S3. Key questions: [KQ-2](../key-questions/KQ-2-event-availability-payloads.md), [KQ-4](../key-questions/KQ-4-blocked-state-permission.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/kimi-hook-capture/s3/run-20261020T133622Z/` (tmux `kimihook-s3-3898584`, pane `%226`) |
| Launch | kimi 2.2.0, **no `--auto`**; scratch config forced `default_permission_mode = "manual"` before the hook merge |
| Collector | gen 1, port 38113, 16 accepted events |
| Recording | 117 samples; labels `s3-permission-allow`, `s3-permission-deny`; modal snapshots in `notes/s3-allow-modal.txt`, `notes/s3-deny-modal.txt` |
| Session | `session_e5946585-0949-4cf4-8ecb-cef0c6d5565c`; `SessionStart` 0.254 s after the allow prompt |

## Permission Panel (runtime-discovered)

Header: `Write this file?` (Write tool), body shows the file path and `1 hello`, footer `↑/↓ select · 1/2/3/4 choose · ↵ confirm · ctrl+e preview`.

Options, exactly as painted:

| Index | Label | Key used |
| --- | --- | --- |
| 1 | `Approve once` | `1` (allow) |
| 2 | `Approve for this session` | not used |
| 3 | `Reject` | not used |
| 4 | `Reject with feedback` | not used |
| — | — | `Escape` (deny; rejects directly, no feedback state) |

The driver parsed the numbered options from the pane and selected the first label starting with `Approve`; the deny path used `Escape` and recorded option 3 (`Reject`) as the corresponding label.

## Ordered Event Sequences

Allow file (`/tmp/houmao-kimi-hook-allow.txt`):

| Seq | Event | received_at_utc | Key fields |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:36:25.651 | `source=startup` |
| 2 | `UserPromptSubmit` | 13:36:25.753 | allow prompt |
| 3 | `TurnStarted` | 13:36:25.834 | `turn_id=0` |
| 4 | `PreToolUse` | 13:36:32.130 | `tool_name=Write`, `tool_call_id=tool_8IHFsvSl8v9sJ7a260y2kiOV` |
| 5 | `PermissionRequest` | 13:36:32.192 | same `tool_call_id`, `turn_id=0`, `agent_id=main`, `id=approval_389229a4…`, `action="Writing /tmp/…-allow.txt"`, `display={kind:file_io, operation:write, path, content}` |
| 6 | `PostToolUse` | 13:36:32.611 | same `tool_call_id`, `tool_output="Wrote 6 bytes to …"` |
| 7 | `PermissionResult` | 13:36:32.617 | `decision=approved`, same `tool_call_id`, `turn_id=0`, same approval `id` |
| 8 | `Stop` | 13:36:35.840 | turn end |

Deny file (`/tmp/houmao-kimi-hook-deny.txt`):

| Seq | Event | received_at_utc | Key fields |
| --- | --- | --- | --- |
| 9 | `UserPromptSubmit` | 13:36:36.264 | deny prompt |
| 10 | `TurnStarted` | 13:36:36.315 | `turn_id=1` |
| 11 | `PreToolUse` | 13:36:42.588 | `tool_call_id=tool_3pQqrH1B2oOahJClPSNG1w1U` |
| 12 | `PermissionRequest` | 13:36:42.637 | same `tool_call_id`, `turn_id=1`, `id=approval_eff681e2…` |
| 13 | `PermissionResult` | 13:36:42.875 | `decision=rejected`, same `tool_call_id`, `turn_id=1` |
| 14 | `PostToolUseFailure` | 13:36:42.891 | same `tool_call_id`, `error={code:"internal", message:"Tool \"Write\" was not run because the user rejected the approval request.", retryable:false}` |
| 15 | `Stop` | 13:36:47.586 | the turn continues and settles normally |
| 16 | `SessionEnd` | 13:36:48.242 | `reason=exit` |

## Timings and Pairing

| Measure | Allow | Deny |
| --- | --- | --- |
| Prompt → `PreToolUse` | ~6.7 s (model planning) | ~6.3 s |
| `PermissionRequest` → driver key | 0.371 s (`1` at 13:36:32.563) | 0.096 s (`Escape` at 13:36:42.733) |
| `PermissionRequest` → `PermissionResult` | 0.425 s (includes tool execution) | 0.238 s |
| `PermissionResult` → `PostToolUse`/`Failure` | `PostToolUse` **before** result (6 ms) | failure 16 ms after result |
| `tool_call_id` pairing | PreToolUse = Request = PostToolUse = Result | PreToolUse = Request = Result = Failure |
| `turn_id` | 0 on Request/Result; absent on tool events | 1 on Request/Result |
| Approval `id` | shared Request/Result | shared Request/Result |

The allow-path result fires **after** the tool has executed (`PostToolUse` precedes `PermissionResult`); the deny-path result fires immediately after the decision and is followed by `PostToolUseFailure`. This is the settle signature for the reducer.

## Verdict

**PASS.** Both decisions captured with `decision` values `approved` and `rejected`, call-level pairing by `tool_call_id` and approval `id`, and distinct settle signatures. The deny path does not emit `Interrupt`; the turn continues to `Stop`. Under `--auto` no permission event fires (S0/S1/S4-S9 controls).

## Harness Corrections (2026-10-20)

- Scenario opening now lets the allow prompt create the session, then requires `SessionStart` within 15 s of that prompt. The approval key remains runtime-discovered; no hardcoded key was needed.
- No other S3-specific correction.

## Cleanup

`kimihook-s3-3898584` exited via `/exit`; collector stopped. Modal snapshots and run root retained under `tmp/kimi-hook-capture/s3/`.
