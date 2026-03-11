## Context

The interactive CAO demo starts against a fixed loopback CAO target at `http://127.0.0.1:9889` and is intended to replace any verified local `cao-server` that is already serving that endpoint. The replacement flow first tries launcher-managed `stop` against the current run's config and then walks previously recorded demo configs that may own the live fixed-port service.

The observed failure happens before that search can complete. When launcher `stop` is invoked with a fresh runtime root whose `runtime/cao-server/<host>-<port>/` directory has not been created yet, the launcher tries to persist `launcher_result.json` into a non-existent parent directory and crashes. The interactive demo then treats that traceback as fatal malformed stop output and aborts replacement before it can try older known configs.

This change is intentionally narrower than the earlier standalone-lifecycle work. It does not redefine replacement policy; it hardens the already-intended replacement sequence so fresh run roots and stale config candidates do not turn safe replacement into startup failure.

## Goals / Non-Goals

**Goals:**
- Make launcher `stop` return structured results even when its artifact directory has not yet been created for the current config.
- Preserve launcher-managed verified replacement as the preferred interactive-demo path.
- Allow the demo replacement loop to keep trying later known configs when one stop attempt fails to produce usable structured output and the fixed loopback service is still present.
- Add focused regression coverage at the launcher and interactive-demo layers.

**Non-Goals:**
- Changing the fixed loopback target or introducing multi-port CAO discovery.
- Reworking the standalone CAO ownership model introduced by the lifecycle change.
- Making the demo silently kill unverifiable loopback occupants.
- Replacing the existing procfs/PID fallback policy with a new process-management subsystem.

## Decisions

### 1. Launcher result persistence will create parent directories lazily

The launcher already treats `launcher_result.json` as a stable diagnostics artifact for `start` and `stop`. The safest place to repair the missing-directory crash is at the shared result-writing boundary, so result persistence will ensure the parent directory exists before writing.

Why this over only patching `stop_cao_server()`:
- The bug is fundamentally a filesystem precondition violation at the artifact-writing layer.
- Fixing it once at the writer keeps all early-return `stop` paths safe and protects future callers that also rely on structured result output.
- It preserves the current launcher contract instead of adding special-case logic to a single stop branch.

Alternatives considered:
- Create the artifact directory only at the top of `stop_cao_server()`: viable, but narrower and easier to regress if more result-writing call sites are added later.
- Catch `FileNotFoundError` in the interactive demo and fall back immediately: rejected because it leaves the launcher itself unable to satisfy its own diagnostics contract.

### 2. Interactive demo replacement will treat one bad stop candidate as non-terminal while the verified service is still listening

The interactive demo's `_stop_cao_server_with_known_configs()` routine already walks multiple launcher configs because the currently live fixed-port service may belong to an earlier run. That routine will be hardened so a single candidate that returns malformed or unusable stop output does not abort the full replacement attempt as long as:
- the loopback target is still listening, and
- there are more known configs to try.

Why this over relying only on the launcher fix:
- The launcher fix addresses the observed repro, but the demo is still coordinating across multiple potentially stale configs.
- The demo should remain resilient if one candidate points at damaged artifacts or an older partially broken runtime root.
- This keeps the preferred launcher-managed replacement path intact instead of prematurely dropping to PID-based fallback or failing fast.

Alternatives considered:
- Stop after the first launcher error and force PID-based termination immediately: rejected because it discards ownership-aware launcher verification too early.
- Ignore malformed stop output completely and always keep going: rejected because the demo should still fail if the service becomes unverifiable or all candidates are exhausted.

### 3. Regression coverage will prove both the launcher contract and the cross-config replacement flow

This bug crossed a module boundary: launcher `stop` violated its structured-output contract, and the interactive demo treated that as fatal before finishing its known-config scan. Tests should therefore exist at both layers.

Why this over only adding an integration test:
- A launcher unit test can pinpoint the missing-directory condition directly and keep the failure easy to diagnose.
- A demo test can prove the intended higher-level behavior: fresh current config plus older owning config still results in successful verified replacement.

Alternatives considered:
- Demo-only tests: rejected because they hide whether a future regression came from launcher result persistence or the demo retry logic.

## Risks / Trade-offs

- [Demo hardening could mask genuine launcher breakage] → Only continue to later configs while the loopback service is still present and still on the verified replacement path; fail once candidates are exhausted or the service becomes unsafe to classify.
- [Shared result-writer mkdir broadens artifact creation side effects] → Limit the change to parent-directory creation immediately before file write; do not create unrelated state or alter payload semantics.
- [OpenSpec capability overlap with the earlier standalone-lifecycle change] → Keep this change narrowly scoped to stop-path robustness and cross-config retry behavior, not lifecycle-policy redesign.

## Migration Plan

1. Harden launcher result persistence so `stop` can emit structured output from a fresh runtime root.
2. Update interactive-demo replacement to continue across known configs when one candidate returns malformed stop output and the verified fixed-port service is still listening.
3. Add launcher and demo regression tests for the observed failure mode.
4. Re-run the interactive CAO demo start flow against an already-healthy fixed-port `cao-server`.

Rollback strategy:
- Revert the launcher mkdir hardening and demo retry changes together if they introduce incorrect replacement behavior.
- Keep the current manual-recovery workaround available: direct verified process termination followed by a fresh demo start.

## Open Questions

- Whether malformed stop output from a known config should be surfaced in the final startup error message as aggregated diagnostics if every candidate fails.
- Whether the same retry-hardening should also be applied to any future non-demo CAO replacement workflows that iterate over known launcher configs.
