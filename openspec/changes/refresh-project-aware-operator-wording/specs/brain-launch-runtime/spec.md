## ADDED Requirements

### Requirement: Project-aware build and launch results describe selected local roots explicitly
Maintained project-aware build and launch surfaces SHALL describe overlay-local default roots, explicit root overrides, and implicit overlay bootstrap in operator-facing result text and machine-readable payload details.

When a maintained build or launch flow resolves runtime or jobs state from the selected project overlay, the result SHALL describe that scope as the active project runtime root or overlay-local jobs scope rather than as a generic shared-root default.

When a maintained build or launch flow implicitly bootstraps the selected overlay, the operator-facing result SHALL surface that bootstrap outcome explicitly instead of requiring the operator to infer it from created files on disk.

#### Scenario: Project-aware build reports overlay-local runtime selection and bootstrap
- **WHEN** an operator runs a maintained project-aware build or launch command without an explicit runtime-root override
- **AND WHEN** the command bootstraps the selected overlay for that invocation
- **THEN** the operator-facing result describes the resolved runtime scope as the active project runtime root under the selected overlay
- **AND THEN** the result surfaces that the overlay was bootstrapped implicitly during that invocation

#### Scenario: Explicit runtime override remains described as an explicit override
- **WHEN** an operator runs a maintained build or launch command with an explicit runtime-root override
- **THEN** the operator-facing result describes that root as an explicit runtime-root override
- **AND THEN** it does not describe that path as though it were the active project runtime root selected from overlay-local defaults
