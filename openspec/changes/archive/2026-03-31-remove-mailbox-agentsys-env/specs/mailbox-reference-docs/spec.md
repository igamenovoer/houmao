## MODIFIED Requirements

### Requirement: Mailbox contract documentation covers the implemented v1 mailbox surfaces
The mailbox contract documentation SHALL describe the implemented v1 mailbox surfaces that readers must follow.

At minimum, that contract coverage SHALL include:

- the canonical mailbox message and addressing model,
- the durable manifest-backed mailbox binding, discoverable mailbox skill projection, and manager-owned `houmao-mgr agents mail` expectations,
- the gateway-first mailbox workflow and the `houmao-mgr agents mail resolve-live` discovery contract,
- authority-aware mailbox command outcomes that distinguish verified execution from non-authoritative TUI submission fallback,
- the filesystem mailbox layout and artifact contract,
- the policy-oriented role of shared filesystem mailbox `rules/`.

Compatibility helper scripts under `rules/scripts/`, when still published, SHALL be documented as compatibility or implementation detail rather than as the primary ordinary workflow contract.

The mailbox contract documentation SHALL NOT present mailbox-specific `AGENTSYS_MAILBOX_*` env bindings as part of the supported v1 mailbox contract for ordinary mailbox work.

#### Scenario: Contract documentation covers canonical and runtime mailbox surfaces
- **WHEN** a reader needs the normative mailbox reference for v1 behavior
- **THEN** the mailbox contract pages describe the canonical message model, addressing, threading, the durable mailbox binding model, the primary discoverable mailbox skill surface, and the `houmao-mgr agents mail` command surface
- **AND THEN** the reader does not need to reconstruct those contracts only from scattered source files
- **AND THEN** the pages use examples or representative shapes to make those contracts easier to understand

#### Scenario: Contract documentation treats helper scripts as compatibility detail
- **WHEN** a reader needs to understand mailbox-local compatibility helpers and filesystem storage contracts
- **THEN** the mailbox contract pages explain the filesystem layout and durable artifacts first
- **AND THEN** any documented `rules/scripts/` helpers are presented as compatibility or implementation detail instead of as the ordinary mailbox workflow contract

#### Scenario: Contract documentation explains verified versus non-authoritative outcomes
- **WHEN** a reader needs to understand what `houmao-mgr agents mail ...` can prove
- **THEN** the mailbox contract pages explain the difference between verified manager-owned or gateway-backed execution and non-authoritative TUI submission fallback
- **AND THEN** the docs do not present TUI submission as equivalent to verified mailbox success

### Requirement: Mailbox operation documentation covers common workflows and lifecycle handling
The mailbox operation documentation SHALL explain how to work with the mailbox system safely in the implemented v1 flow, including the preferred local serverless late-registration workflow and the manager-owned resolver-first discovery path for current mailbox state.

At minimum, that operational guidance SHALL cover:

- the local serverless workflow of `houmao-mgr mailbox init`, `houmao-mgr agents launch` or `join`, `houmao-mgr agents mailbox register`, and `houmao-mgr agents mail`,
- mailbox read, send, reply, and explicit mark-read workflows,
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
- **THEN** the mailbox operations pages explain mailbox enablement, bootstrap expectations, the discoverable mailbox skill surface, and common read, send, reply, and mark-read workflows
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
- **THEN** the mailbox operations docs explain how to verify the requested outcome through manager-owned `status` or `check`, filesystem mailbox inspection, or transport-native mailbox state
- **AND THEN** the docs do not treat submission-only fallback as self-verifying mailbox success

### Requirement: Mailbox internal documentation explains runtime integration and mutable-state architecture
The mailbox internal documentation SHALL explain how the runtime integrates mailbox support and how the filesystem transport divides immutable content from mutable state.

At minimum, that internal coverage SHALL include:

- primary runtime-owned mailbox skill projection under `skills/mailbox/...`,
- durable manifest-backed mailbox binding and current-mailbox resolution behavior,
- mailbox-local rules and managed helper interaction points,
- SQLite responsibility boundaries,
- address-scoped locking behavior for mailbox mutation flows.

#### Scenario: Internal docs explain runtime integration
- **WHEN** a maintainer needs to understand how mailbox support is attached to runtime sessions
- **THEN** the mailbox internals pages explain the primary discoverable mailbox skill projection under `skills/mailbox/...`, the manifest-backed mailbox binding model, and mailbox command integration points
- **AND THEN** the reader can relate the mailbox reference to the runtime integration code paths
- **AND THEN** the explanation gives enough plain-language framing that a developer new to the mailbox subsystem can follow the architecture

#### Scenario: Internal docs explain mutable-state and locking responsibilities
- **WHEN** a maintainer needs to understand mailbox mutation safety and state ownership
- **THEN** the mailbox internals pages explain the split between immutable canonical messages, mutable SQLite-backed mailbox state, and address-scoped locking behavior
- **AND THEN** the documentation makes clear which mailbox artifacts are authoritative for each responsibility
