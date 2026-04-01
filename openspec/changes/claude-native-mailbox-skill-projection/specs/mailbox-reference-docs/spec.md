## MODIFIED Requirements

### Requirement: Mailbox internal documentation explains runtime integration and mutable-state architecture
The mailbox internal documentation SHALL explain how the runtime integrates mailbox support and how the filesystem transport divides immutable content from mutable state.

At minimum, that internal coverage SHALL include:

- the primary runtime-owned mailbox skill projection contract for each supported tool family,
- Claude-native top-level mailbox skill projection under the active Claude skill root,
- the boundary between the isolated runtime-owned Claude home and any user-owned project-local `.claude/` tree,
- the visible mailbox-subtree projection used by other current tool families when applicable,
- durable manifest-backed mailbox binding and current-mailbox resolution behavior,
- mailbox-local rules and managed helper interaction points,
- SQLite responsibility boundaries,
- address-scoped locking behavior for mailbox mutation flows.

#### Scenario: Internal docs explain runtime integration
- **WHEN** a maintainer needs to understand how mailbox support is attached to runtime sessions
- **THEN** the mailbox internals pages explain the tool-specific discoverable mailbox skill projection contract, including Claude-native top-level Houmao skill paths and non-Claude mailbox subtree paths where applicable
- **AND THEN** the mailbox internals pages make clear that Houmao keeps Claude runtime-owned state in an isolated runtime home rather than projecting it into the user repo's `.claude/` tree
- **AND THEN** the mailbox internals pages explain the manifest-backed mailbox binding model and mailbox command integration points
- **AND THEN** the reader can relate the mailbox reference to the runtime integration code paths
- **AND THEN** the explanation gives enough plain-language framing that a developer new to the mailbox subsystem can follow the architecture

#### Scenario: Internal docs explain mutable-state and locking responsibilities
- **WHEN** a maintainer needs to understand mailbox mutation safety and state ownership
- **THEN** the mailbox internals pages explain the split between immutable canonical messages, mutable SQLite-backed mailbox state, and address-scoped locking behavior
- **AND THEN** the documentation makes clear which mailbox artifacts are authoritative for each responsibility
