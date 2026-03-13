## ADDED Requirements

### Requirement: Agent gateway reference documentation is organized under a dedicated subtree
The repository SHALL publish the agent gateway reference documentation under `docs/reference/gateway/` with an `index.md` entrypoint instead of concentrating the full gateway reference inside broader runtime pages.

That subtree SHALL provide a navigational overview that directs readers to detailed gateway documentation pages by topic.

#### Scenario: Gateway reference entrypoint is a navigational index
- **WHEN** a reader opens the agent gateway reference entrypoint
- **THEN** the repository presents `docs/reference/gateway/index.md`
- **AND THEN** that page explains the structure of the gateway reference subtree and links to the detailed pages

#### Scenario: Top-level docs navigation reaches the gateway subtree
- **WHEN** a reader browses top-level reference indexes or broader runtime reference pages
- **THEN** those pages link to the agent gateway reference subtree
- **AND THEN** the subtree is discoverable without requiring the reader to inspect source directories directly

### Requirement: Agent gateway reference documentation separates contracts, operations, and internals
The `docs/reference/gateway/` subtree SHALL separate detailed gateway documentation into distinct categories for contracts, operations, and internals.

The gateway reference SHALL include at minimum one detailed page in each of those categories.

#### Scenario: Gateway contracts, operations, and internals have distinct pages
- **WHEN** a reader navigates the agent gateway reference subtree
- **THEN** the subtree provides dedicated detailed pages for gateway contracts, operational workflows, and internal architecture
- **AND THEN** those pages do not rely on one mixed catch-all page to explain all gateway topics

### Requirement: Agent gateway reference pages combine intuitive explanations with exact technical detail
Each detailed agent gateway reference page SHALL be understandable to first-time readers while still preserving the exact technical details needed for implementation, debugging, or maintenance.

At minimum, each detailed gateway reference page SHALL include:

- a short explanation of what the page covers,
- plain-language framing or mental-model guidance before dense technical detail,
- the relevant exact technical specifics, constraints, or contracts,
- at least one concrete example, representative payload, or artifact shape where it materially helps understanding.

#### Scenario: New reader can orient before reading exact gateway contracts
- **WHEN** a first-time reader opens a detailed agent gateway reference page
- **THEN** the page first explains the purpose of the topic in accessible language
- **AND THEN** the reader can build an intuitive mental model before encountering the full technical detail

#### Scenario: Developer can still find exact gateway specifics
- **WHEN** a developer opens a detailed agent gateway reference page to answer an implementation or debugging question
- **THEN** the page includes the exact gateway constraints, contracts, or artifact details relevant to that topic
- **AND THEN** the page is not limited to high-level explanatory prose alone

### Requirement: Important gateway procedures include embedded Mermaid sequence diagrams
When an agent gateway reference page introduces an important procedure involving multiple participants or steps, the page SHALL include an embedded Mermaid `sequenceDiagram` block directly in the Markdown page.

These diagrams SHALL accompany the prose explanation rather than replace it.

Important gateway procedures include at minimum:

- launch-time auto-attach or attach-later flows,
- request acceptance and queued execution flows,
- detach, restart, or stale-live-binding cleanup flows,
- recovery or reconciliation flows where managed-agent continuity changes the result.

#### Scenario: Procedure page includes an embedded sequence diagram
- **WHEN** a gateway reference page introduces an important gateway procedure
- **THEN** that page includes an embedded Mermaid `sequenceDiagram` block in the Markdown content
- **AND THEN** the diagram appears alongside the written explanation of the procedure

#### Scenario: Diagram supplements rather than replaces the written procedure
- **WHEN** a reader uses the documentation to understand an important gateway procedure
- **THEN** the page provides both prose explanation and a Mermaid sequence diagram
- **AND THEN** the reader is not required to infer the full procedure from the diagram alone

### Requirement: Gateway contract documentation covers the implemented v1 gateway surfaces
The agent gateway contract documentation SHALL describe the implemented v1 gateway surfaces that readers must follow.

At minimum, that contract coverage SHALL include:

- the distinction between gateway-capable and currently gateway-attached sessions,
- stable attachability metadata versus live gateway bindings,
- the strict attach contract and tmux-published environment pointers,
- desired listener versus live listener concepts,
- the implemented HTTP routes and request kinds,
- the versioned status model and current status axes,
- durable gateway state artifacts and their responsibilities,
- current validation and error semantics that are observable in the implemented v1 flow.

The gateway contract documentation SHALL reflect current implemented behavior and SHALL NOT imply unsupported live-adapter coverage or unimplemented request behavior as though it were already available.

#### Scenario: Contract documentation covers attach, status, and request surfaces
- **WHEN** a reader needs the normative gateway reference for current v1 behavior
- **THEN** the gateway contract pages describe attach metadata, live env bindings, the HTTP surface, request kinds, and the status model
- **AND THEN** the reader does not need to reconstruct those contracts only from scattered source files

#### Scenario: Contract documentation stays within implemented v1 scope
- **WHEN** a reader uses the gateway reference docs to understand supported behavior
- **THEN** the documentation makes clear the currently implemented v1 scope and boundaries
- **AND THEN** the docs do not describe future extensibility as if it were already implemented behavior

### Requirement: Gateway operational documentation covers lifecycle and operator-facing workflows
The agent gateway operational documentation SHALL explain how to work with the gateway safely in the implemented v1 flow.

At minimum, that operational guidance SHALL cover:

- launch-time auto-attach and attach-later behavior,
- detach behavior and stop-session interaction,
- status inspection and the difference between offline, unavailable, and live states,
- stale live-binding invalidation or cleanup behavior where relevant to operator workflows,
- the difference between direct runtime control and gateway-routed queued control at the level needed to operate the system correctly.

#### Scenario: Operational guidance covers gateway lifecycle actions
- **WHEN** an operator or developer needs to understand how a gateway starts, attaches, detaches, or disappears from a running session
- **THEN** the gateway operations pages explain those lifecycle actions and their observable runtime effects
- **AND THEN** the explanation is concrete enough for a new reader to follow the intended sequence safely

#### Scenario: Operational guidance explains gateway-capable versus live-gateway states
- **WHEN** a reader needs to understand why a session is gateway-capable but not currently attached to a live gateway
- **THEN** the gateway operations pages explain the distinction between stable attachability and live bindings
- **AND THEN** the reader can tell which gateway-aware actions require a live attached instance

### Requirement: Gateway internal documentation explains queueing, epochs, and recovery boundaries
The agent gateway internal documentation SHALL explain how the gateway sidecar persists state, serializes work, and behaves when managed-agent continuity changes.

At minimum, that internal coverage SHALL include:

- the durable queue and event-log model,
- current-instance state and epoch tracking,
- queue admission and single active execution behavior,
- restart recovery for previously accepted work,
- replay blocking or reconciliation behavior when the managed-agent instance changes,
- the separation between gateway-local health and managed-agent availability,
- the current live-adapter boundary in v1.

#### Scenario: Internal docs explain queueing and current-instance state
- **WHEN** a maintainer needs to understand how gateway-managed work is accepted, persisted, and executed
- **THEN** the gateway internals pages explain the durable queue, current-instance state, and active execution model
- **AND THEN** the reader can relate those docs to the gateway implementation without reverse-engineering the queue behavior from code alone

#### Scenario: Internal docs explain recovery and replay boundaries
- **WHEN** a maintainer needs to understand how gateway behavior changes across restart, managed-agent outage, or managed-agent epoch change
- **THEN** the gateway internals pages explain the recovery, reconciliation, and replay-blocking boundaries in the implemented v1 flow
- **AND THEN** the documentation makes clear why gateway-local health and managed-agent availability are reported separately

### Requirement: Agent gateway reference pages identify the source materials they reflect
The agent gateway reference documentation SHALL identify the implementation files or tests that each detailed page reflects.

This source mapping SHALL help keep the repo-level gateway reference aligned with the implementation and behavior-defining tests without forcing readers to use the source files as the only long-form documentation.

#### Scenario: Detailed gateway pages point to implementation sources
- **WHEN** a reader opens a detailed agent gateway reference page
- **THEN** that page identifies the relevant source files or tests that define the documented behavior
- **AND THEN** future gateway changes have a clear trace from implementation surfaces to repo-level reference docs

### Requirement: Agent gateway reference pages introduce terminology clearly
The agent gateway reference documentation SHALL introduce important subsystem terms clearly instead of assuming prior knowledge.

At minimum, the documentation SHALL define or explain recurring terms such as gateway-capable session, live gateway bindings, attach contract, request admission, managed-agent epoch, reconciliation, and not-attached state before relying on them heavily.

#### Scenario: Reader encounters gateway terms with enough context
- **WHEN** a new user or developer encounters gateway-specific terminology in the reference subtree
- **THEN** the page or subtree entrypoint explains that terminology in accessible language
- **AND THEN** the documentation does not rely on unexplained gateway jargon as the only way to understand gateway behavior
