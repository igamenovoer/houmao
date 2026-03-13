## ADDED Requirements

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
- runtime mailbox bindings and runtime `mail` command expectations,
- managed mailbox helper script contract,
- filesystem mailbox layout and artifact contract.

#### Scenario: Contract documentation covers canonical and runtime mailbox surfaces
- **WHEN** a reader needs the normative mailbox reference for v1 behavior
- **THEN** the mailbox contract pages describe the canonical message model, addressing, threading, runtime mailbox bindings, and runtime `mail` command surface
- **AND THEN** the reader does not need to reconstruct those contracts only from scattered source files
- **AND THEN** the pages use examples or representative shapes to make those contracts easier to understand

#### Scenario: Contract documentation covers managed helpers and filesystem layout
- **WHEN** a reader needs to understand the mailbox-local helper and storage contracts
- **THEN** the mailbox contract pages describe the managed helper invocation and result contract plus the filesystem mailbox layout and durable artifacts
- **AND THEN** the documentation reflects the implemented v1 mailbox transport rather than an abstract future transport

### Requirement: Mailbox operation documentation covers common workflows and lifecycle handling
The mailbox operation documentation SHALL explain how to work with the mailbox system safely in the implemented v1 flow.

At minimum, that operational guidance SHALL cover:

- mailbox enablement and bootstrap expectations,
- mailbox read, send, and reply workflows,
- address-routed registration lifecycle modes,
- repair or recovery expectations for mailbox roots.

#### Scenario: Operational guidance covers runtime mailbox workflows
- **WHEN** an operator or developer needs to use the mailbox system in practice
- **THEN** the mailbox operations pages explain mailbox enablement, bootstrap expectations, and common read, send, and reply workflows
- **AND THEN** those pages direct the reader to the managed mailbox rules and helper expectations where relevant
- **AND THEN** those workflows are explained with enough concrete detail that a new reader can follow the intended sequence safely
- **AND THEN** important workflows are accompanied by embedded Mermaid sequence diagrams

#### Scenario: Operational guidance covers lifecycle and recovery
- **WHEN** an operator or developer needs to understand mailbox joins, leaves, or repair behavior
- **THEN** the mailbox operations pages explain registration lifecycle modes and repair or recovery expectations
- **AND THEN** the documentation reflects the implemented address-routed v1 lifecycle rather than the earlier principal-keyed layout

### Requirement: Mailbox internal documentation explains runtime integration and mutable-state architecture
The mailbox internal documentation SHALL explain how the runtime integrates mailbox support and how the filesystem transport divides immutable content from mutable state.

At minimum, that internal coverage SHALL include:

- runtime-owned mailbox skill projection and binding refresh behavior,
- mailbox-local rules and managed helper interaction points,
- SQLite responsibility boundaries,
- address-scoped locking behavior for mailbox mutation flows.

#### Scenario: Internal docs explain runtime integration
- **WHEN** a maintainer needs to understand how mailbox support is attached to runtime sessions
- **THEN** the mailbox internals pages explain the runtime-owned mailbox skill projection, env binding model, and mailbox command integration points
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
