## ADDED Requirements

### Requirement: Generic mailbox help and rootless results describe project-aware mailbox selection
Maintained `houmao-mgr mailbox ...` help text and rootless result wording SHALL distinguish between an active project mailbox root and an explicit shared mailbox-root override.

When no explicit mailbox-root override wins and project context is active, operator-facing wording SHALL describe the resolved mailbox scope as the active project mailbox root.

When `--mailbox-root` or `HOUMAO_GLOBAL_MAILBOX_DIR` wins, operator-facing wording SHALL describe that scope as an explicit mailbox-root selection or shared mailbox-root override rather than as the active project mailbox root.

#### Scenario: Mailbox help text describes the active project mailbox root fallback
- **WHEN** an operator runs `houmao-mgr mailbox --help` or inspects a mailbox subcommand help page with `--mailbox-root`
- **THEN** the help output explains that rootless mailbox commands may default to the active project mailbox root
- **AND THEN** it does not present the shared mailbox root as the only maintained default

#### Scenario: Rootless mailbox bootstrap surfaces project-aware selection
- **WHEN** an operator runs a maintained rootless mailbox command in project context without `--mailbox-root`
- **AND WHEN** that invocation resolves mailbox state from the selected project overlay
- **THEN** the operator-facing result describes the resolved mailbox scope as the active project mailbox root
- **AND THEN** it does not describe that resolution as though the command had targeted an explicit shared mailbox-root override
