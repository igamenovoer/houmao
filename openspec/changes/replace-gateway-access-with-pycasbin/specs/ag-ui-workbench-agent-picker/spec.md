# Spec Delta

## ADDED Requirements

### Requirement: The Picker Uses Verified Targets for Signed Access

The local server SHALL resolve a discovered agent through an operator-approved endpoint source for signed requests. The server SHALL select the signer using the verified target identity and configured binding. Cached pane URLs and operator-pane labels SHALL convey no signing authority.

#### Scenario: The operator changes a discovered pane to a manual URL

- **WHEN** an operator edits the displayed AG-UI URL and the pane switches to manual targeting
- **THEN** the workbench discards that pane's inherited signer binding
- **AND THEN** protected signing for a manual destination requires an explicitly approved server-side binding
