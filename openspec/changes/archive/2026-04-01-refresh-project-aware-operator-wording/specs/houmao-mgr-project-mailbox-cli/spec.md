## ADDED Requirements

### Requirement: Project mailbox wording describes the selected overlay mailbox root
Maintained `houmao-mgr project mailbox ...` help text, failures, and operator-facing result wording SHALL describe the mailbox scope as the selected overlay mailbox root rather than as a hard-coded current-project `.houmao/mailbox` path.

When `project mailbox init` or another stateful project-mailbox command bootstraps the selected overlay implicitly, the operator-facing result SHALL surface that bootstrap outcome explicitly.

When a non-creating project-mailbox command cannot resolve an active overlay, the failure SHALL describe the selected overlay root for that invocation and that the command did not fall back to the generic shared mailbox root.

#### Scenario: Help text describes the selected overlay mailbox root
- **WHEN** an operator runs `houmao-mgr project mailbox --help`
- **THEN** the help output describes the surface as mailbox-root operations against `mailbox/` under the selected project overlay
- **AND THEN** it does not imply that the command only targets a caller-local literal `.houmao/mailbox` path

#### Scenario: Missing overlay failure stays tied to the selected overlay root
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** no project overlay exists there
- **AND WHEN** an operator runs a maintained non-creating `houmao-mgr project mailbox ...` command
- **THEN** the failure identifies `/tmp/ci-overlay` as the selected overlay root for that invocation
- **AND THEN** it states that the command did not fall back to the generic shared mailbox root
