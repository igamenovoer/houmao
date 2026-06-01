## ADDED Requirements

### Requirement: Registry-backed discovery includes external communication-only records
`houmao-mgr` registry-backed managed-agent discovery SHALL include external communication-only records as selectable communication targets while preserving the existing local lifecycle record contract.

Local lifecycle records under `live_agents/` SHALL remain the first registry discovery source for normal managed-agent selectors. External records SHALL be considered only after no matching local lifecycle record is selected. Explicit pair-port targeting SHALL continue to bypass registry discovery.

External discovery SHALL resolve by local external-agent id for `--agent-id` and by local external-agent name for `--agent-name`. It SHALL route to the stored remote agent reference rather than treating the local alias as a remote pair-managed identity.

#### Scenario: External record resolves after local lifecycle lookup
- **WHEN** an operator runs `houmao-mgr agents state --agent-name remote-james`
- **AND WHEN** no local lifecycle record matches `remote-james`
- **AND WHEN** exactly one external communication-only record has local name `remote-james`
- **THEN** registry discovery resolves the external record
- **AND THEN** command routing uses the record's stored remote pair API base URL and remote agent reference

#### Scenario: Local lifecycle record takes precedence over external alias
- **WHEN** a local lifecycle record and an external communication-only record could both match selector `james`
- **THEN** registry discovery selects the local lifecycle record
- **AND THEN** it does not silently shadow local lifecycle authority with the external alias

#### Scenario: Explicit port bypass remains unchanged
- **WHEN** an operator runs `houmao-mgr agents state --agent-name remote-james --port 9891`
- **THEN** the command uses the explicit local-loopback pair port behavior
- **AND THEN** it does not read local lifecycle or external communication-only registry records for that invocation

### Requirement: External registry records remain separate from local lifecycle records
External communication-only records SHALL be stored in a registry collection that is separate from local lifecycle records. Local lifecycle validation, lease freshness, tmux liveness probing, relaunch resolution, and stale local runtime cleanup SHALL NOT require external records to contain local runtime metadata.

Registry cleanup that is designed for stale local lifecycle records SHALL NOT delete valid external communication-only records merely because they lack local tmux sessions, local leases, or local manifest paths.

#### Scenario: External record without local manifest remains valid
- **WHEN** the registry contains a valid external communication-only record with no local manifest path and no tmux session metadata
- **THEN** registry readers accept it as an external locator record
- **AND THEN** local lifecycle record validation is not applied to that external record

#### Scenario: Local stale cleanup preserves external record
- **WHEN** a local stale-registry cleanup pass inspects registry state
- **AND WHEN** it encounters a valid external communication-only record
- **THEN** the cleanup pass preserves the external record
- **AND THEN** it does not remove the record due to missing local tmux liveness
