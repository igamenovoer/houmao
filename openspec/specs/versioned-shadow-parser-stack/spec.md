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

### Requirement: Dialog projection processing is modular and swappable within the parser stack
The runtime-owned shadow parser stack SHALL resolve dialog projection through a provider-owned projection processor abstraction rather than by hardwiring all projection rules into one monolithic parser method.

For each parsed snapshot, the provider parser SHALL select exactly one projection processor instance.
The projection processor contract SHALL be a repo-owned duck-typed interface such as a `Protocol` or an equivalent narrow abstraction rather than an ad hoc callback surface.
That contract SHALL operate on an already-normalized snapshot plus provider-owned projection context and SHALL return provider-owned projection content/evidence for one snapshot.

Parser/shared-core flow SHALL retain ANSI stripping, newline normalization, preset resolution, surface assessment, projection fallback behavior, head/tail slicing, and final `DialogProjection`/`ProjectionMetadata` assembly around the selected processor output.

Default projection processor selection SHALL live in the provider parser, colocated with provider preset/version resolution.
That selection SHALL depend at minimum on the resolved provider parser preset/version and MAY additionally depend on matched output-variant evidence or other provider-owned snapshot evidence.
When no exact processor mapping exists for a detected provider version or output family, the provider parser SHALL follow its version-aware fallback policy rather than pushing fallback behavior into runtime lifecycle code.

Projection processor selection SHALL remain isolated from runtime lifecycle monitoring so that changing projection logic for a provider/output family does not require changing runtime `TurnMonitor` logic or unrelated provider surface-classification code.

Projection provenance SHALL identify the selected processor instance through a stable string `projector_id`.

#### Scenario: Provider swaps projection processor for a known output family
- **WHEN** a provider parser preset or output family is mapped to a different projection processor implementation
- **THEN** the provider parser uses that selected processor to produce `DialogProjection`
- **AND THEN** runtime lifecycle logic continues to consume the resulting shared projection contract without requiring unrelated changes

#### Scenario: Projection processor selection is version-aware
- **WHEN** two provider versions require different dialog-cleanup logic for otherwise similar TUI snapshots
- **THEN** the provider parser may select different projection processor instances for those versions
- **AND THEN** the selection remains inside the parser stack rather than being spread across runtime lifecycle code

#### Scenario: Projection processor fallback follows provider parser policy
- **WHEN** a detected provider version does not have an exact projection processor mapping
- **THEN** the provider parser falls back according to its version-aware selection policy
- **AND THEN** runtime lifecycle code and repo-owned helpers continue to consume the same shared projection contract

### Requirement: Surface assessment models use a frozen common base with provider-specific subclasses
The shadow parser stack SHALL model snapshot state assessment with frozen value objects.

At minimum, the shared base `SurfaceAssessment` contract SHALL carry:

- `availability`,
- `business_state`,
- `input_mode`,
- `ui_context` using a common base vocabulary that includes at least `normal_prompt`, `selection_menu`, `slash_command`, and `unknown`, and
- `operator_blocked_excerpt` when an active blocked surface exposes a useful operator-facing excerpt, and
- parser metadata/anomalies.

The shared `business_state` vocabulary SHALL include:

- `idle`
- `working`
- `awaiting_operator`
- `unknown`

The shared `input_mode` vocabulary SHALL include:

- `freeform`
- `modal`
- `closed`
- `unknown`

Provider implementations SHALL expose provider-specific subclasses that refine `ui_context` and evidence fields without changing the shared base semantics.

#### Scenario: Claude and Codex assessments share common fields but keep provider-specific context vocabularies
- **WHEN** the stack returns Claude and Codex surface assessments
- **THEN** both results expose the same shared base fields for availability, business state, input mode, `ui_context`, and metadata
- **AND THEN** each provider may extend `ui_context` and evidence with provider-specific values

#### Scenario: Working surface can remain typeable
- **WHEN** a provider snapshot shows processing or progress evidence while the active editable prompt is still open
- **THEN** the returned `SurfaceAssessment.business_state` is `working`
- **AND THEN** the returned `SurfaceAssessment.input_mode` may still be `freeform`

#### Scenario: Blocked-surface excerpt is shared across providers
- **WHEN** a provider snapshot exposes a blocked operator surface with a visible approval, trust, or selection excerpt
- **THEN** the returned `SurfaceAssessment.operator_blocked_excerpt` may carry that excerpt on the shared base contract
- **AND THEN** runtime does not need provider-specific downcasting to surface blocked diagnostics

### Requirement: Slash-command surface classification follows the active input region
The runtime-owned shadow parser stack SHALL classify `ui_context="slash_command"` only when the currently active provider input surface is still inside slash-command interaction.

Historical slash-command echoes, command results, or model-switch output that remain visible elsewhere in the same `mode=full` scrollback SHALL NOT keep a newer normal prompt classified as `slash_command`.

When a newer normal prompt is visible, the returned `SurfaceAssessment.input_mode` value SHALL reflect that recovered `freeform` prompt even if the dialog projection still includes earlier slash-command content.

#### Scenario: Active slash-command prompt is classified as slash-command
- **WHEN** a provider snapshot still shows the current editable prompt inside slash-command input
- **THEN** the returned `SurfaceAssessment.ui_context` is `slash_command`
- **AND THEN** the returned `SurfaceAssessment.input_mode` is `modal`

#### Scenario: Historical slash-command history does not poison a later normal prompt
- **WHEN** a provider snapshot still includes an earlier slash command and its visible result in the dialog history
- **AND WHEN** a newer normal prompt is now the active input surface
- **THEN** the returned `SurfaceAssessment.ui_context` is not `slash_command`
- **AND THEN** the returned `SurfaceAssessment.input_mode` reflects the newer normal prompt rather than the historical slash-command line

### Requirement: Input mode and UI context are co-derived from one active-surface pass
For each parsed snapshot, provider parsers SHALL derive `input_mode` and `ui_context` from the same active-surface evidence pass.

When evidence conflicts inside one bounded window, parsers SHALL resolve input semantics with this precedence:

1. operator-blocked surfaces such as trust, approval, onboarding, login, or selection UI
2. slash-command or other modal command surfaces
3. normal freeform prompt surfaces
4. `unknown` when the active input region cannot be resolved safely

Parsers SHALL NOT emit contradictory pairs such as:

- `ui_context = slash_command` with `input_mode = freeform`
- provider blocked contexts such as `trust_prompt`, `approval_prompt`, or `selection_menu` with `input_mode = freeform`

#### Scenario: Stronger blocked context overrides visible prompt markers
- **WHEN** a bounded snapshot window still contains normal prompt markers but the active surface is a trust, approval, or selection prompt
- **THEN** the parser resolves `input_mode` from the blocked surface rather than from the historical prompt marker
- **AND THEN** the resulting `ui_context` and `input_mode` stay consistent with that blocked surface

#### Scenario: Ambiguous active surface falls back to unknown instead of contradiction
- **WHEN** the parser cannot safely resolve whether the active surface is modal or freeform
- **THEN** it returns `input_mode = unknown`
- **AND THEN** it does not emit a contradictory `ui_context` or freeform-ready classification

### Requirement: Submit readiness is derived from shared shadow surface axes
For shadow parser results, submit readiness SHALL be treated as a derived predicate rather than as a separate primitive parser state.

A surface is `submit_ready` only when all of the following are true:

- `availability = supported`
- `business_state = idle`
- `input_mode = freeform`

Provider implementations SHALL NOT force a separate readiness enum that contradicts those shared axes.

#### Scenario: Idle freeform surface is submit-ready
- **WHEN** a provider snapshot is supported, not actively working, and exposes a normal freeform prompt
- **THEN** the resulting surface satisfies the derived `submit_ready` predicate
- **AND THEN** runtime may use that derived predicate for prompt submission logic

#### Scenario: Working freeform surface is not submit-ready
- **WHEN** a provider snapshot is supported and still processing while the prompt remains typeable
- **THEN** the resulting surface does not satisfy the derived `submit_ready` predicate
- **AND THEN** runtime does not treat typing capability alone as proof that submission is safe

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

### Requirement: Shadow parser stack supports controlled projection-processor override
The runtime-owned shadow parser stack SHALL support controlled override of the projection processor used for a parsed snapshot so tests and advanced callers can swap projection behavior without rewriting provider parser classes.

This controlled override SHALL be exposed through provider parser construction and through `ShadowParserStack` construction.
The stack-level override SHALL act as pass-through injection to the selected provider parser rather than as an independent projector-selection mechanism.
This controlled override SHALL remain narrower than arbitrary runtime plugin discovery.

#### Scenario: Test or advanced caller injects a projection processor override through the shared stack
- **WHEN** a test or advanced caller supplies an explicit projection processor override through `ShadowParserStack` for a supported provider
- **THEN** the stack uses that processor for matching snapshots
- **AND THEN** the returned `DialogProjection.projection_metadata.projector_id` reflects the injected processor

#### Scenario: Direct provider parser construction supports the same explicit override
- **WHEN** a test or advanced caller constructs a provider parser directly with an explicit projection processor override
- **THEN** that parser uses the injected processor for matching snapshots
- **AND THEN** the override contract matches the shared stack pass-through behavior

### Requirement: Core shadow parser stack does not own prompt-to-answer association
The core shadow parser stack SHALL NOT claim that projected dialog content is the authoritative final answer for the current prompt.

Prompt-to-answer association, when needed, SHALL be treated as a separate optional layer above the core parser stack.

#### Scenario: Stack returns projected dialog without authoritative answer claim
- **WHEN** the parser stack processes a snapshot whose projected dialog may contain historical visible content
- **THEN** it returns projected dialog and parser metadata
- **AND THEN** it does not claim that the projection is the authoritative answer for the most recent prompt

### Requirement: Repo-owned shadow-aware helper code uses the shared stack-level abstraction
Repo-owned workflows or demo helpers that need to parse supported provider TUI snapshots outside the main CAO turn engine SHALL use the shared shadow parser stack or another repo-owned stack-level adapter that preserves provider selection, parser-owned projector selection, and controlled override behavior.

They SHALL NOT bypass that shared abstraction by pinning provider-private parser classes as the normal integration point for shadow parsing behavior that the stack now owns.

#### Scenario: Demo helper parses supported TUI snapshots through the shared stack
- **WHEN** a repo-owned helper needs to inspect live Claude or Codex `mode=full` output outside the main turn engine
- **THEN** it obtains parsing behavior through `ShadowParserStack` or an equivalent shared adapter
- **AND THEN** provider/version-specific projector selection remains centralized behind the shared adapter instead of being reimplemented by the helper

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
