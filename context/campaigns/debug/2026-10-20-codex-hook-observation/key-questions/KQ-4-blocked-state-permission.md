# KQ-4: Blocked State and Permission Semantics

Status: resolved (iteration 1, 2026-10-20; deny-aborts-turn semantics recorded for the reducer). Owner: iteration 1. Campaign: [debug-intent.md](../debug-intent.md).

## Question

Does `PermissionRequest` give houmao a truthful hooks-only `blocked` state for Codex — "the TUI is asking the user for an action and will not proceed until it is settled" — and what event settles it?

Source baseline: `PermissionRequest` fires in the approval path before Guardian/user review (`codex-rs/core/src/tools/approvals.rs:486-505`), only when a tool actually requests approval; it has **no `tool_use_id`**; outputs can allow/deny, but houmao's observer never answers — the human settles through the TUI. `permission_mode` currently emits only `default` or `bypassPermissions` (`codex-rs/core/src/hook_runtime.rs:1039-1047`).

## Propositions

### P4.1 PermissionRequest precedes the modal and names the pending action

In a session launched without approval bypass, a tool call needing approval emits `PermissionRequest` with `tool_name`/`tool_input` before (or as) the TUI approval modal paints. Test: S3 lane; compare hook timestamp vs pane-recorded modal paint.

### P4.2 Allow path settles with the matching tool event

When the user allows, the next hook events include the paired `PreToolUse` (and later `PostToolUse`) for the same call; the blocked interval is measurable end to end. Test: S3 allow arm; record the settle event and latency.

### P4.3 Deny path settles observably

When the user denies, some hook event or the absence thereof plus a following `Stop`/turn continuation truthfully marks the settle; if no hook event fires on deny, the reducer rule must be named (e.g. settle on next `PostModelRequest` or `Stop`). Test: S3 deny arm; record exactly what fires after denial.

### P4.4 No false blocked in bypass mode

Sessions launched with `--dangerously-bypass-approvals-and-sandbox` (the standard unattended lane) never emit `PermissionRequest`, so the blocked state is unreachable there. Test: verify across S1/S4/S5/S6 streams that no `PermissionRequest` arrives under bypass.

### P4.5 Correlation without tool_use_id is specified

A deterministic rule associates a `PermissionRequest` with its tool call (candidate: next `PreToolUse` with equal `tool_name` in the same `turn_id`, verified against `tool_input` equality). Test: S3 streams; validate the rule against labeled allow/deny outcomes, including two approval requests in one turn if the frozen prompt produces them.

## Answer

Iteration 1, 2026-10-20, codex-cli 0.163.0, S3 lane (`approval_policy = "on-request"`, `sandbox_mode = "read-only"`, hook-trust bypass retained). Evidence: [S3 permission lane](../evidences/2026-10-20-s3-permission-lane.md), [payload catalog](../evidences/2026-10-20-codex-hook-payload-catalog.md).

- **P4.1 confirmed.** `PermissionRequest` arrives before the modal's first captured 5 fps frame (04:31:24.903 vs frame at 04:31:25) and ~390 ms before the user's `y`. The payload names the pending action (`tool_name`, `tool_input.command`, plus a `description` justification not present on `PreToolUse`).
- **P4.2 refuted as proposed, corrected.** `PreToolUse` does NOT follow the approval — it precedes `PermissionRequest` by ~54 ms. On allow, the settle event is `PostToolUse` with the **same `tool_use_id`** as the already-seen `PreToolUse` (measured 457 ms after the request). The blocked interval is therefore `PermissionRequest` → matching-`tool_use_id` `PostToolUse`.
- **P4.3 confirmed with a semantic correction.** On deny (Esc at the 0.163.0 modal, whose only negative option is "No, and tell Codex what to do differently"), the next and only settle event is `Interrupt` (63 ms after the keypress, same `turn_id`, no reason field): **deny aborts the whole turn**, there is no `PostToolUse` and no `Stop`. The reducer rule: blocked settles on `PostToolUse` (allow path) or `Interrupt` (deny path).
- **P4.4 confirmed.** No `PermissionRequest` arrived in any bypass-lane session (S0/S1/S4/S5/S6/S7/F1/T1/T2 all clean), so `blocked` is unreachable in the standard unattended lane — matching the Claude lane's manual-permission-mode caveat.
- **P4.5 specified (candidate refuted, replacement validated).** "Next `PreToolUse` with equal `tool_name`" is wrong (it mispairs across turns). The validated rule: pair a `PermissionRequest` with the **immediately preceding** `PreToolUse` in the same `turn_id` with equal `tool_name` (verify `tool_input.command` equality); the settle on allow is the `PostToolUse` carrying that `PreToolUse`'s `tool_use_id`. Two approval cycles in one session matched one-to-one with zero ambiguity.

Summary: Codex gives a truthful hooks-only `blocked` state via `PermissionRequest`, with the pair-back rule to its `PreToolUse` and settle on `PostToolUse` (allow) or `Interrupt` (deny, which aborts the turn). This is cleaner than the Claude lane (no `tool_use_id` gap matters in practice) but the deny-means-abort semantics must be reflected in the reducer.

## Scope

Covers the permission/blocked surface only. General event catalog is KQ-2; merge rules are KQ-5. Evidence: `evidences/` links added as produced.
