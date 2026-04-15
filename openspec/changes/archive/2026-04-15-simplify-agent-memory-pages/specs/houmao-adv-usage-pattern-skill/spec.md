## REMOVED Requirements

### Requirement: Advanced usage patterns store mutable ledgers in the workspace scratch lane
**Reason**: Managed memory no longer includes a scratch lane, and pages must not become scratch ledgers under another name.

**Migration**: Advanced usage patterns SHALL use mailbox, reminders, runtime-visible state, or pattern-specific mechanisms for mutable retry and dedupe ledgers. They may use readable memory pages only for operator-visible context summaries.

## ADDED Requirements

### Requirement: Advanced usage patterns do not use managed memory as mutable ledger storage
The `houmao-adv-usage-pattern` skill SHALL NOT direct mutable pairwise edge-loop or relay-loop ledgers to managed memory pages by default.

When the pattern references durable operator-visible context, it SHALL describe readable memo pages under `HOUMAO_AGENT_PAGES_DIR` as summaries or pointers rather than authoritative retry/dedupe ledgers.

The skill SHALL NOT reference `HOUMAO_AGENT_SCRATCH_DIR` or `HOUMAO_AGENT_PERSIST_DIR` as current managed memory variables.

#### Scenario: Pairwise guidance avoids scratch-lane ledger paths
- **WHEN** an agent reads the pairwise edge-loop advanced usage pattern
- **THEN** the guidance does not direct the agent to store the ledger under `$HOUMAO_AGENT_SCRATCH_DIR/edge-loops/ledger.json`
- **AND THEN** any memory page guidance is framed as readable context rather than mutable retry authority

#### Scenario: Relay guidance avoids scratch-lane ledger paths
- **WHEN** an agent reads the relay-loop advanced usage pattern
- **THEN** the guidance does not direct the agent to store the ledger under `$HOUMAO_AGENT_SCRATCH_DIR/relay-loops/ledger.json`
- **AND THEN** the guidance does not use `HOUMAO_AGENT_PERSIST_DIR` for long-lived archive notes
