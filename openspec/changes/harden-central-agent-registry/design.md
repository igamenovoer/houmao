## Context

`add-central-agent-registry` introduced the shared per-user live-agent registry so name-based runtime control can recover sessions across runtime roots. Review of the implementation found that the first pass gets the basic publication model right, but still treats several registry problems as hard runtime failures:

- tmux-local discovery falls back to the registry only when the tmux session is missing, not when tmux-published pointers are missing or stale,
- malformed registry records abort lookup instead of behaving like stale entries,
- timestamp parsing accepts naive values that make lease freshness timezone-dependent,
- best-effort registry refresh and cleanup work can incorrectly fail otherwise successful runtime actions, and
- registry filesystem helpers are not resilient to temp-file or per-directory cleanup failures.

This follow-up change is intentionally narrower than the original registry introduction. It hardens the recovery and failure-isolation semantics without changing the registry root, agent-key derivation, mailbox transport shape, or lifecycle publication hooks already chosen in the earlier change.

Because `agent-discovery-registry` is still being introduced through `add-central-agent-registry`, this change should land with or after that registry feature work. The goal here is to pin the corrected follow-up semantics so implementation can proceed without re-litigating the review decisions.

## Goals / Non-Goals

**Goals:**
- Make shared-registry fallback available for missing or stale tmux-local discovery pointers, not only missing tmux sessions.
- Treat malformed registry records as unusable or stale at lookup time so discovery can recover cleanly.
- Require timezone-aware registry timestamps so lease freshness is deterministic across environments.
- Keep registry refresh on the existing runtime-owned publication hooks while isolating registry failures from already-successful prompt, control, mailbox-refresh, and stop actions.
- Harden shared-registry filesystem helpers so failed atomic writes do not leak temp files and cleanup can continue past one bad directory with explicit failure reporting.
- Update tests and docs so the hardened behavior becomes the pinned contract.

**Non-Goals:**
- Changing the registry root, lease duration, canonical-name rules, or full SHA-256 `agent_key` derivation.
- Adding a heartbeat, daemon, or broader registry inspection CLI.
- Relaxing the strict v1 mailbox registry shape for hypothetical future non-filesystem transports.
- Reworking harmless internal cleanup such as duplicate canonicalization that does not affect behavior.

## Decisions

### 1. Broaden registry fallback to discovery-pointer failures, but not identity mismatches

Name-based tmux-backed control will continue trying tmux-local discovery first. The difference is that missing or stale `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` now count as fallback-eligible discovery failures rather than terminal errors.

The runtime will still fail fast on hard validation mismatches such as:
- registry or tmux manifest payloads whose persisted tmux session identity does not match the addressed agent name,
- invalid absolute-path requirements, or
- cases where both tmux-local and registry-backed resolution are unusable.

Rationale:
- this matches the original intent that the registry covers unavailable tmux-local discovery,
- it improves cross-root recovery without masking real ownership or integrity problems,
- and it keeps local tmux pointers authoritative when they are present and valid.

Alternatives considered:
- fallback only when `tmux has-session` fails: rejected because it leaves corrupted local pointers unrecoverable even when registry state is fresh.
- fallback on every tmux-local validation failure: rejected because that would hide manifest/session mismatch bugs that should remain explicit.

### 2. Treat malformed records as stale at resolution boundaries while preserving strict validation internally

Registry resolution will interpret missing, malformed, schema-invalid, or non-fresh records as unusable/stale results instead of surfacing those validation problems as lookup-stopping runtime errors.

Strict validation still matters. The implementation should keep a strict record parser for:
- publish-time verification,
- cleanup classification,
- diagnostics and operator-visible error details where appropriate.

Rationale:
- the spec already describes malformed records as a not-found or stale outcome,
- discovery is a best-effort locator path rather than an authoritative state store,
- and cleanup tooling remains the right place to remove bad directories after the reader stops treating them as live.

Alternatives considered:
- keep malformed records as hard resolution errors: rejected because one bad `record.json` can unnecessarily block recovery until manual cleanup.

### 3. Require timezone-aware timestamps in the registry record contract

`published_at` and `lease_expires_at` will require explicit timezone information in the persisted registry contract. Naive timestamps must be rejected during validation rather than interpreted relative to the reader's local timezone.

Rationale:
- lease freshness is part of the shared contract and must be deterministic,
- the current publisher already emits aware timestamps, so this is a contract tightening rather than a behavior change for healthy writers,
- and explicit offsets keep the schema honest for cross-environment readers and tests.

Alternatives considered:
- silently normalize naive timestamps to UTC: rejected because it weakens the contract and preserves ambiguous persisted data.

### 4. Keep lifecycle publication hooks, but isolate registry failures from primary runtime success paths

The runtime will continue publishing and refreshing shared-registry state at the lifecycle points already chosen by the original registry change:
- start,
- resume,
- manifest-persisting prompt or control flows,
- gateway capability and attach or detach,
- mailbox binding refresh,
- and authoritative stop teardown.

However, once the primary runtime action has already succeeded, a registry refresh or cleanup failure must not overwrite that success. This especially applies to:
- `send_prompt`,
- `interrupt`,
- `send_input_ex`,
- `refresh_mailbox_bindings`,
- `close`, and
- post-terminate registry cleanup in `stop`.

Start or resume publication failures may still surface directly because those paths are the explicit points where the system is materializing or reclaiming registry ownership for the live session.

Rationale:
- the registry is additive discovery metadata, not a required gate on primary session control,
- keeping the existing hooks preserves freshness behavior chosen in the earlier change,
- and distinguishing startup ownership failures from post-success refresh failures gives operators meaningful errors without breaking routine control flows.

Alternatives considered:
- disable refresh by default except on a smaller set of hooks: rejected because it changes the lifecycle contract already adopted in the original change.
- swallow all publication failures everywhere: rejected because it would hide registry ownership failures during start or resume.

### 5. Make registry filesystem helpers failure-tolerant and explicitly report partial cleanup failure

Two storage hardening rules are needed:

1. Atomic-write helpers must remove temp files when `replace()` fails after a temp file has been written.
2. Stale-record cleanup must continue past a per-directory removal failure and return explicit information about the failed directories instead of aborting the entire pass.

Cleanup should not silently discard failure details. Failed removals need a separate reported outcome rather than being collapsed into the same bucket as lease-fresh preserved directories.

Rationale:
- registry cleanup is expected best-effort maintenance work,
- a single busy or permission-protected directory should not block all later stale cleanup,
- and preserving failure visibility helps operators repair unusual filesystem problems without losing normal cleanup progress.

Alternatives considered:
- `ignore_errors=True` everywhere: rejected because it hides operational failures and makes debugging harder.

## Risks / Trade-offs

- [Risk] This change depends on the shared-registry model introduced by `add-central-agent-registry`, so archive or implementation ordering matters. -> Mitigation: keep that dependency explicit in proposal/design and scope this change only to follow-up hardening.
- [Risk] Treating malformed records as stale may reduce immediate visibility of corrupted registry files during ordinary lookup. -> Mitigation: keep strict validation for publish-time verification, cleanup classification, and targeted diagnostics/tests.
- [Risk] Isolating refresh failures from successful runtime actions could make operators miss registry drift if diagnostics are too quiet. -> Mitigation: require explicit warning or result reporting paths in runtime and CLI coverage.
- [Risk] Tightened timestamp validation can make old malformed records unreadable until they are refreshed or cleaned up. -> Mitigation: that is acceptable because such records should already be treated as stale/unusable; cleanup tooling and session republish paths provide recovery.

## Migration Plan

1. Update delta specs to pin the hardened fallback, malformed-record, timestamp, and cleanup semantics.
2. Implement runtime resolution changes so missing or stale tmux-local pointers can fall back to fresh registry state without hiding hard identity mismatches.
3. Implement registry lookup and storage hardening for malformed-record handling, timezone-aware timestamp validation, temp-file cleanup, and per-directory cleanup continuation with explicit failure reporting.
4. Update runtime control and teardown flows so successful prompt/control/stop actions remain successful even when secondary registry refresh or cleanup work fails.
5. Add unit and integration coverage for the newly pinned scenarios and update operator-facing docs.

Rollback strategy:
- revert to the prior registry behavior where malformed records may raise, discovery fallback is narrower, and registry errors can still propagate through primary runtime actions.
- existing session manifests, runtime roots, and shared-registry directory layout remain unchanged, so rollback is behavioral rather than migratory.

Operational note:
- existing malformed or naive-timestamp registry records may become unreadable under the hardened contract until the live session republishes them or `cleanup-registry` removes them. That is acceptable because those records should no longer be treated as trustworthy live discovery state.

## Open Questions

None.
