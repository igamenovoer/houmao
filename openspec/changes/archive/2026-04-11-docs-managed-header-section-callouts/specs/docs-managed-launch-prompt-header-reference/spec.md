## MODIFIED Requirements

### Requirement: Reference page documents the managed launch prompt header

The docs site SHALL include a reference page at `docs/reference/run-phase/managed-prompt-header.md` describing the Houmao-owned prompt header that is prepended to managed launches by default.

The docs site index entry for that reference page (`docs/index.md`) SHALL mention per-section control in its one-line description, alongside composition, opt-out, and stored-profile policy.

#### Scenario: Docs index entry reflects per-section control

- **WHEN** a reader scans `docs/index.md` looking for the managed-header reference
- **THEN** the index entry mentions per-section control or independently controllable sections
- **AND THEN** the entry links to `docs/reference/run-phase/managed-prompt-header.md`
