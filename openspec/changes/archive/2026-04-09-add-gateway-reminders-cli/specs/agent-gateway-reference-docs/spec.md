## ADDED Requirements

### Requirement: Gateway reminder reference docs cover CLI, proxy, and direct reminder surfaces together
The agent gateway reference documentation SHALL explain gateway reminders through three aligned operator layers:

- `houmao-mgr agents gateway reminders ...` as the preferred operator-facing CLI surface,
- managed-agent `/houmao/agents/{agent_ref}/gateway/reminders...` routes as the pair-managed proxy surface,
- direct `/v1/reminders` routes as the lower-level live gateway contract.

The gateway reminder docs SHALL explain when each layer is appropriate, and SHALL make clear that the CLI and pair-managed proxy surfaces are wrappers over the same underlying live reminder model.

At minimum, the reminder reference docs SHALL explain:

- that ranking remains numeric even when the CLI offers prepend and append placement flags,
- that `--before-all` and `--after-all` are convenience placement modes rather than new gateway ranking semantics,
- that direct `/v1/reminders` remains useful for exact contract inspection and debugging,
- that pair-managed reminder operations do not require the operator to discover the live gateway listener directly.

#### Scenario: Reader learns the CLI-first reminder workflow from the gateway reference
- **WHEN** a reader opens the gateway reminder operations page to learn how to create or inspect reminders
- **THEN** the page introduces `houmao-mgr agents gateway reminders ...` as the preferred operator surface
- **AND THEN** the page does not present direct `/v1/reminders` HTTP as the only supported way to work with reminders

#### Scenario: Maintainer can still find the underlying direct reminder contract
- **WHEN** a maintainer opens the gateway reminder operations page to inspect payload and route semantics
- **THEN** the page still points them to the exact `/v1/reminders` contract and representative payloads
- **AND THEN** the page explains how the higher-level CLI and pair-managed proxy surfaces map onto that lower-level contract
