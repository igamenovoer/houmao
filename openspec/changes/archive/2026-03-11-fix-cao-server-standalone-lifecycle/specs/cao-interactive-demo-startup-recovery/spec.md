## REMOVED Requirements

### Requirement: Interactive demo startup SHALL confirm before recycling an existing verified local loopback CAO server
**Reason**: Interactive demo agent recreation is now required to deterministically replace the verified fixed-loopback CAO service instead of routing through an operator confirmation branch.
**Migration**: Repo-local callers and docs should assume that starting a new interactive demo agent on the fixed loopback target automatically recycles the verified local `cao-server`; `-y` no longer controls that replacement decision.

## ADDED Requirements

### Requirement: Interactive demo startup SHALL force-replace the verified local loopback CAO server during agent recreation
For the fixed local CAO target `http://127.0.0.1:9889`, interactive demo startup SHALL establish a fresh standalone local `cao-server` context for each agent recreation instead of silently reusing stale or incompatible server state.

If launcher `status` verifies that a healthy local `cli-agent-orchestrator` service is already serving the fixed loopback target, the demo SHALL treat that service as a verified local `cao-server` and SHALL stop it before launching the replacement server context for the new run.

If launcher status is not healthy but the fixed loopback target is still occupied, the demo MAY use best-effort process inspection as a fallback verification path. That fallback SHALL skip unreadable or disappearing procfs entries and SHALL only fail when the loopback occupant still cannot be safely verified as `cao-server`.

If the process serving the fixed loopback target cannot be safely verified as `cao-server`, the demo SHALL fail explicitly and SHALL NOT create an active interactive state artifact.

If the demo cannot complete the stop-and-restart sequence for the verified fixed-loopback CAO service, it SHALL fail explicitly and SHALL NOT continue with interactive session creation.

#### Scenario: Verified stale loopback CAO server is recycled automatically
- **WHEN** a developer starts the interactive demo and a verified local `cao-server` is already healthy on `http://127.0.0.1:9889`
- **THEN** the demo stops that server before creating the replacement local CAO server context
- **AND THEN** the subsequent interactive session launch uses the demo's configured launcher-home context instead of the stale server context

#### Scenario: Unreadable unrelated procfs entries do not block verified replacement
- **WHEN** a developer starts the interactive demo and launcher status already verifies a healthy local `cao-server` on the fixed loopback target
- **AND WHEN** unrelated `/proc/<pid>/fd` directories on the same machine are unreadable
- **THEN** the demo still treats the loopback occupant as verified for replacement purposes
- **AND THEN** startup does not fail solely because those unrelated procfs entries were unreadable

#### Scenario: Fallback process verification skips unreadable procfs entries
- **WHEN** a developer starts the interactive demo and launcher status is not healthy while the fixed loopback target is still occupied
- **AND WHEN** procfs inspection encounters unreadable or disappearing `/proc/<pid>/fd` entries during fallback verification
- **THEN** the demo skips those entries and continues best-effort verification
- **AND THEN** startup does not crash solely because one procfs entry could not be inspected

#### Scenario: Unverifiable loopback port occupant fails safely
- **WHEN** a developer starts the interactive demo and the fixed loopback target is occupied by a process that cannot be safely verified as `cao-server`
- **THEN** startup fails with an explicit diagnostic
- **AND THEN** the demo does not write `state.json` as active

#### Scenario: Replacement failure leaves no active interactive state
- **WHEN** a developer starts the interactive demo and a verified local `cao-server` is already serving `http://127.0.0.1:9889`
- **AND WHEN** the demo cannot successfully stop that server or cannot start its replacement CAO context
- **THEN** startup fails explicitly
- **AND THEN** the demo does not continue with interactive session creation
