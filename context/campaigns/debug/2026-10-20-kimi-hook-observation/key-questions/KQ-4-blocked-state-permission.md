# KQ-4: Blocked-State and Permission Semantics

Status: answered (2026-10-20); named unresolved items remain where marked. Owner: iteration 1. Campaign: [debug-intent.md](../debug-intent.md).

## Question

Can houmao's `blocked`/`interrupted` posture states be derived from kimi hook events, and what exactly happens on the permission allow and deny paths at 2.2.0?

Source baseline: permission gating at `extern/orphan/kimi-code/packages/agent-core-v2/src/agent/toolApproval/toolApprovalService.ts:101-145` (@ `67325c1`); permission payloads at `agent/agentExternalHooksService.ts:178-190`; interrupt at `:389-397`; `StopFailure` at `:399-410`.

## Propositions

### P4.1 PermissionRequest/Result pair by tool_call_id

Unlike Codex (whose `PermissionRequest` lacks `tool_use_id`), kimi's `PermissionRequest` and `PermissionResult` both carry `tool_call_id` and `turn_id`, so call-level pairing needs no ordering heuristic. Test: S3; verify the pair shares `tool_call_id` and matches the surrounding `PreToolUse`.

### P4.2 Allow and deny paths have distinct settle signatures

On allow: `PermissionResult(decision="approved")` then `PostToolUse` with the same `tool_call_id`. On deny: `PermissionResult(decision="rejected")`, then record exactly what follows — `PostToolUseFailure`, `Interrupt`, both, or neither — and whether the turn continues. Test: S3 approve-then-deny; the deny settle signature becomes the reducer rule (or the named v1 fallback if no settle event exists).

### P4.3 The blocked window is derivable in ask mode

The interval `PermissionRequest` → `PermissionResult` is the hook-derived `blocked` window, with timing comparable to the TUI modal paint (pane frames). Test: S3 paired recording; measure request-to-modal and result-to-resume latencies. Under `--auto` (houmao's unattended strategy) the window never exists — the control evidence comes from S1's total absence of permission events.

### P4.4 Interrupt semantics are settled

Esc mid-turn emits `Interrupt(turn_id, reason="cancelled")` in place of `Stop` (source: fires on any cancelled turn end, `agentExternalHooksService.ts:394-396`); no `Stop` follows the aborted turn. Test: S5; verify against the pane recording's interrupt frame.

### P4.5 StopFailure availability

`StopFailure(error_type, error_message)` fires when a turn fails on an error. Forcing a real provider error cheaply (for example a bogus `-m` model alias) may fail earlier at config validation instead; if no clean forcing arm exists at zero extra cost, this proposition is named unresolved with the missing evidence stated. Test: one opportunistic arm, budget-capped.

## Answer

(2026-10-20, full capture matrix executed. Evidence: [S3 permission lane](../evidences/2026-10-20-s3-permission-lane.md), [S5 interrupt](../evidences/2026-10-20-s5-interrupt.md), [payload catalog](../evidences/2026-10-20-kimi-hook-payload-catalog.md).)

- **P4.1 — confirmed.** `PermissionRequest` and `PermissionResult` both carry `tool_call_id` and `turn_id`, plus a shared approval `id` (`approval_<uuid>`). In S3 the pair matched the surrounding `PreToolUse`/`PostToolUse` by `tool_call_id`; no ordering heuristic is needed. The allow call paired `tool_8IHFsvSl8v9sJ7a260y2kiOV` across PreToolUse/Request/PostToolUse/Result; the deny call paired `tool_3pQqrH1B2oOahJClPSNG1w1U` across PreToolUse/Request/Result/Failure.
- **P4.2 — confirmed with distinct settle signatures.** Allow: `PermissionResult(decision=approved)` **after** `PostToolUse` (the tool ran first), then `Stop`. Deny: `PermissionResult(decision=rejected)` immediately after the decision, then `PostToolUseFailure(error.code=internal, retryable=false)`, then `Stop`. The deny path emits **no `Interrupt`**; the turn continues and settles normally. The reducer rule is: approved → tool-completion then result; rejected → result then failure, both followed by `Stop`.
- **P4.3 — confirmed.** The blocked window `PermissionRequest` → `PermissionResult` measured 0.425 s on the allow path (includes the 0.371 s to the driver's key and the tool execution) and 0.238 s on the deny path. The pane's `Write this file?` modal with numbered options agreed with the hook window. Under `--auto` no permission window exists: S0/S1/S4-S9 produced zero permission events.
- **P4.4 — confirmed.** Esc mid-turn emitted `Interrupt(turn_id=0, reason=cancelled)`; the `Stop` count stayed 0 before and after. The pane's interrupt frame agrees with the hook settle. No `Stop` follows the aborted turn.
- **P4.5 — unresolved.** `StopFailure(error_type, error_message)` was never forced. The opportunistic arm was not attempted because a bogus model alias would have been an unplanned session/failure mode; the missing evidence is one turn that fails in the provider/agent loop with a hook subscription active.

Permission-lane labels observed live: `Write this file?`; options `1. Approve once`, `2. Approve for this session`, `3. Reject`, `4. Reject with feedback`; footer `↑/↓ select · 1/2/3/4 choose · ↵ confirm · ctrl+e preview`. Approve used `1`; deny used `Escape` (direct reject, no feedback state). These labels are TUI surfaces, not hook payload fields; `PermissionResult` did not echo `selected_label`.

Missing evidence for all five: the S3 (ask-mode approve/deny) and S5 (Esc interrupt) arms under an amended gate, plus one `--auto` session-bearing arm as the permission-absence control.

## Scope

Covers blocked/interrupted posture derivability and permission-path signatures. The merge of these into the public state model is KQ-5. Evidence: `evidences/` links added as produced.
