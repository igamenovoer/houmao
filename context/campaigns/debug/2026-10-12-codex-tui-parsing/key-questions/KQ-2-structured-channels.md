# KQ-2: Can codex structured event channels serve as the state oracle?

Status: partially answered 2026-10-12 (offline-oracle feasibility confirmed; live attach unverified). Iteration owner: iteration 1 (Arm C, feasibility input). Evidence: [session 1](../evidences/2026-10-12-session1-lifecycle-capture.md) + [session 2](../evidences/2026-10-12-session2-operator-surfaces-capture.md) Arm C sections.

## Opening Statement

Codex exposes machine-readable event channels that kimi-code lacked as a practical oracle: the app-server JSON-RPC protocol (houmao already ships a `codex_app_server` launch backend, `src/houmao/agents/realm_controller/backends/`) and `codex exec --json` NDJSON events. If one of these streams carries turn lifecycle and approval events with full fidelity while the TUI runs, it can act as an independent ground-truth oracle for validating text-scraping repairs (Arm A) — and possibly as a superior detection channel where houmao itself launched the session. The kimi campaign's equivalent question (KQ-3) remained unopened; codex gives it a stronger premise because houmao already integrates the app-server lane.

## Critical Propositions

### P2.1 Event coverage

The app-server event stream (or `exec --json`) distinguishes, at minimum: turn started, turn completed (with outcome), approval requested/pending/resolved, user-input requested, interruption, and error/terminal failure — the events that flip the two user-facing booleans.

### P2.2 Coexistence with the TUI

The structured stream is available while the interactive TUI runs (app-server attached to the same session, or a tap on the TUI's own event channel), so labels can be derived for the exact samples a recording captured. If the channels only work in headless mode, their oracle value drops to cross-checking, not per-sample labeling.

### P2.3 Fidelity vs surface truth

Events and TUI surface states agree on admission decisions: an event-derived "busy" never co-occurs with a surface that genuinely accepts prompt submission, and vice versa. Known risk: provider-side queuing (submitting during busy) may be visible in events before the surface reflects it, or vice versa.

## Answer / Resolution

Partially answered by iteration 1's Arm C (post-hoc rollout inspection; full inventory in `evidences/` Arm C sections):

- **P2.1 — confirmed for lifecycle.** The rollout stream under `CODEX_HOME/sessions/` carries `task_started`, `task_complete`, `turn_aborted`, `item_completed`, `custom_tool_call(+output)`, `message`, `token_count` with ISO timestamps and turn ids, written while the TUI runs. Operator denial lands as `turn_aborted`, distinct from `task_complete`.
- **P2.2 — confirmed offline, unverified live.** Rollout files persist post-session and align to labeled spans within ≤0.5 s (`task_complete` at 37.8 s vs `Worked for` dock at 37.91 s). Whether an app-server client can attach to a live TUI session and stream the same events was not tested — that is the live-oracle question for a future iteration.
- **P2.3 — confirmed on the captured matrix.** Event-derived turn boundaries match blind labels at every turn seam in both sessions (7 + 42 lifecycle events).

Open remainder: live app-server attach semantics (P2.2 live half) and approval-request events (approvals were driven by the harness, not mapped to specific rollout events beyond `turn_aborted`).

## Scope

Covers codex app-server JSON-RPC and `codex exec --json` as candidate oracle/replacement channels. Escape-sequence channels (OSC 133 / 9;4) are not this question; they are audited as iteration 1's Arm B, and a KQ opens for them only if the audit finds surviving sequences. Production adoption of any structured channel is out of scope for the campaign; integration follows only after manual review of campaign reports (user directive 2026-10-12), with no OpenSpec artifacts produced by this campaign.
