## ADDED Requirements

### Requirement: CLI reference documents the `agents gateway reminders` subgroup
The CLI reference SHALL document `houmao-mgr agents gateway reminders` as a first-class subgroup of `agents gateway`.

At minimum, that coverage SHALL include:

- `list`
- `get`
- `create`
- `set`
- `remove`

The `agents-gateway` reference page SHALL provide full option tables and brief usage guidance for those reminder commands.

That reminder coverage SHALL explain:

- the same managed-agent selector rules used by the rest of `agents gateway`,
- that reminder commands work through pair-managed authority when `--pair-port` is used,
- that ranking remains numeric,
- that `--before-all` places a reminder ahead of the current minimum ranking,
- that `--after-all` places a reminder after the current maximum ranking,
- that direct `/v1/reminders` remains the lower-level gateway contract underneath the CLI.

#### Scenario: Reader finds all reminder subcommands from the `agents gateway` CLI reference
- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md`
- **THEN** the page documents `reminders list`, `reminders get`, `reminders create`, `reminders set`, and `reminders remove`
- **AND THEN** the reminder subgroup appears alongside the other current `agents gateway` operator surfaces rather than as an undocumented exception

#### Scenario: Reader can understand ranking placement flags from the CLI reference
- **WHEN** a reader looks up `houmao-mgr agents gateway reminders create` or `set`
- **THEN** the option tables and prose explain `--ranking`, `--before-all`, and `--after-all`
- **AND THEN** the page makes clear that ranking is numeric and that the convenience flags resolve to concrete numeric positions relative to the live reminder set
