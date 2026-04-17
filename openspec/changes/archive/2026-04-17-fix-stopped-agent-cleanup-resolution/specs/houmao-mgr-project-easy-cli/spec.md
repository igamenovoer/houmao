## ADDED Requirements

### Requirement: Easy instance stop preserves managed-agent cleanup locators
`houmao-mgr project easy instance stop --name <name>` SHALL preserve durable cleanup locator fields from the underlying managed-agent stop result when they are available.

At minimum, the successful easy-instance stop output SHALL include:

- `manifest_path`
- `session_root`

The command SHALL continue validating that the target belongs to the selected project overlay before stopping it. After stop, the emitted locator fields SHALL let the operator run `houmao-mgr agents cleanup session|logs|mailbox --manifest-path <path>` or `--session-root <path>` without relying on a live shared-registry record.

#### Scenario: Easy instance stop returns cleanup locators
- **WHEN** an operator runs `houmao-mgr project easy instance stop --name reviewer`
- **AND WHEN** the selected managed agent belongs to the active project overlay
- **AND WHEN** the underlying stop result exposes `manifest_path` and `session_root`
- **THEN** the easy-instance stop output includes those locator fields
- **AND THEN** the output still includes the selected project overlay metadata

#### Scenario: Easy instance stop keeps overlay validation before stop
- **WHEN** an operator runs `houmao-mgr project easy instance stop --name reviewer`
- **AND WHEN** the resolved managed agent manifest does not belong to the selected project overlay
- **THEN** the command fails before stopping the target
- **AND THEN** it does not emit cleanup locators for an unrelated managed session
