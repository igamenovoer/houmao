# Design

## Context

Issue #104 was reproduced against `78e48c5d` using stock Hermes v0.23.4 and the instructional Hermes cases. The runtime already has native admission, current-generation registry authority, owner-private daemon evidence, and a shared self-manifest resolver. The fixture keeps a separate run snapshot for developer follow-up. [Proposal](proposal.md)

## Goals / Non-Goals

Use the existing owner prompt ledger and native Hermes receipt contract. Keep readiness and terminal attachment independent. For self targeting, require current generation and recorded daemon evidence while retaining the existing permission and key checks.

Keep the scope to manager control, verified Hermes service and TUI callers, and manager fixtures. The Hermes protocol, public command names, terminal parser operations, and mailbox transports retain their existing contracts.

## Decisions

### Carry One Owner Claim Through Native Submission and Settlement

Select the structured Hermes TUI path at the shared manager prompt entrypoint so local, self, and delegated callers use it. Verify the exact current owner, reserve once with Hermes reconciliation, and pass that claim and request ID to `submit_native_prompt`. The backend already checks the pinned native session immediately before submitting. A prior state sample explains readiness but cannot reserve future admission.

The parser path cannot describe Hermes native state. The full Hermes observer also reconciles the owner ledger, so invoking it from the reservation callback would open a second write transaction while the first is held. Keep full observation outside that transaction. Use the final native check and retire a confirmed pre-handoff refusal without leaving an unresolved claim. [Manager Dispatch](../../../src/houmao/srv_ctrl/commands/managed_agents.py#L2734) · [Owner Reservation](../../../src/houmao/agents/realm_controller/owner_admission.py#L422)

Extract the existing bounded receipt wait so it consumes an already-admitted request. It queries Hermes directly, which allows settlement without a gateway. Map the manager response from the attributable typed receipt because the generic event-based path expects terminal events that Hermes does not emit. A terminal result needs verified outcome evidence. At deadline, report a verified queue acceptance or handoff when available. Otherwise report uncertainty and preserve the unresolved claim. Keep the existing exact-ID acknowledgment recovery. Gateway submission still returns its immediate native acknowledgment. Delegated waits and native calls must fit the remaining v1 execution deadline. [Receipt Reader](../../../src/houmao/agents/realm_controller/backends/hermes_tui.py#L601)

### Separate Self Lookup, Caller Provenance, and Gateway Liveness

Choose the detached Hermes path before interpreting service supervisor tmux hints. Use the runtime-supplied manifest locator for normal launches. For a stock-started daemon adopted for the exact managed home, publish a small owner-private locator at a fixed path confined to that home. The canonical Hermes home is a discovery input. The locator contains identity, generation, and a confined runtime manifest path. It carries no credentials and confers no authority.

Publish or refresh daemon evidence when the owning lifecycle verifies the daemon and its saved native binding. Reuse the runtime-owned Hermes evidence paths. TUI uses its manifest-specific native directory. Service selects the exact private service incarnation and validates its existing native binding. Do not use the ACP client's PID as proof of the daemon. Bind the evidence to the manifest, generation, owner, launch home, and workspace. Fence updates across replacement and check the recorded native session binding where available. For same-daemon reuse across a generation change, fence old work before publishing the new binding. Discovery alone cannot establish self authority.

The common self resolver checks manifest confinement, execution identity, active registry generation, and native owner evidence. Use bounded checks of the kernel parent chain and daemon birth identity for the local tool caller. Confirm the birth identity and generation at the proof boundary. Ancestry establishes ownership by the managed daemon. The saved session identifies the runtime's native binding. A forged, unreadable, or stale Hermes proof fails before signing or dispatch.

Gateway self-key lookup and ingress share the current-generation and exact daemon liveness check. The gateway process itself does not run under the Hermes daemon. Preserve the existing target, key registration, revision, grant, and listener checks. Read-only self verification does not start a daemon or publish owner evidence. Tmux-only controls still verify their owning surface. [Self Resolver](../../../src/houmao/agents/realm_controller/self_manifest.py#L72) · [Daemon Evidence](../../../src/houmao/agents/realm_controller/backends/hermes_native.py#L353) · [Gateway Liveness](../../../src/houmao/agents/realm_controller/gateway_access_runtime.py#L83)

### Verify Fixture Ownership Before Following a New Generation

For a manager run, load the captured ID under its recorded fixture registry and resolve the exact local record. Match the confined manifest, owner binding, runtime lineage, backend, and socket to the captured run. Existing runs can establish lineage from their saved identity, manifest, and socket. Persist any additional verified identifiers for future checks. A newer generation may refresh the run only when it belongs to that same runtime. Pass the verified target to the existing operation and fence the generation again at the effect boundary. A fresh selector lookup could choose a different owner.

Clear stale cleanup flags when the captured runtime becomes active. Use current verified gateway metadata for fixture routes that already use a gateway. A confirmed stopped runtime permits idempotent stop. Missing or mismatched evidence requires an explicit diagnostic. Keep offline inspection and the raw and passive fixture paths on their existing contracts.

Capture launch identity before the initial prompt and keep that identity for failure-path cleanup. Report manager failures with the existing structured error plus the exit code and exact run-private diagnostic path when written. Allocate the diagnostic path uniquely, keep it private, and redact credential values. Public errors use an operation label and omit raw arguments and diagnostics. [Fixture Lifecycle](../../../scripts/agents/test-fixtures/fixturelib/launch.py#L797) · [Error Capture](../../../scripts/agents/test-fixtures/fixturelib/prepare.py#L142)

## Risks / Trade-Offs

- A busy snapshot can change between state and prompt. The final native check governs submission, and a verified native queue receipt survives a human input race.
- A daemon or runtime can change between observation and proof. Fence by generation and process birth, and leave ambiguous admissions unresolved.
- A fixture may see a reused logical ID or a relaunch in progress. Require the captured lineage before mutation, and preserve the evidence needed to diagnose the refusal.

## Migration Plan

Ship native prompt dispatch and detached proof before relying on fixture reconciliation for end-to-end qualification. A Hermes generation with insufficient detached-owner evidence can obtain it through a supported launch or explicit relaunch. Existing fixture snapshots are reconciled after verification. When syncing the specs, update the self-identity capability's purpose to include verified detached daemon callers.
