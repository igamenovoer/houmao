# cursor-anchored-signal-extraction Specification

## Purpose
Define the shared zone-partitioned signal extraction model used by shadow parsers before provider-specific surface classification.

## Requirements

### Requirement: Shadow parser extracts a typed signal set from each tail snapshot
For each shadow-mode tail snapshot, the provider parser SHALL extract signals into a typed `SnapshotSignalSet` frozen value object before state classification.

The signal set SHALL carry at minimum:
- `prompt_boundary_index`: the line index within the tail where the active zone begins, or None when no anchor is found,
- `active_zone_lines`: the tail lines from the prompt boundary to the end,
- `historical_zone_lines`: the tail lines above the prompt boundary,
- provider-neutral common booleans scoped to the active zone (`has_idle_prompt`, `has_processing_spinner`, `has_response_marker`, `has_operator_blocked`, `has_slash_command`, `has_error_banner`),
- `operator_blocked_excerpt`: extracted from active zone only when a blocked surface is detected,
- `active_prompt_payload`: text content following the active prompt character, and
- `anchor_type`: which anchor kind matched the prompt boundary, and
- a provider-neutral mechanism such as `blocked_surface_kind` for provider-specific blocked-surface semantics.

Signal extraction SHALL be a pure function: given the same tail lines and preset, it SHALL always produce the same `SnapshotSignalSet`.

#### Scenario: Signal extraction produces a typed value object from tail lines
- **WHEN** the provider parser receives a tail snapshot of normalized scrollback lines
- **THEN** it produces a `SnapshotSignalSet` frozen value object
- **AND THEN** all per-signal booleans reflect pattern matches within the active zone only

#### Scenario: Signal extraction is deterministic
- **WHEN** the same tail lines and preset are provided to the signal extractor twice
- **THEN** both invocations produce identical `SnapshotSignalSet` values

### Requirement: Prompt boundary is detected by reverse scan of tail lines
The signal extractor SHALL identify the prompt boundary by scanning tail lines in reverse order (from the bottom/newest to the top/oldest) and resolving the result to the start of the latest active interaction block.

Provider-defined boundary anchors SHALL include at minimum:
- idle prompt patterns (e.g., `❯` for Claude, `codex>` for Codex),
- processing spinner patterns,
- menu/approval block start patterns, and
- setup/onboarding block patterns.

When a visible prompt owns spinner/progress lines below it, the `prompt_boundary_index` SHALL resolve to that prompt line so the active zone still includes the typeable prompt together with the processing evidence.

When no anchor pattern matches any line in the tail, the prompt boundary SHALL be None and the entire tail SHALL be treated as the active zone.

#### Scenario: Idle prompt at bottom of tail sets prompt boundary
- **WHEN** the tail snapshot ends with a line matching the provider's idle prompt pattern
- **THEN** the prompt boundary index points to that line
- **AND THEN** lines above that index are classified as historical zone

#### Scenario: Prompt owning spinner remains the boundary
- **WHEN** the tail snapshot contains an idle prompt line followed by processing spinner/progress lines that belong to the same active interaction block
- **THEN** the prompt boundary index points to the prompt line rather than the spinner/progress line
- **AND THEN** the active zone includes both the prompt and the processing evidence

#### Scenario: Processing spinner without open prompt sets prompt boundary
- **WHEN** the tail snapshot ends with lines showing processing spinner activity and no still-open idle prompt that owns that processing block
- **THEN** the prompt boundary index points to the spinner line
- **AND THEN** the active zone includes the spinner and any contiguous processing lines below it

#### Scenario: No anchor found treats entire tail as active zone
- **WHEN** no line in the tail matches any provider anchor pattern
- **THEN** the prompt boundary is None
- **AND THEN** the entire tail is treated as the active zone for signal detection

### Requirement: State classification operates only on active-zone signals
The provider parser SHALL derive `business_state`, `input_mode`, and `ui_context` from the `SnapshotSignalSet` which contains only active-zone signal evidence. Historical-zone content SHALL NOT contribute to state classification.

#### Scenario: Historical response marker does not affect current idle classification
- **WHEN** the tail contains a response marker (`●`) in the historical zone above the prompt boundary
- **AND WHEN** the active zone contains an idle prompt
- **THEN** the surface assessment classifies `business_state = idle` and `input_mode = freeform`
- **AND THEN** the historical response marker does not influence classification

#### Scenario: Historical slash command does not create false slash_command context
- **WHEN** the tail contains a `/model` or other slash command in the historical zone
- **AND WHEN** the active zone contains a normal idle prompt
- **THEN** the surface assessment classifies `ui_context = normal_prompt`
- **AND THEN** the historical slash command does not produce a `slash_command` ui_context

#### Scenario: Historical spinner does not produce false working state
- **WHEN** the tail contains a spinner-like Unicode line in the historical zone
- **AND WHEN** the active zone contains an idle prompt
- **THEN** the surface assessment classifies `business_state = idle`
- **AND THEN** the historical spinner-like content does not produce a `working` business_state

### Requirement: Zone partitioning utility is shared across providers
The generic reverse-scan algorithm for finding the prompt boundary SHALL be implemented as a shared utility in the shadow parser core module.

Provider parsers SHALL supply their own provider-defined boundary anchors to the shared utility. Those anchors MAY use richer provider-owned matching semantics than a flat shared boolean vocabulary. The utility SHALL return the prompt boundary index or None.

#### Scenario: Claude and Codex parsers use the same boundary-finding algorithm with different patterns
- **WHEN** Claude and Codex parsers both need to find the prompt boundary
- **THEN** both call the shared `find_prompt_boundary()` utility
- **AND THEN** each passes its own provider-specific boundary anchors

### Requirement: Active prompt payload is anchored to the prompt boundary line
When the prompt boundary is an idle prompt anchor, the `active_prompt_payload` SHALL be extracted from the prompt boundary line itself rather than from a fragile backwards scan of the last non-empty line.

#### Scenario: Prompt payload extracted from boundary line ignores trailing blank lines
- **WHEN** the prompt boundary is an idle prompt line followed by blank or status lines
- **THEN** the active prompt payload is extracted from the prompt boundary line
- **AND THEN** trailing blank lines do not shift the detected prompt content

#### Scenario: Non-prompt boundary produces no prompt payload
- **WHEN** the prompt boundary is a processing spinner or blocked-surface anchor
- **THEN** the active prompt payload is None
