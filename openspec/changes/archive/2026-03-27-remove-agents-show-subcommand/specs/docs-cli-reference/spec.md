## MODIFIED Requirements

### Requirement: houmao-mgr reference documents all command groups

The CLI reference SHALL include a page for `houmao-mgr` documenting its active command groups (`admin`, `agents`, `brains`, `mailbox`, and `server`) with subcommand summaries derived from `srv_ctrl/commands/` module docstrings, Click decorators, and live help output.

The CLI reference SHALL make the major nested managed-agent command families discoverable either inline or through dedicated linked pages. At minimum, that coverage SHALL include:

- `agents launch`, `join`, `list`, `state`, `prompt`, `stop`, `interrupt`, and `relaunch`,
- `agents turn`,
- `agents gateway`,
- `agents mail`,
- `agents mailbox`,
- `agents cleanup`,
- `admin cleanup`.

#### Scenario: Reader finds current agent lifecycle commands

- **WHEN** a reader looks up `houmao-mgr agents`
- **THEN** they find documented subcommands for launch, join, list, state, prompt, stop, interrupt, relaunch, turn, mail, mailbox, cleanup, and gateway operations
- **AND THEN** the CLI reference does not present removed or outdated group names such as `passthrough` as active command groups

#### Scenario: Reader can discover nested managed-agent command families

- **WHEN** a reader needs details for `agents gateway`, `agents turn`, `agents mail`, `agents mailbox`, or `admin cleanup`
- **THEN** the CLI reference provides a direct path to formal reference coverage for those nested families
- **AND THEN** the reader does not need to reconstruct those command surfaces only from source code or scattered prose pages

#### Scenario: Reader finds brain management commands

- **WHEN** a reader looks up `houmao-mgr brains`
- **THEN** they find documented subcommands for load, list, and build operations
