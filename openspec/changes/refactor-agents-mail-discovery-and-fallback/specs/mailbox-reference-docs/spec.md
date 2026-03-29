## MODIFIED Requirements

### Requirement: Mailbox contract documentation covers the implemented v1 mailbox surfaces
The mailbox contract documentation SHALL describe the implemented v1 mailbox surfaces that readers must follow.

At minimum, that contract coverage SHALL include:

- the canonical mailbox message and addressing model,
- runtime mailbox bindings, discoverable mailbox skill projection, and manager-owned `houmao-mgr agents mail` expectations,
- the gateway-first mailbox workflow and the `houmao-mgr agents mail resolve-live` discovery contract,
- the filesystem mailbox layout and artifact contract,
- the policy-oriented role of shared filesystem mailbox `rules/`.

Compatibility helper scripts under `rules/scripts/`, when still published, SHALL be documented as compatibility or implementation detail rather than as the primary ordinary workflow contract.

#### Scenario: Contract documentation covers canonical and runtime mailbox surfaces
- **WHEN** a reader needs the normative mailbox reference for v1 behavior
- **THEN** the mailbox contract pages describe the canonical message model, addressing, threading, runtime mailbox bindings, the primary discoverable mailbox skill surface, and the `houmao-mgr agents mail` command surface
- **AND THEN** the reader does not need to reconstruct those contracts only from scattered source files
- **AND THEN** the pages use examples or representative shapes to make those contracts easier to understand

#### Scenario: Contract documentation treats helper scripts as compatibility detail
- **WHEN** a reader needs to understand mailbox-local compatibility helpers and filesystem storage contracts
- **THEN** the mailbox contract pages explain the filesystem layout and durable artifacts first
- **AND THEN** any documented `rules/scripts/` helpers are presented as compatibility or implementation detail instead of as the ordinary mailbox workflow contract

### Requirement: Mailbox operation documentation covers common workflows and lifecycle handling
The mailbox operation documentation SHALL explain how to work with the mailbox system safely in the implemented v1 flow, including the preferred local serverless late-registration workflow and the manager-owned live-binding discovery path.

At minimum, that operational guidance SHALL cover:

- the local serverless workflow of `houmao-mgr mailbox init`, `houmao-mgr agents launch` or `join`, `houmao-mgr agents mailbox register`, and `houmao-mgr agents mail`,
- mailbox read, send, reply, and explicit mark-read workflows,
- the discoverable mailbox skill surface used by runtime-owned mailbox work in current sessions,
- address-routed registration lifecycle modes,
- repair or recovery expectations for mailbox roots,
- the supported use of `houmao-mgr agents mail resolve-live` to obtain current bindings and any live `gateway.base_url` for attached `/v1/mail/*` work instead of ad hoc host or port rediscovery,
- the ordinary agent workflow of gateway HTTP when a live gateway is available and `houmao-mgr agents mail ...` when it is not,
- the role of shared filesystem mailbox `rules/` as markdown policy guidance rather than the ordinary execution protocol.

#### Scenario: Operational guidance covers runtime mailbox workflows
- **WHEN** an operator or developer needs to use the mailbox system in practice
- **THEN** the mailbox operations pages explain mailbox enablement, bootstrap expectations, the discoverable mailbox skill surface, and common read, send, reply, and mark-read workflows
- **AND THEN** those pages explain the supported gateway-first, `houmao-mgr agents mail` fallback workflow clearly enough for a new reader to follow safely
- **AND THEN** important workflows are accompanied by embedded Mermaid sequence diagrams

#### Scenario: Operator can follow the preferred late-registration workflow
- **WHEN** a reader wants to enable mailbox support for a local managed agent
- **THEN** the mailbox operations docs show the preferred sequence of mailbox-root setup, agent launch or join, mailbox registration, and mailbox follow-up
- **AND THEN** the workflow does not require launch-time mailbox flags as the primary local serverless path

#### Scenario: Reader resolves live mailbox bindings through the manager-owned helper
- **WHEN** a reader needs the current mailbox binding set or the exact live gateway mail endpoint for attached shared-mailbox work
- **THEN** the mailbox operations docs direct the reader to `houmao-mgr agents mail resolve-live`
- **AND THEN** the docs explain that the returned `gateway.base_url` is the supported discovery path instead of ad hoc live host or port guessing
