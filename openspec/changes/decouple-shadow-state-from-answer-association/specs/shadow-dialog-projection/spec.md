## ADDED Requirements

### Requirement: Dialog projection uses frozen value objects with shared fields and provider-specific extensions
For shadow-mode sessions, dialog projection SHALL be represented by frozen value objects rather than ad hoc dictionaries or raw strings.

At minimum, the shared base `DialogProjection` contract SHALL provide:

- `raw_text`,
- `normalized_text`,
- `dialog_text`,
- `head`,
- `tail`,
- projection provenance/metadata, and
- anomalies when projection rules detect drift or ambiguity.

Provider implementations MAY refine projection metadata and evidence through provider-specific subclasses, but SHALL preserve the shared field meanings.

#### Scenario: Claude and Codex projections share the same base projection fields
- **WHEN** the runtime returns dialog projection for Claude and Codex shadow-mode sessions
- **THEN** both payloads expose the same base projection text fields and transcript slices
- **AND THEN** provider-specific subclasses may attach additional projection evidence without changing the shared contract

### Requirement: Shadow-mode sessions expose normalized dialog projection
For CAO-backed sessions running in `parsing_mode=shadow_only`, the system SHALL expose a caller-facing dialog projection derived from provider TUI snapshots rather than raw tmux scrollback.

Dialog projection SHALL:

- strip ANSI and provider-specific TUI chrome,
- preserve essential dialog ordering,
- retain user/assistant content that remains visible in the projected transcript, and
- record provenance indicating that the projection was derived from TUI snapshots rather than a structured turn protocol.

#### Scenario: Projection removes TUI chrome while preserving dialog ordering
- **WHEN** a shadow-mode snapshot contains prompt glyphs, ANSI styling, footer chrome, and visible dialog content
- **THEN** the system returns projected dialog content without the TUI chrome
- **AND THEN** the projected dialog preserves the visible dialog ordering from the snapshot

### Requirement: Shadow-mode dialog projection provides transcript slices
The system SHALL expose stable transcript slices over projected dialog content for shadow-mode callers.

At minimum, the system SHALL support caller-visible head and tail views over the projected dialog.

#### Scenario: Caller reads head and tail projection slices
- **WHEN** a shadow-mode turn completes and projected dialog content is available
- **THEN** the system provides caller-visible head and tail views over that projected dialog
- **AND THEN** the slices are derived from projected dialog content rather than raw tmux scrollback

### Requirement: Dialog projection does not imply prompt-associated final answer
The system SHALL NOT represent projected dialog content as the authoritative final answer for the current prompt unless a separate answer-association layer explicitly does so.

Projected dialog MAY include historical dialog content, turn-local UI remnants, or other visible text that is not uniquely attributable to the most recent prompt submission.

#### Scenario: Projected dialog remains valid without answer association
- **WHEN** a projected dialog snapshot contains visible content from multiple visible turns or other turn-local UI
- **THEN** the system still returns the projected dialog content
- **AND THEN** the system does not claim that the projection is the authoritative answer for the most recent prompt by default
