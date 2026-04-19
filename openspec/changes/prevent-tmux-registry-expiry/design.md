## Context

The current shared-registry contract uses lease freshness as the discovery signal. Local registry-backed commands such as `houmao-mgr agents list` read only fresh records, and tmux-backed records currently inherit the default 24-hour lease TTL. That means an otherwise healthy tmux-backed managed agent disappears from local discovery once its registry lease ages out unless some later operation happens to refresh the record.

This is not caused by cleanup removing the record too early. Cleanup already treats tmux-backed records specially by probing local tmux liveness and removing lease-fresh records only when the owning session is gone. The mismatch is that ordinary registry storage and local managed-agent list/selector discovery use a short lease for tmux-backed sessions even though tmux itself is the long-lived authority.

The codebase does not currently maintain a background heartbeat that periodically republishes registry records for idle local tmux-backed sessions. Because of that, simply keeping the existing 24-hour TTL is incompatible with long-lived interactive sessions.

Passive server discovery is an existing exception to the ordinary lookup path. It builds a probe-backed index and already requires both lease freshness and a live local tmux session during each scan. This change preserves that behavior.

## Goals / Non-Goals

**Goals:**
- Keep tmux-backed managed agents discoverable through ordinary local registry-backed lookup for effectively all supported operator lifetimes while their registry records remain present.
- Minimize the behavioral surface area of the change by preserving the current registry-first lookup flow.
- Avoid introducing a resident heartbeat process or periodic refresh loop for ordinary local tmux-backed sessions.
- Preserve explicit cleanup and teardown ownership for removing stale tmux-backed registry state.

**Non-Goals:**
- Adding eager tmux liveness probes to ordinary discovery or list operations.
- Redesigning the full shared-registry liveness model for non-tmux backends.
- Introducing new server APIs or a background registry-renewal daemon.
- Making stale-record cleanup immediate or automatic without an explicit cleanup/teardown path.

## Decisions

### Decision: Publish tmux-backed records with a dedicated long finite sentinel lease

Tmux-backed live-agent records should use a dedicated long finite sentinel TTL instead of the ordinary 24-hour TTL or the existing 30-day joined-session sentinel. This keeps existing discovery code working without modification because lookup still relies on the lease-fresh contract, but tmux-backed records no longer cross the freshness boundary during supported long-running operator workflows.

The sentinel is intentionally finite rather than a max timestamp. A finite operational sentinel such as 100 years avoids changing cleanup timestamp arithmetic while remaining effectively non-expiring for supported lifetimes.

Alternative considered:
- Keep the 24-hour TTL and add periodic lease renewal.
- Rejected because ordinary idle tmux-backed sessions do not have a resident Houmao-owned process that can reliably renew the lease.
- Reuse `JOINED_REGISTRY_SENTINEL_LEASE_TTL`.
- Rejected because the current joined-session sentinel is 30 days, which would recreate the same disappearance bug for longer-lived tmux sessions.
- Store a max-like absolute timestamp.
- Rejected because cleanup currently performs `lease_expires_at + grace_period` arithmetic; a max timestamp would require extra overflow handling that is unnecessary for this change.

### Decision: Keep ordinary local registry discovery lease-based rather than adding tmux probes

Lookup helpers such as `resolve_live_agent_record_by_agent_id()`, `resolve_live_agent_records_by_name()`, and local managed-agent list/selector flows should remain simple lease-based consumers. The contract change should happen at publication time, not by widening ordinary local lookup paths to inspect local tmux state.

Passive server discovery remains a probe-backed index. It may continue to check live tmux session names during scans and should include sentinel-fresh tmux-backed records only when the owning tmux session is live.

Alternative considered:
- Make ordinary discovery fall back to tmux liveness when a record is expired.
- Rejected because it broadens the discovery contract, adds host-local probing cost, and reverses the existing design decision that cleanup owns tmux-backed stale classification.

### Decision: Keep cleanup and teardown as the stale-removal mechanisms for tmux-backed records

Clean stop/teardown should continue clearing the shared-registry record explicitly. For unclean exits, `houmao-mgr admin cleanup registry` should remain the mechanism that removes tmux-backed records whose sessions no longer exist locally.

Alternative considered:
- Add automatic background cleanup or opportunistic pruning during list/lookup.
- Rejected because it couples ordinary discovery to mutation and increases surprise for operators.

### Decision: Scope the change to current tmux-backed publication paths only

The sentinel lease change should apply to current tmux-backed live sessions, including joined tmux sessions. The implementation should use one tmux-specific sentinel constant for the tmux-backed publication path.

Alternative considered:
- Make every live-agent record effectively non-expiring.
- Rejected because the current registry schema only represents tmux terminal records, and adding a non-tmux record contract would require separate schema and cleanup design.

## Risks / Trade-offs

- [Dead tmux-backed records may linger longer after unclean exit] -> Keep explicit teardown removal, preserve admin cleanup tmux probing, preserve passive discovery's live-tmux filter, and add tests covering stale dead-session cleanup.
- [A long finite lease may be mistaken for mathematical infinity] -> Encode the rule as an operational sentinel for supported lifetimes rather than an absolute non-expiring timestamp.
- [Future contributors may accidentally reuse the sentinel for non-tmux records] -> Use a dedicated tmux-specific lease constant and cover the selection logic with targeted tests.
- [Operators may still need to run cleanup after crashes] -> Accept this as the intentional trade-off for removing the 24-hour disappearance failure without adding a heartbeat service.

## Migration Plan

1. Update the `agent-discovery-registry` spec to define tmux-backed records as using a dedicated long finite sentinel lease relative to the ordinary live-agent lease.
2. Change runtime registry record construction to publish all tmux-backed records, including joined sessions, with that tmux-specific sentinel TTL.
3. Add or update tests proving tmux-backed records stay discoverable after the old 24-hour and 30-day boundaries, passive discovery still requires live tmux presence, and cleanup still removes records when tmux is gone.
4. Verify local list/resolve commands continue to work unchanged against the new publication semantics without adding eager tmux probes.

Rollback is straightforward: restore the prior tmux-backed TTL selection and the prior spec text. No data migration is required because persisted records are transient registry state.

## Open Questions

None.
