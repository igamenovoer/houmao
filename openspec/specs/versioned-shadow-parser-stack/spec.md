## ADDED Requirements

### Requirement: Runtime-owned shadow parser stack is version-aware and reports state/projection/anomalies
The system SHALL provide a runtime-owned shadow parser stack for parsing CAO/TUI tool output for:

- `codex`
- `claude`

For each provider, the stack SHALL select exactly one parsing preset for a given output snapshot using this resolution order:

1. An explicit operator override, when provided.
2. A detected version signature from the output when present.
3. A deterministic fallback strategy when version detection fails.

The stack SHALL return:

- a structured provider `SurfaceAssessment` value object for the selected snapshot,
- a structured provider `DialogProjection` value object derived from that snapshot, and
- structured parser metadata that includes at minimum:
  - provider/tool id,
  - selected preset id/version,
  - an output-variant identifier,
  - a boolean indicating whether the output matched a known supported variant exactly,
  - baseline invalidation status when applicable, and
  - anomaly codes when the match is partial.

The stack SHALL treat state/projection artifacts as the core parser contract instead of prompt-associated answer extraction.

#### Scenario: Env override pins the selected parsing preset and returns state/projection artifacts
- **WHEN** an operator sets a shadow parser preset override for a provider
- **AND WHEN** the system parses a shadow output snapshot for that provider
- **THEN** the stack uses the overridden preset selection regardless of auto-detected version signatures
- **AND THEN** parser metadata records the selected preset id/version
- **AND THEN** the stack returns provider-specific `SurfaceAssessment` and `DialogProjection` artifacts for that snapshot

#### Scenario: Unknown version uses a floor preset and reports an anomaly
- **WHEN** output contains a provider version signature `V`
- **AND WHEN** no exact parsing preset exists for `V`
- **AND WHEN** a previous floor preset is selected for best-effort compatibility
- **THEN** parser metadata includes an anomaly indicating that a floor preset was used for an unknown/newer version

### Requirement: Surface assessment models use a frozen common base with provider-specific subclasses
The shadow parser stack SHALL model snapshot state assessment with frozen value objects.

At minimum, the shared base `SurfaceAssessment` contract SHALL carry:

- `availability`,
- `activity`,
- `accepts_input`,
- `ui_context` using a common base vocabulary that includes at least `normal_prompt`, `selection_menu`, `slash_command`, and `unknown`, and
- parser metadata/anomalies.

Provider implementations SHALL expose provider-specific subclasses that refine `ui_context` and evidence fields without changing the shared base semantics.

#### Scenario: Claude and Codex assessments share common fields but keep provider-specific context vocabularies
- **WHEN** the stack returns Claude and Codex surface assessments
- **THEN** both results expose the same shared base fields for availability/activity/input-safety/metadata
- **AND THEN** each provider may extend `ui_context` and evidence with provider-specific values

#### Scenario: Shared base `ui_context` includes slash-command context across providers
- **WHEN** a provider snapshot is classified as being inside slash-command or command-palette UI
- **THEN** the returned `SurfaceAssessment.ui_context` may use the shared `slash_command` base value
- **AND THEN** provider-specific subclasses may still add richer context values alongside that shared base

### Requirement: Slash-command surface classification follows the active input region
The runtime-owned shadow parser stack SHALL classify `ui_context="slash_command"` only when the currently active provider input surface is still inside slash-command interaction.

Historical slash-command echoes, command results, or model-switch output that remain visible elsewhere in the same `mode=full` scrollback SHALL NOT keep a newer normal prompt classified as `slash_command`.

When a newer normal prompt is visible, the returned `SurfaceAssessment.accepts_input` value SHALL reflect that recovered prompt even if the dialog projection still includes earlier slash-command content.

#### Scenario: Active slash-command prompt is classified as slash-command
- **WHEN** a provider snapshot still shows the current editable prompt inside slash-command input
- **THEN** the returned `SurfaceAssessment.ui_context` is `slash_command`
- **AND THEN** the returned `SurfaceAssessment.accepts_input` is `false`

#### Scenario: Historical slash-command history does not poison a later normal prompt
- **WHEN** a provider snapshot still includes an earlier slash command and its visible result in the dialog history
- **AND WHEN** a newer normal prompt is now the active input surface
- **THEN** the returned `SurfaceAssessment.ui_context` is not `slash_command`
- **AND THEN** the returned `SurfaceAssessment.accepts_input` reflects the newer normal prompt rather than the historical slash-command line

### Requirement: Dialog projection models use a frozen common base with provider-specific subclasses
The shadow parser stack SHALL model dialog projection with frozen value objects.

At minimum, the shared base `DialogProjection` contract SHALL carry:

- `raw_text`,
- `normalized_text`,
- `dialog_text`,
- `head`,
- `tail`,
- typed projection metadata/provenance, and
- anomalies when projection rules detect drift or ambiguity.

Provider implementations SHALL expose provider-specific subclasses that refine projection metadata/evidence without changing the shared projection semantics.

#### Scenario: Provider projections share common slices and provenance while keeping provider-specific evidence
- **WHEN** the stack returns Claude and Codex dialog projections
- **THEN** both results expose shared text fields and transcript slices
- **AND THEN** each provider may attach provider-specific projection evidence or metadata

### Requirement: Core shadow parser stack does not own prompt-to-answer association
The core shadow parser stack SHALL NOT claim that projected dialog content is the authoritative final answer for the current prompt.

Prompt-to-answer association, when needed, SHALL be treated as a separate optional layer above the core parser stack.

#### Scenario: Stack returns projected dialog without authoritative answer claim
- **WHEN** the parser stack processes a snapshot whose projected dialog may contain historical visible content
- **THEN** it returns projected dialog and parser metadata
- **AND THEN** it does not claim that the projection is the authoritative answer for the most recent prompt

### Requirement: Unknown or unsupported output variants fail explicitly with diagnostics
When a provider output snapshot does not match any supported output variant for that provider, the system SHALL fail explicitly with an `unsupported_output_format`-class error and SHALL include actionable diagnostics.

At minimum, the diagnostics SHALL include:

- an ANSI-stripped tail excerpt of the output, and
- the provider/tool id and parsing preset selection context (when available).

The system SHALL NOT treat unknown/unsupported output variants as normal `processing` indefinitely.

#### Scenario: Drifted output fails explicitly and includes an excerpt
- **WHEN** a shadow parsing operation receives output that does not match any supported output variant
- **THEN** the operation fails with an explicit `unsupported_output_format`-class error
- **AND THEN** the error includes an ANSI-stripped tail excerpt suitable for debugging
