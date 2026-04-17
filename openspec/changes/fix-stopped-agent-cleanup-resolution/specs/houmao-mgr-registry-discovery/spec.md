## ADDED Requirements

### Requirement: Managed-agent stop responses include durable cleanup locators
`houmao-mgr agents stop` SHALL include durable cleanup locator fields in its successful structured response when the resolved managed-agent target exposes local manifest authority.

At minimum, the successful stop response SHALL include:

- `manifest_path`
- `session_root`

The command SHALL capture these values before clearing or otherwise losing the live shared-registry record. These locator fields SHALL remain valid for supported `houmao-mgr agents cleanup session|logs|mailbox --manifest-path` or `--session-root` follow-up as long as the corresponding runtime-owned artifacts still exist.

The stop command SHALL NOT keep a stopped local session in the live shared registry solely to support later cleanup by name or id.

#### Scenario: Local stop returns cleanup locators before registry removal
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name reviewer`
- **AND WHEN** the target resolves through a fresh local shared-registry record with manifest authority
- **THEN** the successful stop response includes `manifest_path` and `session_root`
- **AND THEN** those fields identify the stopped session envelope that can be passed to `houmao-mgr agents cleanup`

#### Scenario: Stop does not preserve live registry solely for cleanup
- **WHEN** `houmao-mgr agents stop --agent-id agent-123` successfully stops a local tmux-backed managed session
- **THEN** the command may clear the live shared-registry record for that session
- **AND THEN** the structured response still contains the durable cleanup locators needed for follow-up cleanup

#### Scenario: Missing local manifest authority omits cleanup locators
- **WHEN** `houmao-mgr agents stop` resolves a target whose control path does not expose local manifest or session-root authority
- **THEN** the command may omit `manifest_path` and `session_root`
- **AND THEN** the response remains valid for the stop action without inventing cleanup locators
