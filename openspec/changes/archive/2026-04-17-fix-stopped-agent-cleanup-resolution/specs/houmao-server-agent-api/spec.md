## ADDED Requirements

### Requirement: Managed-agent API stop responses include durable cleanup locators
When `POST /houmao/agents/{agent_ref}/stop` successfully stops a managed agent whose resolved authority exposes local manifest and session-root metadata, the response SHALL include durable cleanup locator fields.

At minimum, the successful response SHALL include:

- `manifest_path`
- `session_root`

The route SHALL capture these values before deleting in-memory headless authority, clearing shared-registry records, or removing pair-managed tracking records that would otherwise make the stopped session harder to locate.

If a managed-agent stop target does not expose local manifest or session-root metadata, the route MAY omit the locator fields rather than fabricating them.

#### Scenario: Headless managed-agent stop returns cleanup locators
- **WHEN** a caller submits `POST /houmao/agents/agent-123/stop` for a managed headless agent
- **AND WHEN** the server authority record contains manifest and session-root metadata
- **THEN** the successful response includes `manifest_path` and `session_root`
- **AND THEN** those fields identify the stopped runtime session envelope for later cleanup

#### Scenario: TUI managed-agent stop returns cleanup locators when known
- **WHEN** a caller submits `POST /houmao/agents/reviewer/stop` for a TUI-backed managed agent
- **AND WHEN** the server's tracked identity includes manifest and session-root metadata
- **THEN** the successful response includes `manifest_path` and `session_root`
- **AND THEN** the caller does not need to query the live registry again after stop to discover the cleanup target

#### Scenario: Stop response omits unavailable cleanup locators
- **WHEN** a caller submits `POST /houmao/agents/external/stop`
- **AND WHEN** the resolved stop target has no local manifest or session-root metadata
- **THEN** the successful response may omit `manifest_path` and `session_root`
- **AND THEN** the API does not invent path values that are not known to the resolved authority
