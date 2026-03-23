## MODIFIED Requirements

### Requirement: Mailbox contract documentation covers the implemented v1 mailbox surfaces
The mailbox contract documentation SHALL describe the implemented v1 mailbox surfaces that readers must follow.

At minimum, that contract coverage SHALL include:

- the canonical mailbox message and addressing model,
- runtime mailbox bindings, discoverable mailbox skill projection, and runtime `mail` command expectations,
- managed mailbox helper script contract,
- filesystem mailbox layout and artifact contract.

#### Scenario: Contract documentation covers canonical and runtime mailbox surfaces
- **WHEN** a reader needs the normative mailbox reference for v1 behavior
- **THEN** the mailbox contract pages describe the canonical message model, addressing, threading, runtime mailbox bindings, the primary discoverable mailbox skill surface, and the runtime `mail` command surface
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
- the discoverable mailbox skill surface used by runtime-owned mailbox work in current sessions,
- address-routed registration lifecycle modes,
- repair or recovery expectations for mailbox roots.

#### Scenario: Operational guidance covers runtime mailbox workflows
- **WHEN** an operator or developer needs to use the mailbox system in practice
- **THEN** the mailbox operations pages explain mailbox enablement, bootstrap expectations, the discoverable mailbox skill surface, and common read, send, and reply workflows
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

- primary runtime-owned mailbox skill projection and any compatibility-mirror behavior,
- mailbox binding refresh behavior,
- mailbox-local rules and managed helper interaction points,
- SQLite responsibility boundaries,
- address-scoped locking behavior for mailbox mutation flows.

#### Scenario: Internal docs explain runtime integration
- **WHEN** a maintainer needs to understand how mailbox support is attached to runtime sessions
- **THEN** the mailbox internals pages explain the primary discoverable mailbox skill projection, any hidden compatibility mirror behavior, the env binding model, and mailbox command integration points
- **AND THEN** the reader can relate the mailbox reference to the runtime integration code paths
- **AND THEN** the explanation gives enough plain-language framing that a developer new to the mailbox subsystem can follow the architecture

#### Scenario: Internal docs explain mutable-state and locking responsibilities
- **WHEN** a maintainer needs to understand mailbox mutation safety and state ownership
- **THEN** the mailbox internals pages explain the split between immutable canonical messages, mutable SQLite-backed mailbox state, and address-scoped locking behavior
- **AND THEN** the documentation makes clear which mailbox artifacts are authoritative for each responsibility
