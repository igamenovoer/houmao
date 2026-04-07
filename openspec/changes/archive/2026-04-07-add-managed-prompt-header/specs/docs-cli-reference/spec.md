## ADDED Requirements

### Requirement: CLI reference documents managed-header controls on launch and launch-profile surfaces
The `houmao-mgr` CLI reference SHALL document the managed-header flags on the relevant launch and launch-profile commands.

At minimum, that coverage SHALL include:
- `houmao-mgr agents launch --managed-header|--no-managed-header`
- `houmao-mgr project agents launch-profiles add --managed-header|--no-managed-header`
- `houmao-mgr project agents launch-profiles set --managed-header|--no-managed-header|--clear-managed-header`
- `houmao-mgr project easy profile create --managed-header|--no-managed-header`
- `houmao-mgr project easy instance launch --managed-header|--no-managed-header`

The CLI reference SHALL explain that:
- launch-time managed-header flags are mutually exclusive,
- direct launch override wins over stored launch-profile policy,
- clearing stored launch-profile policy returns that field to inherit behavior,
- omitted launch-time and launch-profile policy falls back to the default enabled managed-header behavior.

#### Scenario: Reader can find the managed-header flags in the CLI reference
- **WHEN** a reader looks up `houmao-mgr agents launch`, `project agents launch-profiles`, or the relevant `project easy` commands
- **THEN** the CLI reference documents the managed-header flags and their meaning
- **AND THEN** the page does not require the reader to infer the new behavior from source code or changelog text

#### Scenario: Reader understands precedence and clear semantics from the CLI reference
- **WHEN** a reader checks the option notes for managed-header controls
- **THEN** the CLI reference explains direct-override precedence over stored profile policy
- **AND THEN** it explains that `--clear-managed-header` returns the stored profile field to inherit behavior
