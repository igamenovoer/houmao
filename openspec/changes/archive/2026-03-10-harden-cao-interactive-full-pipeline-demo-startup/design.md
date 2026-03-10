## Context

The interactive CAO full-pipeline demo pins startup to `http://127.0.0.1:9889` and already has a startup-recovery contract for replacing an existing verified local `cao-server`. In practice, the current implementation in `gig_agents.demo.cao_interactive_full_pipeline_demo` still has two fragile edges:

- startup can fail in environments where a valid local `cao-server` is already listening on the fixed loopback target if replacement falls through to fragile process-table inspection instead of staying on the launcher-managed verification path, and
- procfs fallback logic can raise `PermissionError` while iterating unrelated `/proc/<pid>/fd` directories, turning a recoverable verification path into a startup crash.

This change is intentionally narrow. It does not alter the fixed loopback target, the demo wrapper CLI shape, or the broader brain-launch runtime semantics. It hardens the demo's existing startup-recovery behavior so the advertised wrapper flow remains dependable on real developer machines and in deterministic integration coverage.

## Goals / Non-Goals

**Goals:**

- Keep the fixed-port interactive demo startup working when a verified local `cao-server` already exists and the operator confirms replacement or supplies `-y`.
- Make loopback occupant inspection tolerant of unreadable procfs entries so unrelated permission boundaries do not crash startup.
- Preserve explicit failure when the loopback occupant truly cannot be verified as `cao-server`.
- Refresh demo startup tests so verified replacement and procfs-restriction cases remain deterministic.

**Non-Goals:**

- Changing the demo's fixed CAO base URL or allowing alternate CAO targets.
- Reworking the CAO launcher contract or the brain-launch runtime startup protocol.
- Broadening procfs inspection helpers into shared runtime-wide infrastructure.

## Decisions

### 1. Treat launcher-verified `cao-server` status as the primary authority

When launcher `status` reports a healthy `cli-agent-orchestrator` service on the fixed loopback target, the demo should stay on the launcher-managed replacement path. That means replacement should be driven by the known launcher `stop`/`start` flow and should not require deeper procfs-based occupant verification to succeed.

This keeps the happy path aligned with the existing demo contract and avoids unnecessary exposure to unrelated local process-table complexity when the launcher already proved the occupant is the right service.

Alternative considered: always cross-check launcher status with procfs occupant discovery before replacement. Rejected because it makes the verified path more fragile without adding operator value; launcher verification is already the user-facing authority for this demo flow.

### 2. Keep procfs occupant discovery as a fallback, but make it best-effort

The procfs-based fallback for "port is occupied but launcher status is not healthy" remains useful, because it is the last safety barrier before killing an unknown loopback occupant. However, it should treat unreadable `/proc/<pid>/fd` directories, unreadable symlinks, and disappearing processes as non-matching evidence rather than fatal errors.

In practice this means:

- skip `/proc/<pid>/fd` directories that cannot be listed,
- skip individual `fd` entries that cannot be read,
- continue scanning other candidate processes,
- only fail as unverifiable when the occupant still cannot be uniquely proven to be `cao-server` after the best-effort scan completes.

Alternative considered: drop procfs fallback entirely and rely only on launcher stop paths. Rejected because the demo still needs a safe explicit refusal path when the fixed loopback port is occupied by something outside the known launcher-managed contexts.

### 3. Preserve the existing fail-safe semantics for truly unverifiable occupants

This hardening should not silently kill unknown services. If launcher status is unhealthy and the loopback port is still occupied, startup should still fail unless the fallback can uniquely identify the occupant as `cao-server`.

The key behavior change is not "be more permissive"; it is "do not confuse procfs access noise with proof that the occupant is unsafe or unknown."

Alternative considered: allow replacement whenever the port looks occupied by a single process, even if the command line cannot be verified. Rejected because it weakens the safety contract the demo already documents.

### 4. Make startup coverage deterministic under ambient local loopback state

The demo's integration coverage should not depend on the real machine's current port `9889` state. The tests for wrapper startup and replacement should stub or control loopback-occupancy signals explicitly so they continue to validate the demo contract even when a developer already has a real `cao-server` running locally.

Alternative considered: leave the current tests as-is and rely on clean local environments. Rejected because the demo specifically targets real operator machines, and the integration suite should remain stable in the same kind of environment.

## Risks / Trade-offs

- [Best-effort procfs scanning can hide some permission-denied details] -> Mitigation: keep explicit failure when occupant verification remains inconclusive and preserve actionable diagnostics for the final unverifiable outcome.
- [Launcher-first replacement could miss a mismatch between status output and the actual port occupant] -> Mitigation: keep the requirement that only a healthy `cli-agent-orchestrator` status counts as verified, and keep the existing refusal path for unhealthy or mismatched status.
- [Test isolation changes may diverge from real startup behavior] -> Mitigation: isolate only the environment-sensitive signals in tests while keeping the wrapper command flow and launcher JSON contracts intact.

## Migration Plan

1. Update the interactive demo startup-recovery spec delta to distinguish verified replacement from best-effort fallback verification.
2. Harden `cao_interactive_full_pipeline_demo.py` so procfs fallback skips unreadable entries and launcher-verified replacement stays on the supported stop/start path.
3. Refresh integration coverage for verified replacement, `-y`, and permission-restricted procfs traversal.
4. Validate the demo-specific unit and integration suites.

Rollback strategy: revert the demo startup hardening changes; the prior behavior is localized to the interactive demo module and its tests.

## Open Questions

- Should the demo log a non-fatal diagnostic when procfs fallback skips unreadable directories, or is silent best-effort handling sufficient as long as final failures stay explicit?
