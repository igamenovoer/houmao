## ADDED Requirements

### Requirement: Advanced usage patterns store mutable ledgers in the workspace scratch lane
The `houmao-adv-usage-pattern` skill SHALL direct mutable pairwise edge-loop and relay-loop ledgers to `HOUMAO_AGENT_SCRATCH_DIR`.

The skill SHALL NOT describe `HOUMAO_JOB_DIR` or `HOUMAO_MEMORY_DIR` as the current default location for mutable loop bookkeeping.

When the pattern references durable backlog notes or long-lived archives, it SHALL use `HOUMAO_AGENT_PERSIST_DIR` only when that variable is available.

#### Scenario: Pairwise ledger uses scratch lane
- **WHEN** the pairwise edge-loop pattern describes its local mutable ledger
- **THEN** it directs agents to store the ledger under `$HOUMAO_AGENT_SCRATCH_DIR/edge-loops/ledger.json`
- **AND THEN** it does not present `HOUMAO_JOB_DIR` as the ledger home

#### Scenario: Relay ledger uses scratch lane
- **WHEN** the relay-loop pattern describes its local mutable ledger
- **THEN** it directs agents to store the ledger under `$HOUMAO_AGENT_SCRATCH_DIR/relay-loops/ledger.json`
- **AND THEN** it does not present `HOUMAO_MEMORY_DIR` as the ledger home
