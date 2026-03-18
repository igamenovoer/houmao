# shadow-dialog-projection Specification

## Purpose
Define expected runtime behaviors for projecting normalized dialog from shadow-mode TUI snapshots.

## Requirements

### Requirement: Dialog projection uses frozen value objects with shared fields and provider-specific extensions
For shadow-mode sessions, dialog projection SHALL be represented by frozen value objects rather than ad hoc dictionaries or raw strings.

At minimum, the shared base `DialogProjection` contract SHALL provide:

- `raw_text`, which carries the original snapshot text before runtime normalization,
- `normalized_text`, which carries ANSI-stripped, newline-normalized snapshot text and SHALL remain closer to the source surface than heuristic dialog cleanup,
- `dialog_text`, which carries a best-effort dialog-oriented rendering derived from the snapshot and SHALL NOT be treated as an exact reconstruction of provider-visible TUI text,
- `head`,
- `tail`,
- projection provenance/metadata, and
- anomalies when projection rules detect drift or ambiguity.

Provider implementations MAY refine projection metadata and evidence through provider-specific subclasses, but SHALL preserve the shared field meanings.

#### Scenario: Claude and Codex projections share the same base projection fields
- **WHEN** the runtime returns dialog projection for Claude and Codex shadow-mode sessions
- **THEN** both payloads expose the same base projection text fields and transcript slices
- **AND THEN** provider-specific subclasses may attach additional projection evidence without changing the shared contract

#### Scenario: Caller can distinguish normalized text from heuristic dialog text
- **WHEN** a caller receives a shadow-mode `dialog_projection`
- **THEN** the payload includes both `normalized_text` and `dialog_text`
- **AND THEN** the contract does not require `dialog_text` to be an exact copy of the provider-visible TUI text

### Requirement: Shadow-mode sessions expose normalized dialog projection
For CAO-backed sessions running in `parsing_mode=shadow_only`, the system SHALL expose a caller-facing dialog projection derived from provider TUI snapshots rather than raw tmux scrollback.

Dialog projection SHALL:

- strip ANSI and attempt to remove provider-specific TUI chrome using provider/version-aware heuristics such as regex or other pattern matching over known banners, prompts, separators, spinners, footers, or menu markers,
- preserve essential dialog ordering,
- retain user/assistant content that remains visible in the projected transcript,
- record provenance indicating that the projection was derived from TUI snapshots rather than a structured turn protocol, and
- remain a best-effort rendering rather than an exact-text guarantee.

#### Scenario: Projection removes common TUI chrome while preserving dialog ordering
- **WHEN** a shadow-mode snapshot contains prompt glyphs, ANSI styling, footer chrome, and visible dialog content
- **THEN** the system returns projected dialog content with common known chrome removed
- **AND THEN** the projected dialog preserves the visible dialog ordering from the snapshot

#### Scenario: Projection remains available without exact cleanup fidelity
- **WHEN** provider redraw behavior or drift prevents perfect separation between dialog text and surrounding TUI chrome
- **THEN** the system still returns best-effort projected dialog plus `normalized_text`
- **AND THEN** the runtime does not claim that the projected dialog is an exact recovered transcript

### Requirement: Shadow-mode dialog projection provides transcript slices
The system SHALL expose stable transcript slices over projected dialog content for shadow-mode callers.

At minimum, the system SHALL support caller-visible head and tail views over the projected dialog.
The system SHALL NOT expose raw CAO `tail` transport output as a first-class projection slice in the primary caller-facing contract.
Raw transport tail MAY still exist in diagnostics or internal debugging paths outside the primary projection contract.

#### Scenario: Caller reads head and tail projection slices
- **WHEN** a shadow-mode turn completes and projected dialog content is available
- **THEN** the system provides caller-visible head and tail views over that projected dialog
- **AND THEN** the slices are derived from projected dialog content rather than raw tmux scrollback

#### Scenario: Raw transport tail is not promoted to a primary projection slice
- **WHEN** a caller receives a shadow-mode projection result
- **THEN** the primary projection contract exposes projected `head` and `tail` slices rather than raw CAO `tail` output
- **AND THEN** any retained raw transport tail remains outside the obvious caller-facing projection surface

### Requirement: Dialog projection does not imply prompt-associated final answer
The system SHALL NOT represent projected dialog content as the authoritative final answer for the current prompt unless a separate answer-association layer explicitly does so.

Projected dialog MAY include historical dialog content, turn-local UI remnants, or other visible text that is not uniquely attributable to the most recent prompt submission.

Reliable downstream machine use SHALL depend on a separate caller-owned or protocol-owned extraction contract, such as schema-shaped prompting plus explicit pattern or sentinel extraction over available text surfaces, rather than on `dialog_projection.dialog_text` alone.

#### Scenario: Projected dialog remains valid without answer association
- **WHEN** a projected dialog snapshot contains visible content from multiple visible turns or other turn-local UI
- **THEN** the system still returns the projected dialog content
- **AND THEN** the system does not claim that the projection is the authoritative final answer for the most recent prompt by default

#### Scenario: Caller uses schema-shaped extraction for reliable machine reading
- **WHEN** a downstream integration needs reliable machine-readable data from a shadow-mode session
- **THEN** it uses an explicit answer-association or schema-shaped extraction contract over available text surfaces
- **AND THEN** it does not treat `dialog_projection.dialog_text` by itself as an exact-text guarantee

### Requirement: Shadow-mode text surfaces have explicit reliability tiers
The system SHALL classify repo-owned shadow-mode text uses into three reliability tiers:

- lifecycle/runtime, where best-effort projected dialog is acceptable only for coarse change detection or readiness/completion monitoring,
- operator/diagnostic, where best-effort projected dialog is acceptable for human-facing inspection or debugging surfaces, and
- machine-critical, where projected dialog by itself is insufficient and the consumer SHALL rely on schema-shaped prompting, explicit sentinels, or a caller-owned extractor over available text surfaces.

The current normative mappings for repo-owned consumers SHALL include `_TurnMonitor.observe_completion()` as lifecycle/runtime, interactive demo `output_text_tail` as operator/diagnostic, and runtime mailbox result parsing as machine-critical.

#### Scenario: Lifecycle monitoring uses projected dialog only for coarse change detection
- **WHEN** runtime lifecycle monitoring compares projected dialog before and after prompt submission
- **THEN** it may use projected dialog changes as coarse completion/readiness evidence
- **AND THEN** that lifecycle use does not imply answer extraction or exact-text recovery

#### Scenario: Operator-facing inspect output uses the operator/diagnostic tier
- **WHEN** interactive demo inspect surfaces `output_text_tail`
- **THEN** that field is treated as a best-effort projected diagnostic tail for human inspection
- **AND THEN** the contract does not elevate that field to authoritative reply text

#### Scenario: Machine-critical consumer uses an explicit structured extraction contract
- **WHEN** a machine-critical consumer such as runtime mailbox result parsing needs reliable shadow-mode data
- **THEN** it uses schema/sentinel or caller-owned extraction over available text surfaces
- **AND THEN** projected dialog alone is insufficient as the correctness boundary
