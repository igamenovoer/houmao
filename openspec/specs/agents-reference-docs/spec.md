# agents-reference-docs Specification

## Purpose
Define the structure, coverage, and quality bar for runtime-managed agent reference documentation in the repository.

## Requirements

### Requirement: Runtime-managed agent reference documentation is organized under a dedicated subtree
The repository SHALL publish the runtime-managed agent reference documentation under `docs/reference/agents/` with an `index.md` entrypoint instead of concentrating the full reference in broad standalone runtime pages.

That subtree SHALL provide a navigational overview that directs readers to detailed runtime-managed agent documentation pages by topic.

#### Scenario: Agent reference entrypoint is a navigational index
- **WHEN** a reader opens the runtime-managed agent reference entrypoint
- **THEN** the repository presents `docs/reference/agents/index.md`
- **AND THEN** that page explains the structure of the agent reference subtree and links to the detailed pages

#### Scenario: Top-level docs navigation reaches the agent subtree
- **WHEN** a reader browses top-level reference indexes or broader runtime reference pages
- **THEN** those pages link to the runtime-managed agent reference subtree
- **AND THEN** the subtree is discoverable without requiring the reader to inspect source directories directly

### Requirement: Runtime-managed agent reference documentation separates contracts, operations, and internals
The `docs/reference/agents/` subtree SHALL separate detailed runtime-managed agent documentation into distinct categories for contracts, operations, and internals.

The agent reference SHALL include at minimum one detailed page in each of those categories.

#### Scenario: Agent contracts, operations, and internals have distinct pages
- **WHEN** a reader navigates the runtime-managed agent reference subtree
- **THEN** the subtree provides dedicated detailed pages for runtime-managed agent contracts, operational workflows, and internal architecture
- **AND THEN** those pages do not rely on one mixed catch-all page to explain all runtime-managed agent topics

### Requirement: Runtime-managed agent reference pages combine intuitive explanations with exact technical detail
Each detailed runtime-managed agent reference page SHALL be understandable to first-time readers while still preserving the exact technical details needed for implementation, debugging, or maintenance.

At minimum, each detailed agent reference page SHALL include:

- a short explanation of what the page covers,
- plain-language framing or mental-model guidance before dense technical detail,
- the relevant exact technical specifics, constraints, or contracts,
- at least one concrete example, walkthrough fragment, or representative artifact shape where it materially helps understanding.

#### Scenario: New reader can orient before reading exact runtime details
- **WHEN** a first-time reader opens a detailed runtime-managed agent reference page
- **THEN** the page first explains the purpose of the topic in accessible language
- **AND THEN** the reader can build an intuitive mental model before encountering the full technical detail

#### Scenario: Developer can still find exact runtime specifics
- **WHEN** a developer opens a detailed runtime-managed agent reference page to answer an implementation or debugging question
- **THEN** the page includes the exact runtime-managed agent constraints, contracts, or artifact details relevant to that topic
- **AND THEN** the page is not limited to high-level explanatory prose alone

### Requirement: Important runtime-managed agent procedures include embedded Mermaid sequence diagrams
When a runtime-managed agent reference page introduces an important procedure involving multiple participants or steps, the page SHALL include an embedded Mermaid `sequenceDiagram` block directly in the Markdown page.

These diagrams SHALL accompany the prose explanation rather than replace it.

Important runtime-managed agent procedures include at minimum:

- session start, resume, or stop flows where the sequence materially aids understanding,
- message-passing workflows where the runtime, backend, and optional subsystems interact,
- session-targeting or resolution workflows when manifest-path and tmux-name control paths differ materially.

#### Scenario: Procedure page includes an embedded sequence diagram
- **WHEN** a runtime-managed agent reference page introduces an important procedure
- **THEN** that page includes an embedded Mermaid `sequenceDiagram` block in the Markdown content
- **AND THEN** the diagram appears alongside the written explanation of the procedure

#### Scenario: Diagram supplements rather than replaces the written procedure
- **WHEN** a reader uses the documentation to understand an important runtime-managed agent procedure
- **THEN** the page provides both prose explanation and a Mermaid sequence diagram
- **AND THEN** the reader is not required to infer the full procedure from the diagram alone

### Requirement: Agent contract documentation covers the implemented runtime-managed public surfaces
The runtime-managed agent contract documentation SHALL describe the implemented public surfaces that readers must follow when working with runtime-owned sessions.

At minimum, that contract coverage SHALL include:

- session identity and targeting behavior, including manifest-path versus name-based tmux control,
- the main runtime-managed control surfaces and when each is intended to be used,
- session manifest and runtime-owned storage concepts relevant to public control,
- runtime-managed discovery or environment bindings relevant to session control,
- the relationship between runtime-managed direct control and optional gateway-aware control without duplicating gateway-only contract detail.

#### Scenario: Reader can compare runtime-managed control surfaces
- **WHEN** a reader needs to choose between direct prompt turns, raw control input, mailbox-driven prompt requests, or gateway-aware control
- **THEN** the agent contract docs explain the purpose and boundary of each runtime-managed interaction path
- **AND THEN** the reader can tell which surfaces are direct, which are queued, and which depend on optional subsystems

#### Scenario: Reader can understand session targeting behavior
- **WHEN** a reader needs to target a runtime-managed session by manifest path or tmux name
- **THEN** the agent contract docs explain the identity-resolution model and relevant persisted or tmux-published pointers
- **AND THEN** the reader does not need to infer those control rules only from CLI source code

### Requirement: Agent operational documentation covers session lifecycle and message-passing modes
The runtime-managed agent operational documentation SHALL explain how runtime-owned sessions behave across lifecycle actions and message-passing paths.

At minimum, that operational guidance SHALL cover:

- session start, resume, and stop expectations,
- how gateway capability publication fits into the runtime-owned session lifecycle,
- how message passing differs across direct prompt turns, raw control input, mailbox prompt flows, and gateway-routed requests at the level needed to understand runtime-managed behavior,
- which flows are synchronous versus queued versus delegated to another subsystem.

#### Scenario: Operational guidance covers runtime-managed session lifecycle
- **WHEN** an operator or developer needs to understand what the runtime does during session start, resume, or stop
- **THEN** the agent operations pages explain the major lifecycle stages and their runtime-owned artifacts or side effects
- **AND THEN** the explanation is concrete enough for a new reader to follow the intended sequence safely

#### Scenario: Operational guidance explains message-passing mode differences
- **WHEN** a reader needs to understand how prompt delivery or control input moves through different runtime-managed paths
- **THEN** the agent operations pages explain the behavioral difference between direct prompt turns, raw control input, mailbox prompt flows, and gateway-routed requests
- **AND THEN** the docs make clear which path waits for turn completion, which path sends raw control input, and which path relies on optional queued or delegated handling

### Requirement: Agent internal documentation explains runtime state management and recovery boundaries
The runtime-managed agent internal documentation SHALL explain how the runtime persists session state, publishes discovery metadata, and defines recovery or failure boundaries.

At minimum, that internal coverage SHALL include:

- runtime root and session-root layout relevant to runtime-managed sessions,
- manifest persistence and the split between runtime-owned and backend-owned state,
- tmux environment publication relevant to runtime-managed session discovery,
- stop or cleanup boundaries and stale pointer or binding cleanup behavior where documented in the current implementation,
- runtime error or recovery boundaries at the level needed to understand what the runtime owns versus what it delegates.

#### Scenario: Internal docs explain runtime-owned state responsibilities
- **WHEN** a maintainer needs to understand where runtime-managed session state lives and which artifacts are authoritative
- **THEN** the agent internals pages explain the runtime-owned storage layout, manifest persistence rules, and discovery publication model
- **AND THEN** the reader can relate those docs to the runtime implementation without reverse-engineering the storage model from code alone

#### Scenario: Internal docs explain recovery and failure boundaries
- **WHEN** a maintainer needs to understand how runtime-managed sessions behave around stale bindings, stop flows, or recovery boundaries
- **THEN** the agent internals pages explain the relevant runtime-owned cleanup or recovery expectations
- **AND THEN** the documentation makes clear which failures are handled by the runtime versus by an optional subsystem or backend

### Requirement: Runtime-managed agent reference pages identify the source materials they reflect
The runtime-managed agent reference documentation SHALL identify the implementation files or tests that each detailed page reflects.

This source mapping SHALL help keep the repo-level reference aligned with the implementation and behavior-defining tests without forcing readers to use the source files as the only long-form documentation.

#### Scenario: Detailed agent pages point to implementation sources
- **WHEN** a reader opens a detailed runtime-managed agent reference page
- **THEN** that page identifies the relevant source files or tests that define the documented behavior
- **AND THEN** future runtime changes have a clear trace from implementation surfaces to repo-level reference docs

### Requirement: Runtime-managed agent reference pages introduce terminology clearly
The runtime-managed agent reference documentation SHALL introduce important subsystem terms clearly instead of assuming prior knowledge.

At minimum, the documentation SHALL define or explain recurring terms such as runtime-managed session, session manifest, session root, direct control, queued control, and runtime-owned state before relying on them heavily.

#### Scenario: Reader encounters agent terms with enough context
- **WHEN** a new user or developer encounters runtime-managed agent terminology in the reference subtree
- **THEN** the page or subtree entrypoint explains that terminology in accessible language
- **AND THEN** the documentation does not rely on unexplained runtime jargon as the only way to understand agent behavior
