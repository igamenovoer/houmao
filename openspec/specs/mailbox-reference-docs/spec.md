## Purpose
Define the repository's mailbox reference documentation structure, coverage, and quality bar so readers can find accurate contracts, operations guidance, and internal architecture details under a dedicated mailbox subtree.
## Requirements

### Requirement: Mailbox reference documentation is organized under a dedicated subtree
The repository SHALL publish the mailbox reference documentation under `docs/reference/mailbox/` with an `index.md` entrypoint instead of concentrating the full mailbox reference in one standalone page.

That mailbox reference subtree SHALL provide a navigational overview that directs readers to the detailed mailbox documentation pages by topic.

#### Scenario: Mailbox reference entrypoint is a navigational index
- **WHEN** a reader opens the mailbox reference entrypoint
- **THEN** the repository presents `docs/reference/mailbox/index.md`
- **AND THEN** that page explains the mailbox reference structure and links to the detailed mailbox documentation pages

#### Scenario: Top-level docs navigation reaches the mailbox subtree
- **WHEN** a reader browses the top-level docs indexes or runtime reference pages
- **THEN** those docs pages link to the mailbox reference subtree
- **AND THEN** the mailbox subtree is discoverable without requiring the reader to inspect source directories directly

### Requirement: Mailbox reference documentation separates contracts, operations, and internals
The mailbox reference subtree SHALL separate detailed mailbox documentation into distinct categories for contracts, operations, and internals.

The mailbox reference SHALL include at minimum one detailed page in each of those categories.

#### Scenario: Contracts, operations, and internals have distinct mailbox pages
- **WHEN** a reader navigates the mailbox reference subtree
- **THEN** the mailbox reference provides dedicated detailed pages for mailbox contracts, mailbox operation guidance, and mailbox internals
- **AND THEN** those detailed pages do not rely on one mixed catch-all page to explain all mailbox topics

### Requirement: Mailbox reference pages combine intuitive explanations with exact technical detail
Each detailed mailbox reference page SHALL be understandable to new users or developers while still preserving the exact technical details needed for implementation or debugging.

At minimum, each detailed mailbox page SHALL include:

- a short explanation of what the page covers,
- plain-language framing or mental-model guidance before dense technical detail,
- the relevant exact technical specifics, constraints, or contracts,
- at least one concrete example, walkthrough fragment, or representative artifact shape where it materially helps understanding.

#### Scenario: New reader can orient before reading exact contracts
- **WHEN** a first-time reader opens a detailed mailbox reference page
- **THEN** the page first explains the purpose of the topic in accessible language
- **AND THEN** the reader can build an intuitive mental model before encountering the full technical detail

#### Scenario: Developer can still find exact mailbox specifics
- **WHEN** a developer opens a detailed mailbox reference page to answer an implementation or debugging question
- **THEN** the page includes the exact mailbox constraints, contracts, or artifact details relevant to that topic
- **AND THEN** the page is not limited to high-level explanatory prose alone

### Requirement: Important mailbox procedures include embedded Mermaid sequence diagrams
When a mailbox reference page introduces an important procedure involving multiple participants or steps, the page SHALL include an embedded Mermaid `sequenceDiagram` block directly in the Markdown page.

These diagrams SHALL accompany the prose explanation rather than replace it.

Important mailbox procedures include at minimum:

- runtime mailbox bootstrap or enablement flows,
- runtime `mail` command flows where the sequence materially aids understanding,
- registration or deregistration lifecycle procedures,
- repair or recovery procedures with multi-step interaction.

#### Scenario: Procedure page includes an embedded sequence diagram
- **WHEN** a mailbox reference page introduces an important procedure
- **THEN** that page includes an embedded Mermaid `sequenceDiagram` block in the Markdown content
- **AND THEN** the diagram appears alongside the written explanation of the procedure

#### Scenario: Diagram supplements rather than replaces the written procedure
- **WHEN** a reader uses the documentation to understand an important mailbox procedure
- **THEN** the page provides both prose explanation and a Mermaid sequence diagram
- **AND THEN** the reader is not required to infer the full procedure from the diagram alone

#### Scenario: Sequence diagrams remain readable in common Markdown renderers
- **WHEN** a mailbox procedure page includes an embedded Mermaid sequence diagram
- **THEN** the diagram uses readable participant labels and concise message text suitable for inline rendering in common Markdown viewers
- **AND THEN** the page does not rely on oversized or externally linked diagrams for the main procedural flow

### Requirement: Mailbox contract documentation covers the implemented v1 mailbox surfaces
The mailbox contract documentation SHALL describe the implemented v1 mailbox surfaces that readers must follow.

At minimum, that contract coverage SHALL include:

- the canonical mailbox message and addressing model,
- runtime mailbox bindings, discoverable mailbox skill projection, and manager-owned `houmao-mgr agents mail` expectations,
- the gateway-first mailbox workflow and the `houmao-mgr agents mail resolve-live` discovery contract,
- authority-aware mailbox command outcomes that distinguish verified execution from non-authoritative TUI submission fallback,
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

#### Scenario: Contract documentation explains verified versus non-authoritative outcomes
- **WHEN** a reader needs to understand what `houmao-mgr agents mail ...` can prove
- **THEN** the mailbox contract pages explain the difference between verified manager-owned or gateway-backed execution and non-authoritative TUI submission fallback
- **AND THEN** the docs do not present TUI submission as equivalent to verified mailbox success

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
- the verification paths for non-authoritative manager fallback results,
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

#### Scenario: Operational guidance explains verification for non-authoritative fallback
- **WHEN** a reader follows a mailbox workflow that uses `houmao-mgr agents mail ...`
- **AND WHEN** that command can return `authoritative: false`
- **THEN** the mailbox operations docs explain how to verify the requested outcome through manager-owned `status` or `check`, filesystem mailbox inspection, or transport-native mailbox state
- **AND THEN** the docs do not treat submission-only fallback as self-verifying mailbox success

### Requirement: Mailbox internal documentation explains runtime integration and mutable-state architecture
The mailbox internal documentation SHALL explain how the runtime integrates mailbox support and how the filesystem transport divides immutable content from mutable state.

At minimum, that internal coverage SHALL include:

- primary runtime-owned mailbox skill projection under `skills/mailbox/...`,
- mailbox binding refresh behavior,
- mailbox-local rules and managed helper interaction points,
- SQLite responsibility boundaries,
- address-scoped locking behavior for mailbox mutation flows.

#### Scenario: Internal docs explain runtime integration
- **WHEN** a maintainer needs to understand how mailbox support is attached to runtime sessions
- **THEN** the mailbox internals pages explain the primary discoverable mailbox skill projection under `skills/mailbox/...`, the env binding model, and mailbox command integration points
- **AND THEN** the reader can relate the mailbox reference to the runtime integration code paths
- **AND THEN** the explanation gives enough plain-language framing that a developer new to the mailbox subsystem can follow the architecture

#### Scenario: Internal docs explain mutable-state and locking responsibilities
- **WHEN** a maintainer needs to understand mailbox mutation safety and state ownership
- **THEN** the mailbox internals pages explain the split between immutable canonical messages, mutable SQLite-backed mailbox state, and address-scoped locking behavior
- **AND THEN** the documentation makes clear which mailbox artifacts are authoritative for each responsibility

### Requirement: Mailbox reference pages identify the source materials they reflect
The mailbox reference documentation SHALL identify the implementation files or projected mailbox assets that each detailed page reflects.

This source mapping SHALL help keep the repo-level mailbox reference aligned with the implementation and projected mailbox materials without requiring those projected assets to become the only long-form documentation.

#### Scenario: Detailed mailbox pages point to implementation sources
- **WHEN** a reader opens a detailed mailbox reference page
- **THEN** that page identifies the relevant source files or projected mailbox asset files that define the documented behavior
- **AND THEN** future mailbox changes have a clear trace from implementation surfaces to repo-level reference docs

### Requirement: Mailbox reference pages introduce terminology clearly
The mailbox reference documentation SHALL introduce important mailbox terms clearly instead of assuming prior subsystem knowledge.

At minimum, the documentation SHALL define or explain recurring terms such as canonical messages, mailbox registrations, projections, and mailbox bindings before relying on them heavily.

#### Scenario: Reader encounters mailbox terms with enough context
- **WHEN** a new user or developer encounters mailbox-specific terminology in the mailbox reference subtree
- **THEN** the page or mailbox entrypoint explains that terminology in accessible language
- **AND THEN** the documentation does not rely on unexplained subsystem jargon as the only way to understand mailbox behavior

### Requirement: Mailbox reference documentation provides a Stalwart-first-session reader path
The mailbox reference documentation SHALL provide a clear first-session reader path for Stalwart-backed mailbox use instead of requiring readers to infer that path from filesystem-first pages or low-level contract references.

At minimum, the mailbox reference SHALL:

- make the transport choice visible from the mailbox entry path or quickstart,
- provide a dedicated Stalwart-focused operations page under the mailbox subtree,
- explain the prerequisites and Houmao-side assumptions for a Stalwart-backed session,
- explain how to start a mailbox-enabled session with the `stalwart` transport,
- explain how to verify the first session with `mail check`, `mail send`, and `mail reply`,
- explain that a live gateway mailbox facade becomes the preferred shared path when it is attached.

The Stalwart-focused guidance SHALL include at least one transport-comparison artifact such as a table that helps new readers distinguish filesystem-backed and Stalwart-backed sessions before the docs dive into detailed contracts.

#### Scenario: Reader can choose the Stalwart path from mailbox quickstart
- **WHEN** a first-time reader opens the mailbox entry path to enable mailbox support
- **THEN** the mailbox docs make the transport choice visible near the start of that path
- **AND THEN** the Stalwart path links to a dedicated page that explains the first-session flow without requiring the reader to reconstruct it from low-level contract pages

#### Scenario: Operator can follow a Stalwart-backed first session safely
- **WHEN** an operator wants to start and verify a Stalwart-backed mailbox session
- **THEN** the mailbox operations docs explain the Houmao-side prerequisites, the `stalwart` session-start flow, and the first `mail check`, `mail send`, and `mail reply` steps
- **AND THEN** the same page explains when the operator should expect shared mailbox work to prefer a live gateway mailbox facade

### Requirement: Mailbox reference documentation explains shared mailbox boundaries across runtime, gateway, and transport
The mailbox reference documentation SHALL explain the shared mailbox abstraction boundaries now that filesystem-backed and Stalwart-backed transports both exist.

At minimum, the mailbox reference SHALL explain:

- the difference between direct transport-specific mailbox behavior and the shared gateway mailbox facade,
- that shared mailbox operations are transport-neutral even when implemented by transport-specific adapters underneath,
- that `message_ref` is an opaque shared reply target rather than a filesystem-only or Stalwart-only identifier contract,
- which exact payload and schema details remain centralized in the mailbox and gateway contract pages rather than being duplicated into narrative pages.

When this boundary explanation uses summaries or comparison tables, it SHALL preserve the current implemented v1 behavior rather than describing future transport abstractions as though they were already supported.

#### Scenario: Developer can see direct versus gateway mailbox paths clearly
- **WHEN** a developer opens the mailbox reference to understand how shared mailbox operations are performed
- **THEN** the mailbox docs explain the distinction between direct transport-specific behavior and the shared gateway mailbox facade
- **AND THEN** the reader can tell which path is preferred when a live gateway is attached

#### Scenario: Mailbox docs treat shared reply references as opaque
- **WHEN** a reader uses the mailbox reference to understand reply behavior across transports
- **THEN** the docs explain that `message_ref` is an opaque shared reply target
- **AND THEN** the docs do not present filesystem-specific identifiers or Stalwart-native identifiers as the universal mailbox reply contract
