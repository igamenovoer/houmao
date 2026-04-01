## ADDED Requirements

### Requirement: Runtime cleanup help and payload wording describe the resolved cleanup root consistently
Maintained `houmao-mgr admin cleanup runtime ...` help text and structured cleanup results SHALL describe the resolved runtime scope consistently with the project-aware root contract.

When no explicit runtime-root override wins and project context is active, help text SHALL describe the default cleanup scope as the active project runtime root.

When an explicit runtime-root override or global runtime-root env override wins, help text and cleanup results SHALL describe that scope as an explicit runtime-root selection rather than as an active project runtime root.

#### Scenario: Help text describes project-aware runtime cleanup defaults
- **WHEN** an operator runs `houmao-mgr admin cleanup runtime --help`
- **THEN** the help output explains that `--runtime-root` overrides the active project runtime root when project context is active
- **AND THEN** it does not imply that the maintained default is always a shared runtime root

#### Scenario: Cleanup result distinguishes explicit override from project-aware default
- **WHEN** an operator runs `houmao-mgr admin cleanup runtime sessions --runtime-root /tmp/houmao-runtime --dry-run`
- **THEN** the structured cleanup result identifies `/tmp/houmao-runtime` as the selected cleanup root for that invocation
- **AND THEN** the operator-facing wording does not describe that explicit override as the active project runtime root
