## Context

Issue `#40` exposes a gap between Houmao's persisted lifecycle model and the actual health of a local tmux-backed managed-agent session.

Today, shared lifecycle is intentionally simple:

- `active`
- `stopped`
- `relaunching`
- `retired`

But active local control currently assumes that an `active` record also has a fully healthy tmux authority. In the failure shape from the issue:

- the registry still says `active`
- the tmux session still exists
- window `0` and pane `0` are gone
- only an auxiliary gateway window remains

Current code then gets trapped:

```text
active record
  -> local controller resume
  -> eager tmux primary-window preparation
  -> failure because session:0 is missing
  -> stop/relaunch never reach their real recovery logic
```

Cleanup has a second mismatch: it treats "tmux session exists" as equivalent to "managed agent is still live", even when the contractual primary surface is already gone.

The design therefore needs to distinguish persisted lifecycle from host-local tmux authority health without turning the shared registry into a stale cache of tmux topology.

## Goals / Non-Goals

**Goals:**
- Make degraded active tmux-backed managed agents recoverable through supported lifecycle commands.
- Keep the shared lifecycle-state model stable while adding a derived local tmux-authority health model.
- Allow `agents stop` to retire degraded or stale active local authority without manual tmux cleanup.
- Allow `agents relaunch` to rebuild a missing primary tmux surface when enough local authority still exists.
- Allow `agents cleanup session --purge-registry` to retire obviously broken local active authority when explicit cleanup intent is given.
- Preserve stopped-session revival and reused-home restart as separate, explicit workflows.

**Non-Goals:**
- Add new persisted lifecycle states to the shared registry schema.
- Reopen `--reuse-home` as a live-owner takeover shortcut.
- Automatically "heal" every active session during ordinary inspection or discovery.
- Generalize this change into server-owned remote recovery semantics beyond the local tmux-backed runtime path.
- Improve operator-facing redirect messaging from `project easy instance launch --reuse-home --force ...` when the resolved target is a degraded or stale active local managed agent. The supported recovery path remains `agents stop` followed by `agents relaunch` or a fresh `agents launch`; teaching the launch CLI to detect this state and emit a contextual redirect is left to a follow-up change.

## Decisions

### Decision: Use a two-layer state model

The design keeps persisted lifecycle state unchanged and adds a separate derived local tmux-authority health classification for tmux-backed local sessions.

Conceptually, operators care about four combined states:

```text
1. active + healthy
2. active + degraded_missing_primary
3. active + stale_missing_session
4. stopped
```

But only the lifecycle half is persisted. The local health half is derived on demand from tmux inspection and never written into the shared registry.

This keeps the registry focused on logical lifecycle continuity instead of trying to persist fast-changing tmux topology facts.

Alternatives considered:
- Add new shared lifecycle states such as `degraded` or `stale_active`: rejected because these are host-local tmux facts that can change out-of-band and would make the registry stale and harder to reason about.
- Keep a single binary live/dead model: rejected because it is the root cause of the current recovery dead-end.

### Decision: Add one shared tmux-authority probe for local managed sessions

The runtime will use a single shared probe near the tmux integration layer to classify the current local authority for a persisted tmux-backed managed session.

At minimum, the probe must answer:

- does the tmux session still exist?
- does the contractual primary window `0` exist?
- does the contractual primary pane `0` exist?

That produces three local health classes:

- `healthy`: session exists and the contractual primary surface exists
- `degraded_missing_primary`: session exists but the contractual primary surface is gone
- `stale_missing_session`: the persisted active record points at a tmux session that no longer exists

The gateway auxiliary window is treated as secondary evidence only. Its presence does not make the primary authority healthy.

Alternatives considered:
- Infer health from registry metadata only: rejected because the registry deliberately does not persist enough tmux topology detail.
- Put separate ad hoc probes in stop, relaunch, and cleanup: rejected because those paths would drift and classify the same broken session differently.

### Decision: Active local command routing becomes probe-first, not eager-primary-window-first

Local active target resolution must stop assuming that every active record can be resumed into a fully healthy controller immediately.

The new routing model is:

```text
resolve active record
  -> run local tmux-authority probe
     -> healthy: use normal active controller resume
     -> degraded_missing_primary: enter degraded recovery path
     -> stale_missing_session: enter stale-active recovery path
```

This means controller construction for healthy paths can stay strict, while degraded and stale recovery paths become explicit instead of accidentally surfacing as generic resume failures.

Alternatives considered:
- Make ordinary controller resume silently recreate window `0`: rejected because it hides degraded state, mutates the session during plain discovery, and makes `stop` less predictable.
- Keep CLI-level special cases without a shared routing model: rejected because stop, relaunch, and cleanup would continue to disagree on what "broken but recoverable" means.

### Decision: `agents stop` retires degraded or stale active authority into lifecycle continuity

`agents stop` becomes the primary safe recovery path for broken local active sessions.

Behavior by local health:

- `active + healthy`
  - use current stop behavior
- `active + degraded_missing_primary`
  - best-effort detach gateway metadata
  - kill the surviving tmux session by name
  - publish a stopped lifecycle record when relaunch authority is still available
- `active + stale_missing_session`
  - skip tmux teardown because no tmux session remains
  - transition the active record out of live state using preserved manifest/session authority
  - publish a stopped lifecycle record when relaunch authority remains, otherwise retire or clear the record explicitly

The key point is that a broken local active record must not remain stuck in `active` solely because normal healthy resume cannot be reconstructed.

Alternatives considered:
- Require operators to use cleanup instead of stop for stale active records: rejected because stop is the most natural supported recovery surface.
- Delete registry state immediately for every stale active stop: rejected because relaunchable continuity should be preserved when supported.

### Decision: `agents relaunch` recovers degraded active sessions directly but keeps stopped revival distinct

`agents relaunch` will support two recovery branches in addition to the existing healthy active relaunch:

- `active + degraded_missing_primary`
  - rebuild the contractual primary surface inside the existing tmux session
  - relaunch the provider on that rebuilt surface
  - keep the logical managed-agent identity and active lifecycle continuity
- `active + stale_missing_session`
  - treat the active record as stale local live authority
  - validate preserved manifest/home/session continuity
  - run the stopped-session revival path to create a fresh live tmux container
  - republish active lifecycle metadata on success

This preserves the conceptual separation between ordinary healthy active relaunch and stopped revival, while still giving operators one supported `agents relaunch` surface for broken active records.

Alternatives considered:
- Continue to require operators to convert broken active sessions into explicit stopped state before relaunch: rejected because the reported issue is specifically that operators cannot reliably do that today.
- Always allocate a brand-new launch through `agents launch`: rejected because recovery should preserve managed-agent continuity and runtime-owned artifacts.

### Decision: Explicit cleanup can retire broken active local authority, but only with purge intent

`agents cleanup session` stays primarily a stopped-session artifact cleanup command.

However, when the operator explicitly passes `--purge-registry`, cleanup may treat `active + degraded_missing_primary` and `active + stale_missing_session` as recoverable broken-local-authority cases rather than as untouchable active sessions.

That explicit purge path may:

- remove a leftover tmux session remnant when one still exists but no primary surface remains,
- remove the session root,
- retire or delete the registry record according to the selected cleanup mode.

Without `--purge-registry`, cleanup remains conservative and should still prefer ordinary stop for live-looking sessions.

Alternatives considered:
- Let ordinary cleanup delete any active broken session automatically: rejected because that is too destructive without explicit operator acknowledgment.
- Keep cleanup blocked whenever lifecycle says `active`: rejected because it preserves the current dead-end.

### Decision: Reused-home semantics remain unchanged

The recently defined stopped-only `--reuse-home` continuity restart contract remains intact.

This change fixes degraded active recovery through:

- `agents stop`
- `agents relaunch`
- `agents cleanup session --purge-registry`

It does not turn `--reuse-home --force ...` back into a live-owner replacement tool.

Alternatives considered:
- Reuse this issue to reopen live-owner `--reuse-home` replacement: rejected because it conflicts with the newer stopped-only continuity model and would blur two different safety contracts.

### Decision: Auxiliary gateway window is rebuilt with the primary surface during degraded relaunch

When `agents relaunch` recovers `active + degraded_missing_primary`, any surviving auxiliary gateway window inside the same tmux session SHALL be killed before the contractual primary surface is rebuilt. The gateway is then reprovisioned through the existing post-startup gateway launch path that already runs in normal launch flows.

Rebuilding gateway state from scratch is preferred over rewiring the surviving gateway window because:

- the surviving gateway window represents partial state from a session that already lost its primary surface
- gateway provisioning is an idempotent step in normal launch and reuses the same tmux session container
- preserving the gateway window would force the rebuilt primary controller to rediscover and adopt gateway state mid-recovery, which is a separate failure surface

For `agents stop` on `degraded_missing_primary`, killing the surviving tmux session by name removes the gateway window as a side effect; no separate gateway-window teardown is required beyond the best-effort gateway-state detach already called out in the stop decision.

Alternatives considered:
- Preserve the surviving gateway window across primary rebuild and rewire it to the new controller: rejected because it leaves gateway-side liveness state out of step with the freshly rebuilt primary controller and adds a recovery-only rewiring code path.
- Tear down only the gateway window in `degraded_missing_primary` stop while leaving the surviving tmux container: rejected because the stop contract still needs to publish a clean stopped lifecycle record, which is simpler when the whole tmux session is removed.

### Decision: Stale active without preserved manifest authority retires the lifecycle record

When the selected lifecycle record is `active + stale_missing_session` and preserved manifest/relaunch authority is also unreadable or absent, recovery cannot publish a stopped lifecycle continuity record. The change still has to define what each supported recovery surface does so the operator does not bounce between a permanently un-actionable active record and a generic unusable-target error.

Behavior by command:

- `agents stop`: clear the stale active live claim and retire the registry record idempotently. The successful response identifies that retirement happened without preserved relaunch authority.
- `agents relaunch`: fail explicitly with a clear CLI error pointing to `agents launch` as the supported path forward, since neither active nor stopped revival is available.
- `agents cleanup session --purge-registry`: continue to retire or purge the record as already specified.

This keeps `agents stop` as the primary recovery surface even for the most degraded shape and prevents the registry from accumulating active records that no supported command can clear.

Alternatives considered:
- Treat missing manifest authority as a hard error in stop: rejected because it preserves the original dead-end the issue describes.
- Try to reconstruct manifest authority from registry-only metadata: rejected because the registry deliberately omits enough state to rebuild a runtime authority.
- Allow relaunch to fall through to a fresh `agents launch` automatically: rejected because that loses managed-agent identity continuity silently and conflicts with the principle that fresh launch is an explicit operator action.

## Risks / Trade-offs

- [Probe misclassifies an unusual tmux topology] -> Keep the health model narrow and contract-based: only the managed primary surface determines health, not incidental gateway windows or focus.
- [Stop and cleanup recovery overlap in confusing ways] -> Keep `stop` as the preferred recovery path and require explicit `--purge-registry` before cleanup can retire broken active authority.
- [Stale active relaunch becomes too magical] -> Route it through the existing stopped-session revival machinery rather than inventing an unrelated fresh-launch path.
- [Registry continuity could be lost for badly corrupted sessions] -> Preserve stopped continuity whenever manifest/session authority is still readable; only retire or purge when continuity cannot be supported or the operator explicitly asks for purge cleanup.
- [Surviving gateway window leaks state across primary rebuild] -> Always kill the surviving gateway window before rebuilding the contractual primary surface during degraded relaunch, then reprovision the gateway through normal post-startup gateway launch.
- [Operator hits the same dead-end through the launch CLI] -> The `project easy instance launch --reuse-home --force ...` UX redirect is explicitly deferred; until that follow-up lands, document `agents stop` followed by `agents relaunch` (or fresh `agents launch`) as the supported recovery path for degraded and stale active local managed agents.

## Migration Plan

1. Add the shared local tmux-authority probe and wire it into local active target recovery routing.
2. Update runtime stop and relaunch handling to support degraded and stale active local tmux authority without introducing new persisted lifecycle states.
3. Update CLI registry-backed command resolution so `agents stop` and `agents relaunch` use the new recovery routing instead of collapsing into generic unusable-target errors.
4. Update cleanup planning so `agents cleanup session --purge-registry` can retire broken local active authority when the tmux-authority probe shows no usable primary surface.
5. Add regression coverage for degraded-primary recovery, stale-missing-session retirement, and explicit cleanup of broken active records.

Rollback is localized: remove the probe-driven degraded recovery branches and return to the current strict behavior where only healthy active authority can be resumed and cleaned.

## Open Questions

None for proposal scope. The main product decision is already settled: the broken-active recovery path should be solved through stop/relaunch/cleanup, not by changing reused-home back into a live-owner replacement surface.
