# KQ-2: Delivery Semantics

Status: partially resolved (iteration 1, 2026-10-19; P2.5 unreachable). Owner: iteration 1. Campaign: [debug-intent.md](../debug-intent.md).

## Question

What are the real delivery semantics of the v1 hook events: ordering, timing relative to the visible surface, timeout behavior, duplicates, and retry behavior?

## Propositions

### P2.1 Ordering across event types

`UserPromptSubmit`, tool events, and `Stop` for one turn arrive in an order consistent with the design's correlation rules. Queued-input overlap (Submit#2 before Stop#1) is either impossible or measured. Test: S7 capture; record the exact sequence.

### P2.2 PermissionRequest timing

`PermissionRequest` arrives before the permission modal paints, and the lead time is measurable. Test: S3 capture; compare event timestamp against the TUI recording's modal-appearance frame.

### P2.3 High-frequency event cost

`PostToolUse` latency impact is measurable and small enough for the HTTP path, or the event is dropped from v1 per design D6. Test: S1/S5 captures; measure provider-side delay attributable to hook delivery (compare turn wall times with hooks on vs off on matched prompts).

### P2.4 Terminal events under interruption

Esc during a turn either emits `Stop` or does not; whichever it is, it is recorded. Test: S6 capture; this result directly selects the Gap-2 latch carve-out's live arm.

### P2.5 StopFailure reachability

An API failure (relay cut mid-stream) produces `StopFailure` with a usable error class. Test: S6 best-effort arm; if unreachable on this relay, mark unresolved and name the missing control.

## Answer

Iteration 1, 2026-10-19. Verdicts per proposition:

- **P2.1 confirmed.** Per-turn ordering is strict (`UserPromptSubmit` then tool events then `Stop`, `prompt_id`-paired). The queued-overlap case is not impossible but reordered: the queued prompt's `UserPromptSubmit` fires at **type time**, so the S7 sequence is `UPS(essay), UPS(queued), Stop(essay), Stop(queued)` with the two Stops back-to-back at consumption. Evidence: [S7](../evidences/2026-10-19-s7-queue-resume.md).
- **P2.2 confirmed, lead measured within granularity.** In S3 the deny-leg `PermissionRequest` is stamped 13:29:52 and the first visible modal frame is s000030 at 13:29:53; the event strictly precedes paint (lead > 0, bounded < 2 s). The allow-leg event and modal detection fall in the same second (13:29:48). Measurement floor: collector stamps `received_at_utc` at 1 s granularity and pane frames at 0.2 s sampling with 1 s `ts_utc` display; tighter lead needs millisecond stamping (named iteration-2 improvement). Evidence: [S3](../evidences/2026-10-19-s3-permission-lane.md).
- **P2.3 confirmed (no measurable cost).** Matched-prompt comparison: S1 hooks-on turn walls were 2.0 s and 1.0 s (UPS to Stop); the hooks-off control answered in approximately 1.3 to 1.5 s (submit to answer-visible) with 8.184 s settle walls that include the 6 s stability dwell. The delta is sub-second and inside the control heuristic's floor; no `PostToolUse` drop from v1 is warranted on cost grounds. Evidence: [S1](../evidences/2026-10-19-s1-normal-multiturn.md), [s1-control](../evidences/2026-10-19-s1-hooks-off-control.md).
- **P2.4 confirmed (negative).** Esc mid-generation emits nothing: 90 s of total hook silence (no `Stop`, no `StopFailure`, no `PostToolUseFailure`); the pane performs the documented silent abort (footer idles, interrupted prompt restored as a draft). The TUI temporal silent-abort detector remains authoritative; this selects the Gap-2 latch carve-out's live arm. Evidence: [S6](../evidences/2026-10-19-s6-esc-interrupt.md).
- **P2.5 unreachable.** No safe fault lane exists on this host (relay or network cuts are out of bounds). Missing control: a session-scoped API-fault injector (for example a proxy lane that returns 500 for one request). No improvised fault injection was attempted. Evidence: [S6](../evidences/2026-10-19-s6-esc-interrupt.md).

Summary: ordering, permission timing, and hook cost are measured and benign; Esc and denial terminal states are hook-silent by design contract; `StopFailure` remains unverified for want of a safe fault lane.

## Scope

Delivery behavior only. Normalization is KQ-3's input but the field-level catalog is KQ-3; posture reduction is KQ-5. Evidence: `evidences/` links added as produced.
