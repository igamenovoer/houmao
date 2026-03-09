## ADDED Requirements

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
