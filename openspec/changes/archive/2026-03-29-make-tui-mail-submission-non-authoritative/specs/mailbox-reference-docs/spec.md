## MODIFIED Requirements

### Requirement: Mailbox operation documentation covers common workflows and lifecycle handling
The mailbox operation documentation SHALL explain how to work with the mailbox system safely in the implemented v1 flow, including the preferred local serverless late-registration workflow and the runtime-owned live-binding discovery path.

At minimum, that operational guidance SHALL cover:

- the local serverless workflow of `houmao-mgr mailbox init`, `houmao-mgr agents launch` or `join`, `houmao-mgr agents mailbox register`, and `houmao-mgr agents mail`,
- mailbox read, send, and reply workflows,
- the discoverable mailbox skill surface used by runtime-owned mailbox work in current sessions,
- address-routed registration lifecycle modes,
- repair or recovery expectations for mailbox roots,
- the supported use of `pixi run python -m houmao.agents.mailbox_runtime_support resolve-live` to obtain current bindings and any live `gateway.base_url` for attached `/v1/mail/*` work instead of ad hoc host or port rediscovery,
- the distinction between authoritative manager-owned execution results and non-authoritative TUI-mediated submission results,
- the supported verification paths when a mailbox request was submitted through a TUI-mediated flow.

The docs SHALL explain that exact TUI reply-schema recovery is not the supported correctness boundary for `houmao-mgr` mailbox operations.

The docs SHALL direct readers to verify mailbox effects through manager-owned follow-up or protocol-owned state rather than by treating transcript parsing alone as mailbox truth.

#### Scenario: Operational guidance covers runtime mailbox workflows
- **WHEN** an operator or developer needs to use the mailbox system in practice
- **THEN** the mailbox operations pages explain mailbox enablement, bootstrap expectations, the discoverable mailbox skill surface, and common read, send, and reply workflows
- **AND THEN** those pages direct the reader to the managed mailbox rules and helper expectations where relevant
- **AND THEN** those workflows are explained with enough concrete detail that a new reader can follow the intended sequence safely
- **AND THEN** important workflows are accompanied by embedded Mermaid sequence diagrams

#### Scenario: Operator can follow the preferred late-registration workflow
- **WHEN** a reader wants to enable mailbox support for a local managed agent
- **THEN** the mailbox operations docs show the preferred sequence of mailbox-root setup, agent launch or join, mailbox registration, and `agents mail` follow-up
- **AND THEN** the workflow does not require launch-time mailbox flags as the primary local serverless path

#### Scenario: Docs explain non-authoritative TUI submission results clearly
- **WHEN** a reader uses mailbox docs for a `houmao-mgr` workflow that may fall back to TUI-mediated execution
- **THEN** the docs explain that the command may return submitted, rejected, interrupted, or TUI-error state without claiming mailbox success from transcript parsing
- **AND THEN** the docs identify follow-up verification paths such as mailbox status/check, project mailbox inspection, or transport-native verification

#### Scenario: Reader resolves live mailbox bindings through the runtime-owned helper
- **WHEN** a reader needs the current mailbox binding set or the exact live gateway mail endpoint for attached shared-mailbox work
- **THEN** the mailbox operations docs direct the reader to `resolve-live`
- **AND THEN** the docs explain that the returned `gateway.base_url` is the supported discovery path instead of ad hoc live host or port guessing

#### Scenario: Operational guidance covers lifecycle and recovery
- **WHEN** an operator or developer needs to understand mailbox joins, leaves, or repair behavior
- **THEN** the mailbox operations pages explain registration lifecycle modes and repair or recovery expectations
- **AND THEN** the documentation reflects the implemented address-routed v1 lifecycle rather than the earlier principal-keyed layout
