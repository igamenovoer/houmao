## ADDED Requirements

### Requirement: `houmao-mgr` root error handling does not leak uncaught maintained-command exceptions as Python tracebacks

The top-level `houmao-mgr` wrapper SHALL convert uncaught exceptions from maintained native command trees into non-zero CLI error output rather than allowing a Python traceback to reach the operator.

This SHALL apply to maintained native subcommands under:

- `server`
- `agents`
- `brains`
- `credentials`
- `admin`
- `mailbox`
- `project`
- `system-skills`

When a maintained command already normalizes a failure as explicit operator-facing CLI error output, the root wrapper SHALL preserve that non-zero failure behavior rather than treating the command as successful.

When a maintained command still leaks a non-click exception to the root wrapper, the wrapper SHALL render stable CLI error text instead of a Python traceback and SHALL preserve non-zero exit behavior.

#### Scenario: Project mailbox failure that reaches the root wrapper still renders without traceback

- **WHEN** an operator runs `houmao-mgr project mailbox accounts list`
- **AND WHEN** that maintained command leaks a mailbox-related exception to the top-level wrapper
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** the operator sees CLI error text instead of a Python traceback

#### Scenario: Project recipe failure that reaches the root wrapper still renders without traceback

- **WHEN** an operator runs `houmao-mgr project agents recipes list`
- **AND WHEN** that maintained command leaks a malformed-preset parsing exception to the top-level wrapper
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** the operator sees CLI error text instead of a Python traceback
