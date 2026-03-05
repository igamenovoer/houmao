## ADDED Requirements

### Requirement: Runtime-owned shadow parser stack is version-aware and reports match/anomalies
The system SHALL provide a runtime-owned shadow parser stack for parsing CAO/TUI tool output for:

- `codex`
- `claude`

For each provider, the stack SHALL select exactly one parsing preset for a given output snapshot using this resolution order:

1. An explicit operator override (for example an environment variable that pins a preset version), when provided.
2. A detected version signature from the output when present (for example a banner line).
3. A deterministic fallback strategy when version detection fails (for example “latest known preset”).

The stack SHALL return structured parser metadata that includes at minimum:

- provider/tool id,
- selected preset id/version,
- an output-variant identifier (a stable string identifying the matched format family),
- a boolean indicating whether the output matched a known supported variant exactly,
- baseline invalidation status (when applicable), and
- anomaly codes when the match is partial (for example “unknown version, used floor preset”).

#### Scenario: Env override pins the selected parsing preset
- **WHEN** an operator sets a shadow parser preset override for a provider
- **AND WHEN** the system parses a shadow output snapshot for that provider
- **THEN** the stack uses the overridden preset selection regardless of auto-detected version signatures
- **AND THEN** parser metadata records the selected preset id/version

#### Scenario: Unknown version uses a floor preset and reports an anomaly
- **WHEN** output contains a provider version signature `V`
- **AND WHEN** no exact parsing preset exists for `V`
- **AND WHEN** a previous (floor) preset is selected for best-effort compatibility
- **THEN** parser metadata includes an anomaly indicating that a floor preset was used for an unknown/newer version

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
