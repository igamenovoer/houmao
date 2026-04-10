## 1. Codex Live-Edge Activity Detection

- [x] 1.1 Update Codex single-snapshot activity detection to derive status-row and tool-cell evidence from the live latest-turn region instead of arbitrary full-scrollback rows.
- [x] 1.2 Preserve and verify Codex transcript-growth active detection for spinnerless response streaming after the live-edge scoping change.
- [x] 1.3 Add detector-focused tests covering stale historical `• Working (... esc to interrupt)` rows above a prompt-ready surface and confirm they no longer produce current active evidence.

## 2. Tracker Stale-Active Recovery

- [x] 2.1 Add tracker configuration and state plumbing for a stale-active recovery window with a default of 5 seconds.
- [x] 2.2 Implement stale-active recovery through the existing ReactiveX scheduler/pipeline so stable submit-ready posture can clear a stuck `turn.phase=active` without manual timer bookkeeping.
- [x] 2.3 Ensure stale-active recovery publishes `turn.phase=ready` without manufacturing `last_turn.result=success`, and expose explicit notes or transition evidence when recovery fires.

## 3. End-to-End Validation

- [x] 3.1 Add shared-tracking or server-tracking tests that cover a stuck active Codex session recovering to ready after 5 seconds of stable submit-ready posture.
- [x] 3.2 Add regression coverage showing that ongoing latest-turn transcript growth blocks stale-active recovery even when the visible running row disappears.
- [x] 3.3 Validate gateway-facing prompt readiness for tmux-backed Codex sessions so mail-notifier polling is no longer suppressed by stale active state once the live surface is truly ready.
