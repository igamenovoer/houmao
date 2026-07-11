## RENAMED Requirements

- FROM: `Headless Claude/Gemini/Codex sessions are tmux-backed and inspectable`
- TO: `Headless sessions are tmux-backed and inspectable`

## ADDED Requirements

### Requirement: Brain launch runtime excludes Gemini backends
The brain launch runtime SHALL NOT resolve, validate, start, resume, or dispatch a Gemini interactive or headless backend.

#### Scenario: Gemini backend cannot reach runtime dispatch
- **WHEN** a launch plan or persisted manifest names `gemini_cli` or `gemini_headless`
- **THEN** runtime validation rejects the unsupported value before provider start

## REMOVED Requirements

### Requirement: Gemini headless backend via `gemini -p` + `--resume`
**Reason**: Gemini headless execution is no longer supported.
**Migration**: Not applicable; the provider is deleted before the next release.

### Requirement: Gemini headless startup supports API-key and OAuth auth families
**Reason**: Gemini credential and headless startup support is removed.
**Migration**: Not applicable.

### Requirement: Gemini OAuth-backed runtime homes are non-interactive-ready for headless startup
**Reason**: Houmao no longer constructs Gemini runtime homes.
**Migration**: Not applicable.

### Requirement: Gemini managed skill projection uses the generic `.agents/skills` root
**Reason**: Houmao no longer constructs or adopts Gemini homes or projects Gemini skills.
**Migration**: Not applicable.

### Requirement: Gemini headless runtime honors unattended launch policy when compatible registry coverage exists
**Reason**: The Gemini backend and launch-policy strategy are removed together.
**Migration**: Not applicable.
