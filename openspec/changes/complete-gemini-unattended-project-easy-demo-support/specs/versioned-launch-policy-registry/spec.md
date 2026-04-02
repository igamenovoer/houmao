## ADDED Requirements

### Requirement: Registry declares maintained Gemini unattended headless strategy coverage
The launch-policy registry SHALL include maintained Gemini unattended strategy coverage for the `gemini_headless` backend.

That Gemini strategy coverage SHALL remain version-scoped and SHALL declare:

- the compatible Gemini CLI version range,
- the minimal input contract needed after provider selection is resolved,
- evidence provenance for the maintained no-prompt behavior assumptions,
- any runtime-owned Gemini startup surfaces or provider hooks Houmao must control,
- the ordered actions needed before Gemini provider start.

The Gemini strategy metadata SHALL separate credential readiness from unattended startup compatibility and SHALL describe Gemini's maintained auth readiness in terms of the already-supported Gemini auth families rather than inventing a separate unattended-only auth contract.

#### Scenario: Maintainer inspects Gemini unattended strategy metadata
- **WHEN** a maintainer inspects the launch-policy registry entry that covers maintained Gemini unattended startup
- **THEN** the entry declares `gemini_headless` as a supported backend
- **AND THEN** it declares the compatible Gemini version range, evidence basis, owned startup surfaces or hooks, and ordered actions
- **AND THEN** it keeps credential readiness distinct from the unattended startup ownership model
