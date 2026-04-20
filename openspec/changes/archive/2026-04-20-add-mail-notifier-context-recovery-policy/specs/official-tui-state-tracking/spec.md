## ADDED Requirements

### Requirement: Degraded diagnostics are profile-owned and tool-scoped
The shared tracked-TUI contract SHALL allow supported profiles to publish structured degraded-context diagnostic metadata alongside chat-context state.

That metadata SHALL identify the owning CLI tool or profile family. Any degraded error type value other than `unknown` SHALL be scoped to that owning CLI tool or profile family.

The shared tracked-TUI contract SHALL NOT define one universal degraded error-type enum for all CLI tools. A consumer SHALL NOT assume that two non-`unknown` degraded error type strings from different tool profiles have the same semantics unless those profiles explicitly define that compatibility.

`unknown` SHALL be the only degraded error type value that is shared by default across CLI tool profiles.

#### Scenario: Shared contract carries tool identity
- **WHEN** a tracked-TUI profile publishes degraded-context diagnostic metadata
- **THEN** the metadata identifies the owning CLI tool or profile family
- **AND THEN** consumers can distinguish Codex-owned classifications from Claude, Gemini, or future tool classifications

#### Scenario: Non-unknown degraded error types are not shared by default
- **WHEN** two different CLI tool profiles publish degraded diagnostic metadata
- **AND WHEN** their degraded error type values are not `unknown`
- **THEN** a consumer does not treat those values as the same cross-tool category unless both profiles explicitly define that compatibility

#### Scenario: Unknown remains the shared fallback
- **WHEN** a tracked-TUI profile recognizes degraded context but cannot classify the tool-specific error type
- **THEN** the profile may publish `unknown`
- **AND THEN** consumers may treat `unknown` as the shared unclassified degraded-error fallback

#### Scenario: Tool-specific diagnostics do not imply automatic recovery
- **WHEN** a tracked-TUI profile publishes degraded diagnostic metadata
- **THEN** the shared tracking contract exposes diagnostic evidence only
- **AND THEN** gateway automation selects context recovery only through explicit caller or automation policy
