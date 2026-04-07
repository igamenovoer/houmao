## MODIFIED Requirements

### Requirement: TUI parsing developer guide rewritten without CAO transport framing

The TUI parsing developer guide SHALL describe the runtime-owned parsing stack for tracking interactive and headless agent sessions.

The guide SHALL explicitly state that Gemini is intentionally unsupported for TUI tracking. The index page SHALL include a note after the reading-order table explaining that Gemini uses a headless-only architecture and does not have a TUI parser. The shared-contracts page SHALL note that the provider subclasses (`ClaudeSurfaceAssessment`, `CodexSurfaceAssessment`) cover only the two TUI-tracked providers and that Gemini is excluded by design.

#### Scenario: Architecture page describes actual execution contexts
- **WHEN** a reader checks the TUI parsing architecture
- **THEN** the page describes the runtime-owned execution contexts without CAO transport framing

#### Scenario: Maintenance guide references current packages
- **WHEN** a reader checks the TUI parsing maintenance guide
- **THEN** package names and module paths match the current source tree

#### Scenario: Reader understands why Gemini has no TUI parser
- **WHEN** a reader checks the TUI parsing index page
- **THEN** the page includes a note explaining that Gemini is headless-only by design and does not have a TUI parser
- **AND THEN** the shared-contracts page confirms that provider subclasses cover Claude and Codex only
