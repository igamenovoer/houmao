## ADDED Requirements

### Requirement: Run-phase reference excludes Gemini
Maintained backend, launch-plan, manifest, lifecycle, role-injection, gateway, and realm-controller documentation SHALL not describe Gemini runtime behavior.

#### Scenario: Runtime reference lists backends
- **WHEN** a reader inspects current run-phase backend and schema guidance
- **THEN** `gemini_cli` and `gemini_headless` are absent from supported values and examples
