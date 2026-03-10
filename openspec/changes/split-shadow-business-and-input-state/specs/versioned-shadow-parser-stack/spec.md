## MODIFIED Requirements

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

## ADDED Requirements

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
