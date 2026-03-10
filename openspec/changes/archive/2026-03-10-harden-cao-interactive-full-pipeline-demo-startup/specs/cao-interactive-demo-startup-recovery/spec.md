## MODIFIED Requirements

### Requirement: Interactive demo startup SHALL confirm before recycling an existing verified local loopback CAO server
For the fixed local CAO target `http://127.0.0.1:9889`, interactive demo startup SHALL establish a fresh local `cao-server` context instead of silently reusing stale or incompatible server state.

If launcher `status` verifies that a healthy local `cli-agent-orchestrator` service is already serving the fixed loopback target, the demo SHALL treat that service as a verified local `cao-server` for replacement decisions and SHALL stay on the launcher-managed replacement path.

If a local `cao-server` is already serving the fixed loopback target and can be verified as `cao-server`, the demo SHALL prompt for confirmation before stopping it and launching the replacement server context for the tutorial run.

If the operator supplies `-y` through the demo script surface, the demo SHALL treat that confirmation as already granted.

If launcher status is not healthy but the fixed loopback target is still occupied, the demo MAY use best-effort process inspection as a fallback verification path. That fallback SHALL skip unreadable or disappearing procfs entries and SHALL only fail when the loopback occupant still cannot be safely verified as `cao-server`.

If the process serving the fixed loopback target cannot be safely verified as `cao-server`, the demo SHALL fail explicitly and SHALL NOT create an active interactive state artifact.

#### Scenario: Verified stale loopback CAO server is recycled after confirmation
- **WHEN** a developer starts the interactive demo and a verified local `cao-server` is already healthy on `http://127.0.0.1:9889`
- **AND WHEN** the developer confirms the replacement prompt
- **THEN** the demo stops that server before creating the replacement local CAO server context
- **AND THEN** the subsequent interactive session launch uses the demo's configured launcher-home context instead of the stale server context

#### Scenario: `-y` bypasses the replacement prompt
- **WHEN** a developer starts the interactive demo with `-y`
- **AND WHEN** a verified local `cao-server` is already healthy on `http://127.0.0.1:9889`
- **THEN** the demo replaces that server without waiting for an interactive confirmation prompt
- **AND THEN** the new session launch continues with the demo's configured launcher-home context

#### Scenario: Declining replacement leaves no active state
- **WHEN** a developer starts the interactive demo and a verified local `cao-server` is already healthy on `http://127.0.0.1:9889`
- **AND WHEN** the developer declines the replacement prompt
- **THEN** startup exits without replacing the existing CAO server
- **AND THEN** the demo does not write `state.json` as active

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
