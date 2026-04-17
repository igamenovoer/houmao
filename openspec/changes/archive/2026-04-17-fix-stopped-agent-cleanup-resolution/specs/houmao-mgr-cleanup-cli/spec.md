## ADDED Requirements

### Requirement: Agent cleanup selectors recover stopped sessions from the runtime root
When `houmao-mgr agents cleanup session|logs|mailbox` is invoked with `--agent-id` or `--agent-name` and no fresh shared-registry record exists for that selector, the command SHALL attempt a cleanup-only fallback scan of the effective local runtime root for runtime-owned session envelopes.

The fallback scan SHALL match only persisted session manifests whose `agent_id` or `agent_name` equals the selected cleanup identity. The fallback SHALL NOT make stopped sessions visible to live-control commands such as prompt, interrupt, state, gateway, or mail operations.

When the fallback finds exactly one matching stopped session envelope, the cleanup command SHALL resolve that envelope as the cleanup target and SHALL continue using the existing live-session safety checks before deleting session roots or cleanup-sensitive artifacts.

When the fallback finds multiple matching stopped session envelopes, the cleanup command SHALL fail explicitly with enough candidate metadata for the operator to rerun cleanup with `--manifest-path` or `--session-root`.

When neither fresh registry resolution nor runtime-root fallback finds a target, the cleanup command SHALL fail explicitly and SHALL direct the operator to provide `--manifest-path`, `--session-root`, or the appropriate runtime-root selection when the desired stopped session lives outside the effective runtime root.

The system SHALL NOT create or depend on stopped-session tombstones, stopped-agent indexes, or additional shared-registry records for this fallback.

#### Scenario: Stopped session cleanup recovers by agent id after registry removal
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-id agent-123`
- **AND WHEN** no fresh shared-registry record exists for `agent-123`
- **AND WHEN** exactly one stopped runtime session manifest under the effective runtime root contains `agent_id = "agent-123"`
- **THEN** the command resolves that stopped session envelope as the cleanup target
- **AND THEN** cleanup does not require a live shared-registry record for that stopped session

#### Scenario: Stopped session cleanup recovers by friendly name after registry removal
- **WHEN** an operator runs `houmao-mgr agents cleanup logs --agent-name reviewer`
- **AND WHEN** no fresh shared-registry record exists for `reviewer`
- **AND WHEN** exactly one stopped runtime session manifest under the effective runtime root contains `agent_name = "reviewer"`
- **THEN** the command resolves that stopped session envelope as the cleanup target
- **AND THEN** the command reports the resolved `manifest_path` and `session_root` in its cleanup scope or action details

#### Scenario: Ambiguous stopped cleanup selector fails closed
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-name reviewer`
- **AND WHEN** no fresh shared-registry record exists for `reviewer`
- **AND WHEN** more than one stopped runtime session manifest under the effective runtime root contains `agent_name = "reviewer"`
- **THEN** the command fails with an ambiguity error
- **AND THEN** the error includes candidate cleanup locators such as `agent_id`, `agent_name`, `manifest_path`, and `session_root`

#### Scenario: Cleanup fallback does not address live control
- **WHEN** no fresh shared-registry record exists for `reviewer`
- **AND WHEN** a stopped runtime session manifest under the effective runtime root contains `agent_name = "reviewer"`
- **THEN** `houmao-mgr agents cleanup session --agent-name reviewer` may use runtime-root fallback for cleanup
- **AND THEN** `houmao-mgr agents prompt --agent-name reviewer` does not use that stopped manifest as a live-control target

#### Scenario: No stopped cleanup match remains explicit
- **WHEN** an operator runs `houmao-mgr agents cleanup mailbox --agent-id missing-agent`
- **AND WHEN** no fresh shared-registry record exists for `missing-agent`
- **AND WHEN** no stopped runtime session manifest under the effective runtime root contains `agent_id = "missing-agent"`
- **THEN** the command fails explicitly
- **AND THEN** the error tells the operator to provide a durable cleanup locator such as `--manifest-path` or `--session-root`
