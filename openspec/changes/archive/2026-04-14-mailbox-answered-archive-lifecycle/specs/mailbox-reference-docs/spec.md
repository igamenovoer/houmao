## MODIFIED Requirements

### Requirement: Mailbox operation documentation covers common workflows and lifecycle handling
The mailbox operation documentation SHALL explain how to work with the mailbox system safely in the implemented v1 flow, including the preferred local serverless late-registration workflow and the manager-owned resolver-first discovery path for current mailbox state.

At minimum, that operational guidance SHALL cover:

- the local serverless workflow of `houmao-mgr mailbox init`, `houmao-mgr agents launch` or `join`, `houmao-mgr agents mailbox register`, and `houmao-mgr agents mail`,
- mailbox list, peek, read, send, post, reply, mark, move, and archive workflows,
- the mailbox lifecycle distinction between read, answered, archived, and open inbox work,
- the discoverable mailbox skill surface used by runtime-owned mailbox work in current sessions,
- address-routed registration lifecycle modes,
- repair or recovery expectations for mailbox roots,
- the supported use of `houmao-mgr agents mail resolve-live` to obtain current mailbox bindings and any live `gateway.base_url` for attached `/v1/mail/*` work instead of ad hoc host or port rediscovery,
- the ordinary agent workflow of gateway HTTP when a live gateway is available and `houmao-mgr agents mail ...` when it is not,
- the verification paths for non-authoritative manager fallback results,
- the role of shared filesystem mailbox `rules/` as markdown policy guidance rather than the ordinary execution protocol.

The mailbox operation documentation SHALL NOT require mailbox-specific shell export or mailbox-specific `AGENTSYS_MAILBOX_*` env inspection as part of the ordinary workflow for current mailbox work.

#### Scenario: Operational guidance covers runtime mailbox workflows
- **WHEN** an operator or developer needs to use the mailbox system in practice
- **THEN** the mailbox operations pages explain mailbox enablement, bootstrap expectations, the discoverable mailbox skill surface, and common list, peek, read, send, reply, mark, move, and archive workflows
- **AND THEN** those pages explain the supported gateway-first, `houmao-mgr agents mail` fallback workflow clearly enough for a new reader to follow safely
- **AND THEN** important workflows are accompanied by embedded Mermaid sequence diagrams

#### Scenario: Operator can follow the preferred late-registration workflow
- **WHEN** a reader wants to enable mailbox support for a local managed agent
- **THEN** the mailbox operations docs show the preferred sequence of mailbox-root setup, agent launch or join, mailbox registration, and mailbox follow-up
- **AND THEN** the workflow does not require launch-time mailbox flags as the primary local serverless path

#### Scenario: Reader resolves current mailbox state through the manager-owned helper
- **WHEN** a reader needs the current mailbox binding set or the exact live gateway mail endpoint for attached shared-mailbox work
- **THEN** the mailbox operations docs direct the reader to `houmao-mgr agents mail resolve-live`
- **AND THEN** the docs explain that the returned `gateway.base_url` is the supported discovery path instead of ad hoc live host or port guessing

#### Scenario: Operational guidance explains verification for non-authoritative fallback
- **WHEN** a reader follows a mailbox workflow that uses `houmao-mgr agents mail ...`
- **AND WHEN** that command can return `authoritative: false`
- **THEN** the mailbox operations docs explain how to verify the requested outcome through manager-owned status or mailbox list/read state, filesystem mailbox inspection, or transport-native mailbox state
- **AND THEN** the docs do not treat submission-only fallback as self-verifying mailbox success

#### Scenario: Reader understands archive as completion
- **WHEN** a reader follows mailbox workflow documentation for processed mail
- **THEN** the docs describe archive as the normal completion action
- **AND THEN** they do not describe read state alone as closing the requested work
