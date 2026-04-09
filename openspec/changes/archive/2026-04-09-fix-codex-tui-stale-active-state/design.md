## Context

The current Codex tracked-TUI pipeline combines two different kinds of evidence from the same tmux capture:

- full-pane scrollback used for parser-oriented dialog interpretation and historical context, and
- detector-oriented live activity signals used to decide whether the current turn is still active.

In the observed failure, those concerns were not separated tightly enough. The Codex activity detector matched a historical `• Working (... esc to interrupt)` row far above the visible prompt, which kept `active_evidence=true` even while the parser and visible surface both indicated an idle freeform prompt. Because gateway prompt-readiness requires `turn.phase=ready` and `surface.ready_posture=yes`, the gateway mail notifier remained in `busy_skip`.

The fix needs to preserve legitimate active detection for spinnerless Codex output growth, avoid teaching the gateway to special-case stale tracker state, and reuse the existing `reactivex`-driven scheduler model already used by success settling and lifecycle reduction.

## Goals / Non-Goals

**Goals:**
- Stop stale historical Codex status rows from holding the tracked turn in `active`.
- Preserve legitimate active detection when Codex is still streaming text without a visible spinner.
- Add a bounded tracker-owned recovery path that clears a stuck active phase after 5 seconds of stable submit-ready posture.
- Implement the recovery path through the existing ReactiveX scheduler model rather than introducing ad hoc manual timers.
- Preserve observability by emitting explicit notes when stale-active recovery is what clears the active phase.

**Non-Goals:**
- Do not change gateway notifier gating rules or make the gateway override incorrect tracked state locally.
- Do not redefine `idle prompt` to mean successful completion.
- Do not manufacture `last_turn.result=success` when the tracker is merely recovering from stale active evidence.
- Do not change full-scrollback capture requirements for parser-side diagnostics, dialog projection, or history-oriented inspection.
- Do not broaden this change to headless Codex control paths or non-Codex tracked-TUI profiles unless later evidence requires it.

## Decisions

### Decision: Separate parser/history capture from live activity inference

The system will keep full tmux scrollback capture as the authoritative raw input for parser-side interpretation, snapshot history, and debugging. However, Codex single-snapshot activity inference will no longer scan arbitrary historical rows from that full scrollback when deciding whether the current turn is active.

Instead, live status-row and in-flight tool evidence will be derived from a bounded live-edge region tied to the current prompt / latest-turn surface, so historical rows above that region cannot continue to assert current activity.

Why this approach:
- The parser and history features legitimately benefit from full scrollback.
- The demonstrated bug is specifically caused by treating historical transcript rows as current activity.
- Limiting live activity inference is a narrower and safer correction than redefining public readiness semantics.

Alternatives considered:
- Treat any visible prompt as proof that the turn is ready. Rejected because Codex can continue streaming text or remain in an interruptible handoff state while the prompt is visible.
- Change tmux capture to visible-screen-only. Rejected because parser diagnostics and history-oriented behavior still need full scrollback.

### Decision: Keep transcript growth as the spinnerless active signal

The temporal transcript-growth mechanism remains the authoritative fallback for Codex turns that are still progressing without a visible running row. The fix will not replace that mechanism with prompt-only heuristics.

Why this approach:
- It preserves the current design intent that Codex may still be active while answer text continues to grow.
- It avoids regressing real active-turn detection in cases where status rows disappear before the answer is complete.

Alternatives considered:
- Require a visible running row for all active states. Rejected because that would regress known spinnerless streaming cases.

### Decision: Add a stale-active recovery path in the tracker layer

The shared live tracker will add a recovery path that clears `turn.phase=active` after the surface remains submit-ready for a configured window with no live activity evidence, no blocking overlay, and no transcript growth.

This recovery belongs in the tracker layer, not in the gateway notifier, because the tracked public state itself is the incorrect authority during the failure.

Why this approach:
- It fixes the authoritative state instead of adding a consumer-specific bypass.
- It benefits every consumer of tracked TUI readiness, not only the gateway mail notifier.

Alternatives considered:
- Add a gateway-only timeout override. Rejected because the tracker would remain wrong and other consumers would still observe the stale active state.

### Decision: Use ReactiveX timing instead of manual timers

The stale-active recovery will be modeled as a ReactiveX-driven state transition using the tracker’s existing scheduler and observable pipeline patterns. The implementation should reuse the same timing infrastructure already used for settled success handling and lifecycle reduction, rather than introducing a separate imperative timeout bookkeeping path.

Why this approach:
- It keeps time-based tracker behavior under one scheduler model.
- It is easier to test deterministically with the existing historical scheduler and reducer harnesses.
- It satisfies the requirement to avoid a manually managed timer path.

Alternatives considered:
- Maintain an imperative `monotonic_ts` deadline in tracker state and check it every cycle. Rejected because it adds parallel timing logic and duplicates existing scheduler responsibilities.

### Decision: Recovery clears the active phase without manufacturing success

When stale-active recovery fires, the tracker will publish a `ready` turn posture but preserve `last_turn.result` unless the normal success-settlement rules already established a success outcome. Recovery is a correctness safeguard for stuck active state, not evidence that the completed turn succeeded.

Why this approach:
- The observed bug proves stale activity evidence, not successful completion semantics.
- Clearing `active` is enough to restore prompt-readiness for gateway work.
- Manufacturing `success` would blur recovery behavior with true completion evidence.

Alternatives considered:
- Force `last_turn.result=success` when recovery fires. Rejected because it overstates what the evidence proves.

### Decision: Default stale-active recovery window is 5 seconds

The repository will default the stale-active recovery window to 5 seconds. This is deliberately longer than the existing success settle window so the normal success path remains primary, while still bounding notifier stalls to a small, predictable interval.

Why this approach:
- 5 seconds is long enough to avoid racing with brief prompt repaints or short-lived surface churn.
- 5 seconds is short enough to unblock gateway notifier behavior promptly in the demonstrated failure mode.

Alternatives considered:
- Reuse the 1-second settle window. Rejected because recovery is a safety net, not the primary completion signal.
- Use a much longer timeout such as 30 seconds. Rejected because it would leave mailbox notification stalls visible for too long.

## Risks / Trade-offs

- [Live-tail window too narrow] → Legitimate active status evidence near the prompt could be missed. Mitigation: derive the window from existing prompt/latest-turn helpers rather than inventing a separate arbitrary crop.
- [Recovery fires while Codex is still truly active] → The tracker could publish `ready` too early. Mitigation: require no live activity evidence, no transcript growth, stable submit-ready posture, and a full 5-second window before recovery fires.
- [Two timing paths become inconsistent] → Success settling and stale-active recovery could interact poorly. Mitigation: run both through the same ReactiveX scheduler model and make recovery phase-only, not result-producing.
- [Version drift changes Codex prompt behavior again] → The live-edge heuristics may need further tuning. Mitigation: keep explicit tracker notes and transition evidence for recovered stale-active cases so drift is observable.

## Migration Plan

No user-facing migration is required. The change should ship behind the normal tracker configuration path with a default stale-active recovery window of 5 seconds.

Rollout steps:
1. Update Codex live activity inference to ignore stale historical status rows outside the live edge.
2. Add the tracker-level ReactiveX stale-active recovery path and expose its default configuration.
3. Extend tracked-TUI tests to cover stale scrollback rows, visible prompt-ready posture, ongoing transcript growth, and recovery timing.
4. Validate gateway notifier behavior against tmux-backed Codex sessions to confirm unread mail is no longer suppressed by stale active state.

Rollback strategy:
- Disable or remove the stale-active recovery path while retaining the live-edge activity fix if recovery proves too aggressive.
- If the live-edge scoping regresses active detection, fall back to the previous detector behavior while retaining the captured evidence and tests from this change for a narrower follow-up.

## Open Questions

None for proposal scope. The desired behavior is well constrained by the observed failure: stale historical activity must stop blocking readiness, and the 5-second recovery path is the explicit safety net.
