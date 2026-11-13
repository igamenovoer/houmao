## MODIFIED Requirements

### Requirement: System-skills CLI exposes pack lifecycle commands
`houmao-mgr system-skills` SHALL expose `list`, `install`, `status`, `doctor`, `upgrade`, and `uninstall` for Houmao system-skill packs.

The command group SHALL manage standalone pack projections and the tool-scoped skill config. It SHALL NOT expose parent-scoped shared children or provider-native system-prompt files as independent install units.

#### Scenario: Operator opens system-skills help
- **WHEN** an operator runs `houmao-mgr system-skills --help`
- **THEN** help lists all six lifecycle and diagnostic commands
- **AND THEN** it describes shared children as parent-scoped routes rather than install selectors

#### Scenario: Operator inspects a Kimi system-skill pack
- **WHEN** an operator runs a system-skill lifecycle command against a managed Kimi home
- **THEN** the command scopes its output and mutations to catalog-backed skill projections and skill config
- **AND THEN** it neither lists nor mutates `<KIMI_CODE_HOME>/SYSTEM.md`
