## ADDED Requirements

### Requirement: Managed-session cleanup resolves stopped lifecycle registry records
`houmao-mgr agents cleanup session|logs|mailbox` SHALL resolve stopped lifecycle-aware registry records by `--agent-id` and `--agent-name` when those records preserve runtime manifest or session-root authority.

When a stopped lifecycle registry record resolves to a valid runtime-owned session root, cleanup SHALL use that registry record as the cleanup authority rather than requiring a runtime-root scan.

When both a lifecycle registry record and a stopped runtime-root scan candidate match the same selector, the lifecycle registry record SHALL be preferred as the authoritative target.

When multiple stopped lifecycle records match a friendly name, cleanup SHALL fail explicitly and SHALL list candidate agent ids, lifecycle states, manifest paths, and session roots.

#### Scenario: Cleanup resolves stopped record by friendly name
- **WHEN** an operator runs `houmao-mgr agents cleanup logs --agent-name reviewer`
- **AND WHEN** exactly one stopped lifecycle registry record stores `agent_name = "reviewer"` and a valid session root
- **THEN** cleanup resolves that stopped registry record as the target
- **AND THEN** cleanup does not require the operator to copy `--manifest-path` or `--session-root` from the earlier stop output

#### Scenario: Cleanup prefers registry record over stopped runtime scan
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-id agent-123`
- **AND WHEN** the lifecycle registry contains a stopped record for `agent-123`
- **AND WHEN** a runtime-root scan also finds a matching stopped manifest
- **THEN** cleanup uses the registry record as the authoritative identity and locator source
- **AND THEN** the runtime-root scan does not select a different target

#### Scenario: Cleanup stopped friendly-name ambiguity fails closed
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-name reviewer`
- **AND WHEN** two stopped lifecycle registry records store `agent_name = "reviewer"`
- **THEN** cleanup fails explicitly
- **AND THEN** the error lists candidate `agent_id`, lifecycle state, manifest path, and session root values

### Requirement: Managed-session cleanup retires or purges stopped registry records
When `houmao-mgr agents cleanup session` removes or validates removal of a stopped managed-agent session root, the command SHALL update the corresponding lifecycle-aware registry record so that future relaunch does not target deleted runtime artifacts.

By default, cleanup SHOULD mark the registry record as `retired` when the registry record remains useful for audit and diagnostics. The cleanup surface SHALL provide an explicit purge mode to delete the registry record entirely when the operator wants to remove the lifecycle index entry.

Retired registry records SHALL NOT be considered relaunchable and SHALL NOT be included in active list output. Lifecycle-inclusive listing MAY show retired records only when explicitly requested.

#### Scenario: Session cleanup retires stopped record by default
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-name reviewer`
- **AND WHEN** cleanup removes the stopped session root for a lifecycle registry record
- **THEN** the registry record transitions to lifecycle state `retired`
- **AND THEN** future `houmao-mgr agents relaunch --agent-name reviewer` fails with an explicit retired-record message

#### Scenario: Session cleanup purge deletes registry record
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-name reviewer --purge-registry`
- **AND WHEN** cleanup removes the stopped session root for a lifecycle registry record
- **THEN** the registry record is deleted from the managed-agent registry
- **AND THEN** future selector lookup does not find that managed-agent record

#### Scenario: Dry-run cleanup reports registry lifecycle action
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-id agent-123 --dry-run`
- **AND WHEN** the selected stopped registry record would be retired or purged during execute mode
- **THEN** the dry-run cleanup payload includes the planned registry lifecycle action
- **AND THEN** the registry record is not mutated during dry-run

### Requirement: Cleanup preserves active lifecycle records unless explicitly forced through supported live safeguards
Cleanup commands SHALL NOT remove or retire active lifecycle registry records merely because they match an agent name or id.

When cleanup resolves an active record, it SHALL apply the existing live-session safety checks before removing runtime artifacts. If live cleanup is unsupported for the selected action, cleanup SHALL fail explicitly and direct the operator to stop the agent first.

#### Scenario: Cleanup refuses active session root without stop
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-name reviewer`
- **AND WHEN** `reviewer` resolves to an active lifecycle registry record with a live tmux session
- **THEN** cleanup refuses to remove the active session root
- **AND THEN** the error instructs the operator to stop the agent or use an explicit supported force-cleanup flow

#### Scenario: Log cleanup can preserve durable active state
- **WHEN** an operator runs `houmao-mgr agents cleanup logs --agent-id agent-123`
- **AND WHEN** `agent-123` resolves to an active lifecycle registry record
- **THEN** cleanup does not retire or purge the registry record
- **AND THEN** any supported log cleanup still preserves durable manifest, gateway queue, events, and state artifacts
