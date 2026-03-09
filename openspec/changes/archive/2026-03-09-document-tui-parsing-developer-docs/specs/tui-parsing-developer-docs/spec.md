## ADDED Requirements

### Requirement: Repository SHALL publish a focused developer TUI parsing documentation set
The repository SHALL provide a developer-oriented documentation set under `docs/developer/tui-parsing/` for the runtime-owned TUI parsing system.

That documentation set SHALL include at minimum:
- `index.md`,
- `architecture.md`,
- `shared-contracts.md`,
- `runtime-lifecycle.md`,
- `claude.md`,
- `codex.md`, and
- `maintenance.md`.

The landing page SHALL explain the purpose of the document set and link readers to the aspect-focused pages.

#### Scenario: Developer can discover the TUI parsing doc set
- **WHEN** a developer opens `docs/developer/tui-parsing/index.md`
- **THEN** the page explains what the doc set covers
- **AND THEN** it links to the architecture, contract, lifecycle, provider, and maintenance pages

### Requirement: Developer docs SHALL explain the shared ownership boundaries and data contracts
The developer documentation set SHALL explain the stable shared architecture of TUI parsing, including the boundary between provider snapshot parsers, dialog projection, runtime `TurnMonitor`, and optional caller-side answer association.

The docs SHALL describe the shared contract concepts used by the current runtime, including `SurfaceAssessment`, `DialogProjection`, parser metadata/anomalies, projection slices, and the shadow-mode result surface.

#### Scenario: Developer can map the shared runtime model to official docs
- **WHEN** a developer needs to understand what is owned by the parser versus the runtime versus the caller
- **THEN** the doc set explains those boundaries in one place
- **AND THEN** it describes the shared parser artifacts and result payload concepts without requiring the reader to reverse-engineer them from archived change notes

### Requirement: Developer docs SHALL describe runtime lifecycle states and state transitions
The developer documentation set SHALL explain the runtime lifecycle for `shadow_only` turns, including `TurnMonitor` states, major events, success terminality rules, and blocked, stalled, unsupported, and disconnected outcomes.

The lifecycle documentation SHALL include a rendered Mermaid UML-style state-transition diagram for `TurnMonitor`.
The lifecycle documentation SHALL define each documented runtime state and SHALL explain how each major transition event is defined from parser/runtime observations.

#### Scenario: Developer can reason about why a turn did or did not complete
- **WHEN** a developer reads the runtime lifecycle page while debugging a `shadow_only` completion issue
- **THEN** the page describes the relevant runtime states and transition events
- **AND THEN** the page includes a Mermaid state-transition graph for the lifecycle
- **AND THEN** it explains the rule that success terminality requires a return to `ready_for_input` plus post-submit evidence such as projection change or observed `working`

### Requirement: Developer docs SHALL capture provider-specific parsing contracts separately for Claude and Codex
The developer documentation set SHALL provide separate provider-focused pages for Claude and Codex.

Those pages SHALL describe the provider-specific state vocabulary, `ui_context` distinctions, detection predicates or signals, and projection boundaries that matter when maintaining the parser stack.
Each provider page SHALL include a rendered Mermaid parser-state transition diagram and SHALL explain the tool-specific state meanings and transition events used by that provider contract.

#### Scenario: Developer can compare Claude and Codex parser behavior
- **WHEN** a developer is updating or reviewing provider-specific parsing behavior
- **THEN** the Claude and Codex pages describe the provider-specific rules independently
- **AND THEN** each page includes its own parser-state transition graph and state or event explanation
- **AND THEN** the reader can identify where the providers share concepts and where their contracts diverge

### Requirement: Documentation navigation and maintenance guidance SHALL keep the deep-dive docs discoverable
The repository docs navigation SHALL link readers to the TUI parsing developer documentation set, and the developer docs SHALL explain how maintainers should keep the documentation aligned with contracts, specs, and parser fixtures when the TUI surface changes.

Existing reference or troubleshooting pages for shadow parsing SHALL point readers at the deep-dive documentation set for design-level detail instead of duplicating that detail in multiple places.

#### Scenario: Reference page points developers to the deeper design docs
- **WHEN** a developer starts from `docs/index.md` or an existing shadow-parsing reference page
- **THEN** they can navigate to the TUI parsing developer documentation set
- **AND THEN** the maintenance guidance explains which docs, specs, and tests need review when parsing contracts or provider presets change
