# registry-reference-docs Specification

## Purpose
TBD - created by archiving change add-shared-registry-reference-docs. Update Purpose after archive.
## Requirements
### Requirement: Shared-registry reference documentation is organized under a dedicated subtree
The repository SHALL publish the shared live-agent registry reference documentation under `docs/reference/registry/` with an `index.md` entrypoint instead of concentrating the full registry reference inside broader runtime pages.

That subtree SHALL provide a navigational overview that directs readers to detailed registry documentation pages by topic.

#### Scenario: Registry reference entrypoint is a navigational index
- **WHEN** a reader opens the shared-registry reference entrypoint
- **THEN** the repository presents `docs/reference/registry/index.md`
- **AND THEN** that page explains the structure of the registry reference subtree and links to the detailed pages

#### Scenario: Top-level docs navigation reaches the registry subtree
- **WHEN** a reader browses top-level reference indexes or broader runtime reference pages
- **THEN** those pages link to the shared-registry reference subtree
- **AND THEN** the subtree is discoverable without requiring the reader to inspect source directories directly

### Requirement: Shared-registry reference documentation separates contracts, operations, and internals
The `docs/reference/registry/` subtree SHALL separate detailed registry documentation into distinct categories for contracts, operations, and internals.

The registry reference SHALL include at minimum one detailed page in each of those categories.

#### Scenario: Registry contracts, operations, and internals have distinct pages
- **WHEN** a reader navigates the shared-registry reference subtree
- **THEN** the subtree provides dedicated detailed pages for registry contracts, operator-facing workflows, and internal runtime integration
- **AND THEN** those pages do not rely on one mixed catch-all page to explain all registry topics

### Requirement: Shared-registry reference pages combine intuitive explanations with exact technical detail
Each detailed shared-registry reference page SHALL be understandable to first-time readers while still preserving the exact technical details needed for implementation, debugging, or maintenance.

At minimum, each detailed registry reference page SHALL include:

- a short explanation of what the page covers,
- plain-language framing or mental-model guidance before dense technical detail,
- the relevant exact technical specifics, constraints, or contracts,
- at least one concrete example, representative payload, artifact shape, or walkthrough fragment where it materially helps understanding.

#### Scenario: New reader can orient before reading exact registry details
- **WHEN** a first-time reader opens a detailed shared-registry reference page
- **THEN** the page first explains the purpose of the topic in accessible language
- **AND THEN** the reader can build an intuitive mental model before encountering the full technical detail

#### Scenario: Developer can still find exact registry specifics
- **WHEN** a developer opens a detailed shared-registry reference page to answer an implementation or debugging question
- **THEN** the page includes the exact registry constraints, contracts, or artifact details relevant to that topic
- **AND THEN** the page is not limited to high-level explanatory prose alone

### Requirement: Important shared-registry procedures include embedded Mermaid sequence diagrams
When a shared-registry reference page introduces an important procedure involving multiple participants or steps, the page SHALL include an embedded Mermaid `sequenceDiagram` block directly in the Markdown page.

These diagrams SHALL accompany the prose explanation rather than replace it.

Important shared-registry procedures include at minimum:

- name-based resolution with tmux-local discovery and shared-registry fallback,
- stale-record cleanup or removal flows,
- runtime publication, refresh, or teardown flows where registry behavior depends on runtime-managed lifecycle hooks.

#### Scenario: Procedure page includes an embedded sequence diagram
- **WHEN** a registry reference page introduces an important shared-registry procedure
- **THEN** that page includes an embedded Mermaid `sequenceDiagram` block in the Markdown content
- **AND THEN** the diagram appears alongside the written explanation of the procedure

#### Scenario: Diagram supplements rather than replaces the written procedure
- **WHEN** a reader uses the documentation to understand an important shared-registry procedure
- **THEN** the page provides both prose explanation and a Mermaid sequence diagram
- **AND THEN** the reader is not required to infer the full procedure from the diagram alone

### Requirement: Shared-registry contract documentation explains the locator-layer boundary and implemented v2 record semantics
The shared-registry contract documentation SHALL explain that the shared registry is a locator layer pointing to runtime-owned state rather than a replacement authority for manifests, tmux discovery, gateway artifacts, or mailbox state.

At minimum, that contract coverage SHALL include:

- why the shared registry exists alongside tmux-local discovery,
- the effective registry root and `AGENTSYS_GLOBAL_REGISTRY_DIR` override behavior,
- the `live_agents/<agent-id>/record.json` layout,
- canonical `AGENTSYS-...` naming, authoritative `agent_id`, and the difference between name lookup and directory identity,
- the strict v2 record fields and which nested sections are optional,
- lease freshness and timezone-aware timestamp expectations,
- `generation_id` ownership and duplicate-publisher conflict semantics,
- malformed, invalid, or expired records resolving as stale rather than live,
- the boundary that records store secret-free pointers rather than copied runtime payloads,
- the shipped v2 standalone JSON Schema and current typed publication model.

The contract documentation SHALL reflect current implemented v2 behavior and SHALL describe the shipped v2 standalone JSON Schema and current typed publication model as already-shipped behavior.

#### Scenario: Contract docs explain why the registry exists and what it does not own
- **WHEN** a reader needs to understand the purpose of the shared registry
- **THEN** the contract pages explain the cross-runtime-root discovery motivation and the boundary between registry metadata and runtime-owned authority
- **AND THEN** the reader can tell that the registry is a pointer layer rather than a central runtime state store

#### Scenario: Contract docs cover implemented record and ownership semantics
- **WHEN** a reader needs the normative shared-registry reference for current implemented behavior
- **THEN** the contract pages describe record layout, authoritative `agent_id`, canonical naming, freshness, ownership conflicts, stale-record behavior, and the shipped v2 schema surface
- **AND THEN** the reader does not need to reconstruct those rules only from scattered source files or archived registry changes

### Requirement: Shared-registry operational documentation covers discovery fallback and cleanup workflows
The shared-registry operational documentation SHALL explain how registry-backed discovery and cleanup behave in the implemented v1 flow.

At minimum, that operational guidance SHALL cover:

- when name-based control uses tmux-local discovery first,
- when shared-registry fallback applies for missing or stale tmux discovery pointers,
- which validation failures still fail fast instead of falling back silently,
- how `cleanup-registry` removes stale directories and reports removed, preserved, and failed buckets,
- how operators should interpret fresh, stale, malformed, and conflicted registry state at the level needed to use the system safely.

#### Scenario: Operational guidance explains name-based resolution fallback
- **WHEN** an operator or developer needs to understand why a name-addressed control action recovered from tmux-local discovery failure
- **THEN** the registry operations pages explain the resolution order and fallback behavior
- **AND THEN** the reader can tell which discovery problems are fallback-eligible and which remain explicit errors

#### Scenario: Operational guidance explains cleanup outcomes
- **WHEN** an operator runs `cleanup-registry` or needs to inspect stale registry state
- **THEN** the registry operations pages explain the cleanup grace period, removal behavior, and reported removed, preserved, and failed buckets
- **AND THEN** the reader can distinguish currently live entries from stale or cleanup-blocked directories

### Requirement: Shared-registry internal documentation explains runtime publication hooks and failure boundaries
The shared-registry internal documentation SHALL explain how the runtime publishes, refreshes, persists, and clears registry state across runtime-managed session lifecycle actions.

At minimum, that internal coverage SHALL include:

- where `registry_generation_id` is created and persisted for tmux-backed sessions,
- how registry publication relates to manifest persistence and gateway capability publication,
- which runtime-owned actions refresh the registry record,
- how stop teardown clears registry discoverability,
- which registry failures are isolated as warnings after a primary runtime action already succeeded.

#### Scenario: Internal docs explain runtime publication and persistence boundaries
- **WHEN** a maintainer needs to understand how the runtime creates and refreshes shared-registry state
- **THEN** the registry internals pages explain the publication hooks, manifest relationship, and persisted generation behavior
- **AND THEN** the reader can relate those docs to the runtime implementation without reverse-engineering the lifecycle from code alone

#### Scenario: Internal docs explain failure isolation semantics
- **WHEN** a maintainer needs to understand how runtime actions behave when registry refresh or cleanup fails
- **THEN** the registry internals pages explain which failures are surfaced as non-fatal warnings after prompt, mailbox-refresh, or stop success
- **AND THEN** the documentation makes clear that registry maintenance is additive discovery work rather than the primary action result

### Requirement: Shared-registry reference pages identify the source materials they reflect
The shared-registry reference documentation SHALL identify the implementation files and tests that each detailed page reflects.

This source mapping SHALL help keep the repo-level registry reference aligned with the implementation and behavior-defining tests without forcing readers to use source files as the only long-form documentation.

#### Scenario: Detailed registry pages point to implementation sources
- **WHEN** a reader opens a detailed shared-registry reference page
- **THEN** that page identifies the relevant source files or tests that define the documented behavior
- **AND THEN** future registry changes have a clear trace from implementation surfaces to repo-level reference docs

### Requirement: Shared-registry reference pages introduce terminology clearly
The shared-registry reference documentation SHALL introduce important subsystem terms clearly instead of assuming prior knowledge.

At minimum, the documentation SHALL define or explain recurring terms such as shared registry, live-agent record, `agent_id`, generation id, lease freshness, canonical agent name, and locator layer before relying on them heavily.

#### Scenario: Reader encounters registry terms with enough context
- **WHEN** a new user or developer encounters shared-registry terminology in the reference subtree
- **THEN** the page or subtree entrypoint explains that terminology in accessible language
- **AND THEN** the documentation does not rely on unexplained registry jargon as the only way to understand registry behavior
