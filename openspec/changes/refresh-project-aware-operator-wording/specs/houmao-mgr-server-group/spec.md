## ADDED Requirements

### Requirement: Server help and startup wording describe project-aware runtime-root selection
Maintained `houmao-mgr server ...` and `houmao-server ...` operator-facing help text plus startup or status wording SHALL describe project-aware runtime-root selection consistently.

When no explicit runtime-root override wins and project context is active, help text SHALL describe the default server artifact scope as the active project runtime root.

When `--runtime-root` or `HOUMAO_GLOBAL_RUNTIME_DIR` wins, operator-facing wording SHALL describe that scope as an explicit runtime-root selection rather than as an active project runtime root.

#### Scenario: Server help text describes the project-aware runtime-root default
- **WHEN** an operator runs `houmao-mgr server start --help` or `houmao-server serve --help`
- **THEN** the help output explains that `--runtime-root` overrides the active project runtime root when project context is active
- **AND THEN** it does not imply that maintained server artifacts always default to the shared runtime root

#### Scenario: Startup result describes the resolved runtime-root source accurately
- **WHEN** an operator starts a server without an explicit runtime-root override in project context
- **THEN** the startup result describes the resolved server artifact scope as the active project runtime root
- **AND THEN** the wording changes when an explicit runtime-root override is supplied so the explicit override remains visible to the operator
