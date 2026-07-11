## ADDED Requirements

### Requirement: Launch-policy registry contains no Gemini strategies or hooks
The packaged launch-policy registry SHALL contain no Gemini registry file, strategy identifier, backend coverage, owned path, evidence entry, or provider hook.

#### Scenario: Registry inventory excludes Gemini
- **WHEN** a maintainer lists all packaged launch-policy strategies and hook identifiers
- **THEN** no entry names `gemini`, `gemini_cli`, or `gemini_headless`

## REMOVED Requirements

### Requirement: Registry declares maintained Gemini unattended headless strategy coverage
**Reason**: Gemini headless launch and unattended policy support are removed.
**Migration**: Not applicable; the provider is deleted before the next release.
