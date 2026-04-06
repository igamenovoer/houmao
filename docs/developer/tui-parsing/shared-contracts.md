# Shared TUI Parsing Contracts

The shared contract lives in `backends/shadow_parser_core.py` and is reused by the Claude and Codex providers. These types are the stable vocabulary that the rest of the runtime should depend on.

## Shared Snapshot Artifacts

### `SurfaceAssessment`

`SurfaceAssessment` is the provider-agnostic state assessment of one visible snapshot.

| Field | Meaning |
|------|---------|
| `availability` | Whether the surface is supported, disconnected, unsupported, or otherwise unknown |
| `business_state` | The current business-state classification: `idle`, `working`, `awaiting_operator`, or `unknown` |
| `input_mode` | The active input shape: `freeform`, `modal`, `closed`, or `unknown` |
| `ui_context` | Shared or provider-specific UI context label |
| `parser_metadata` | Preset/version/output-family metadata attached to the parse |
| `anomalies` | Structured anomalies attached to this assessment |
| `operator_blocked_excerpt` | Optional menu/approval/setup excerpt when the tool is blocked on operator input |

Provider subclasses refine `ui_context` and may add evidence fields:

- `ClaudeSurfaceAssessment`
- `CodexSurfaceAssessment`

These are the only two TUI-tracked providers. Gemini is excluded by design — it runs on the `gemini_headless` backend only and does not produce TUI snapshots for shadow parsing.

### `DialogProjection`

`DialogProjection` is the dialog-oriented rendering of one snapshot.

| Field | Meaning |
|------|---------|
| `raw_text` | Raw snapshot text before runtime normalization |
| `normalized_text` | ANSI-stripped, normalized snapshot text; closest shared text surface to the captured TUI |
| `dialog_text` | Best-effort projected visible dialog after provider-specific chrome removal; not an exact recovered transcript |
| `head` | Caller-facing head slice over projected dialog |
| `tail` | Caller-facing tail slice over projected dialog |
| `projection_metadata` | Provenance for how the projection was produced |
| `anomalies` | Structured anomalies attached to projection |

Provider subclasses add provider-specific evidence:

- `ClaudeDialogProjection`
- `CodexDialogProjection`

## Shared Enumerations And Concepts

### Availability

`availability` comes from the shared `ShadowAvailability` literal set:

- `supported`: the snapshot belongs to a supported provider/output family
- `unsupported`: the parser does not recognize the snapshot shape safely enough to proceed
- `disconnected`: the surface looks detached or unavailable
- `unknown`: the parser cannot safely determine support or liveness

### Business State

`business_state` comes from the shared `ShadowBusinessState` literal set:

- `idle`
- `working`
- `awaiting_operator`
- `unknown`

### Input Mode

`input_mode` comes from the shared `ShadowInputMode` literal set:

- `freeform`
- `modal`
- `closed`
- `unknown`

Parser state is still only a one-snapshot observation. Runtime lifecycle states such as `waiting`, `in_progress`, `candidate_complete`, `completed`, and `stalled` live one layer higher in the `shared_tui_tracking/` reducer and detector profiles, and runtime derives `submit_ready` from `availability == supported`, `business_state == idle`, and `input_mode == freeform`.

### Shared `ui_context`

Both providers share a base vocabulary:

- `normal_prompt`
- `selection_menu`
- `slash_command`
- `unknown`

Provider pages describe the extra values each provider adds on top of that base.

`slash_command` is an active-surface classification, not a historical-transcript one. If an earlier `/model` or other slash interaction is still visible in projected dialog but the current editable prompt has already recovered to a normal prompt, `ui_context` should no longer remain `slash_command` and `input_mode` should follow the recovered active prompt.

## Metadata And Anomalies

### `ShadowParserMetadata`

`ShadowParserMetadata` captures the parser-side provenance for both state and projection.

Important fields include:

- `provider_id`
- `parser_preset_id`
- `parser_preset_version`
- `output_format`
- `output_variant`
- `output_format_match`
- `detected_version`
- `requested_version`
- `selection_source`
- `baseline_invalidated`
- `anomalies`

### `ProjectionMetadata`

`ProjectionMetadata` explains where the projected dialog came from and how much text it covers.

Important fields include:

- `provider_id`
- `source_kind` (`tui_snapshot` today)
- `projector_id`
- `parser_metadata`
- `dialog_line_count`
- `head_line_count`
- `tail_line_count`

Provider parsers own default projector selection. In practice this means:

- shared core code normalizes the snapshot and assembles the final `DialogProjection`
- the provider parser chooses the version-aware projector instance that will interpret that normalized text
- `projection_metadata.projector_id` identifies the selected projector implementation
- parser-level and `ShadowParserStack`-level overrides are extensibility hooks for swapping projector behavior without replacing the full parser

### Common Anomaly Codes

The shared layer currently defines several important anomaly codes:

- `unknown_version_floor_used`
- `baseline_invalidated`
- `preset_override_used`
- `stalled_entered`
- `stalled_recovered`

The provider parser emits version/baseline anomalies, while the runtime readiness/completion monitor adds stalled lifecycle anomalies.

## Projection Slices And Result Payloads

`shadow_only` callers get projection slices derived from projected dialog, not raw tmux transport output.

The runtime result payload exposes:

- `surface_assessment`
- `dialog_projection`
- `projection_slices`
- `parser_metadata`
- `mode_diagnostics`

That payload intentionally omits a shadow-mode `output_text` compatibility alias. The contract is “here is the parsed surface and projected dialog,” not “here is the authoritative answer text for your prompt.”

### Reliability Tiers

The runtime expects different levels of trust from different projection uses:

- lifecycle/runtime evidence: the current runtime monitor uses `DialogProjection.normalized_text` after pipeline normalization for coarse post-submit change detection; `dialog_text` is not the lifecycle evidence boundary
- operator diagnostics: `dialog_text`, `head`, and `tail` are appropriate for human inspection, logs, and troubleshooting
- machine-critical extraction: do not rely on exact `dialog_text` fidelity; prefer schema-shaped prompting plus explicit sentinels or similarly narrow caller-owned patterns over available text surfaces

## Optional Caller-Side Association

The shared parser contract stops at state and projection. If a caller wants to derive prompt-specific answer text, it must do so explicitly.

The built-in example lives in `backends/shadow_answer_association.py`:

- `DialogAssociator`: protocol for caller-owned association over `DialogProjection` or projected dialog text
- `TailRegexExtractAssociator`: searches the last `tail_chars` of projected dialog and returns a regex match

This layer is useful when the caller owns a narrow answer format, but it is not part of the provider parser guarantee. If the extracted text matters enough to drive downstream automation, prefer making the tool emit a schema-shaped or sentinel-delimited payload first and only use best-effort association as a fallback.
