## Context

Houmao already has two TUI interrupt behaviors that converge on the same operator expectation: local interactive TUI interrupt and gateway-backed TUI interrupt both act as best-effort TUI interruption rather than as process termination. The remaining gap is the direct managed-agent request path in `houmao-server`, where `POST /houmao/agents/{agent_ref}/requests` still uses coarse tracked TUI phase to decide whether interrupt should mutate transport state at all.

That phase gate is too strict for live TUI sessions because Houmao's tracked TUI state is observational and can lag the visible provider affordance. An operator can see a TUI that is still interruptible while the reducer has already returned to `idle`, so a transport-neutral interrupt request becomes an avoidable no-op.

The user direction for this change is narrow: do not broaden into CAO compatibility work. The change only needs to make the remaining direct managed-agent TUI interrupt path honor the same "always send `Escape`" rule as the other TUI interrupt surfaces.

## Goals / Non-Goals

**Goals:**
- Make direct managed-agent interrupt for TUI-backed agents always dispatch a best-effort `Escape` interrupt signal.
- Preserve transport-neutral caller behavior so operators keep using `houmao-mgr agents interrupt` and `POST /houmao/agents/{agent_ref}/requests` rather than reasoning about raw control-input paths.
- Preserve current headless interrupt semantics, including active-execution targeting and no-op behavior when no headless work is active.
- Document the TUI/headless interrupt split clearly in the packaged messaging guidance.

**Non-Goals:**
- Redesign CAO-compatible `/cao/*` routes or compatibility-provider exit behavior.
- Change gateway raw control-input semantics or replace `agents gateway send-keys`.
- Change managed-agent stop/close semantics.
- Introduce provider-confirmed interrupt acknowledgements for TUI sessions.

## Decisions

### 1. TUI interrupt branches on transport, not tracked active phase

Direct managed-agent interrupt will branch first on the resolved managed-agent transport. For TUI-backed agents, the server will attempt to deliver one `Escape` interrupt signal whenever the TUI control path is reachable, even if coarse tracked phase is currently `idle` or `unknown`.

Rationale:
- TUI tracking is advisory and can lag visible provider state.
- `Escape` is the least-destructive interrupt signal for the maintained TUI tools.
- The caller asked for interrupt intent, not for a state-inspection veto.

Alternative considered:
- Keep the current `turn.phase == active` gate and return no-op otherwise.
  Rejected because it makes interrupt reliability depend on delayed observation instead of the live TUI contract.

### 2. TUI interrupt success means "signal dispatched", not "active turn confirmed"

For TUI-backed agents, a successful interrupt response will mean Houmao dispatched the `Escape` interrupt signal to the reachable TUI path. It will not mean the server proved that the provider was actively generating at that exact instant.

Rationale:
- A live TUI can absorb `Escape` into several legitimate postures: interrupting generation, dismissing an overlay, or stabilizing an ambiguous ready surface.
- The operator intent is still satisfied better by dispatching `Escape` than by refusing to act.

Alternative considered:
- Require proof of active generation before interrupt can be considered accepted.
  Rejected because it reintroduces the delayed-tracking failure mode this change is fixing.

### 3. Headless interrupt keeps its current no-op gate

Headless interrupt will continue to target active managed execution only. When no headless turn is active, Houmao will keep returning explicit no-op semantics instead of fabricating interruption.

Rationale:
- Headless interrupt is process/execution control, not TUI steering.
- The headless path already has server-owned active-turn authority that is stronger than observational TUI phase.

Alternative considered:
- Unify TUI and headless semantics by always returning accepted interrupt even for idle headless state.
  Rejected because headless has no equivalent of harmless `Escape` delivery; a false acceptance would hide real admission state.

### 4. User-facing guidance will describe TUI interrupt as best-effort `Escape`

The packaged messaging skill and native CLI contract will describe ordinary TUI interrupt as best-effort `Escape` delivery. Exact raw TUI shaping remains owned by `agents gateway send-keys`; ordinary interrupt should not require callers to drop down to that raw path.

Rationale:
- Operators should not have to know that TUI interrupt happens to be implemented with `Escape`.
- Raw `send-keys` remains the right tool for precise slash-menu, cursor, and partial-input work.

Alternative considered:
- Tell users to use `gateway send-keys "<[Escape]>"` for TUI interrupt.
  Rejected because it leaks transport details into the ordinary interrupt workflow and breaks the transport-neutral contract.

## Risks / Trade-offs

- [Idle `Escape` can dismiss a TUI overlay] → Accept this as the intended best-effort interrupt trade-off and document it as a TUI-specific behavior rather than treating it as an error.
- [Future regressions may reintroduce active-phase gating] → Add contract coverage at the API and CLI/spec level plus focused tests on the direct managed-agent TUI interrupt path.
- [Callers may overread interrupt acceptance as proof of active generation] → Keep the documentation explicit that TUI interrupt means signal dispatch, not provider-confirmed active-turn cancellation.

## Migration Plan

No data migration is required.

Implementation rollout:
1. Remove the direct managed-agent TUI interrupt no-op gate that depends on coarse tracked phase.
2. Route direct TUI interrupt delivery through the same best-effort `Escape` semantic used by the maintained TUI interrupt surfaces.
3. Preserve headless interrupt admission and no-op behavior unchanged.
4. Update messaging/CLI guidance and targeted tests.

Rollback is straightforward: restore the previous direct TUI active-phase gate and the earlier accepted/no-op behavior if the new interrupt contract proves too permissive.

## Open Questions

None.
