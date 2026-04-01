## ADDED Requirements

### Requirement: Representative project-aware workflows are validated before archive
Before `make-operations-project-aware` is archived, maintainers SHALL run representative maintained workflows that demonstrate the project-aware contract works with overlay-local defaults and fewer explicit root overrides.

#### Scenario: Maintained demo workflows prove overlay-local defaults
- **WHEN** maintainers run the representative workflow validation for this change
- **THEN** the validation MUST include maintained demo or operator workflows that now rely on overlay-local runtime or jobs or mailbox defaults, including the maintained minimal launch and single-agent mail wake-up surfaces or equivalent maintained replacements

#### Scenario: Validation evidence remains reproducible
- **WHEN** the representative workflow validation completes
- **THEN** the executed commands and their outcomes MUST be recorded in a repeatable form suitable for change close-out, rather than relying on ad hoc manual notes

### Requirement: Parent change readiness is re-checked after verification
The project-aware close-out flow SHALL re-check the parent OpenSpec change after the broader automated and representative workflow validation passes.

#### Scenario: Parent change is confirmed after broader validation
- **WHEN** the broader verification and representative workflow validation both pass
- **THEN** maintainers MUST re-run the parent change status or apply instructions for `make-operations-project-aware` and use that result as the readiness signal for archive
