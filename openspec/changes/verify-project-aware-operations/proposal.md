## Why

`make-operations-project-aware` is functionally implemented, but it is still blocked on broader coverage and end-to-end validation. The remaining risk is no longer design ambiguity; it is gaps in automated scenario coverage and missing proof that representative operator workflows still behave correctly with overlay-local defaults.

## What Changes

- Add an explicit verification matrix for the project-aware local-root contract across project, launch, mailbox, cleanup, and server surfaces.
- Add representative workflow validation requirements for maintained demos and interactive or operator-facing flows that now rely on overlay-local defaults.
- Record the focused automated and manual validation evidence needed to close the remaining `make-operations-project-aware` tasks.

## Capabilities

### New Capabilities
- `project-aware-verification-evidence`: Defines the required automated coverage matrix for overlay selection, implicit bootstrap, nested-repo boundary handling, overlay-local runtime or jobs or mailbox defaults, cleanup override behavior, and server-start behavior.
- `project-aware-workflow-validation`: Defines the representative demo and operator workflow validation needed to prove the project-aware contract works with fewer explicit root overrides.

### Modified Capabilities

## Impact

- `tests/unit/` and `tests/integration/` coverage for project-aware root selection and operator flows
- Maintained demo validation under `scripts/demo/` and related demo-focused tests
- OpenSpec completion evidence for `openspec/changes/make-operations-project-aware/`
