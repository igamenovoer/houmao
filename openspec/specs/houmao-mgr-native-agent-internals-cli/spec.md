## Purpose

Define the internal provider-aligned native-agent command surface used to inspect and mutate compatibility launch material outside ordinary Houmao project workflows.

## Requirements

### Requirement: `houmao-mgr internals native-agent` exposes provider-aligned native launch material
`houmao-mgr` SHALL expose an internal command family shaped as:

```text
houmao-mgr internals native-agent <resource> <verb>
```

At minimum, `internals native-agent` SHALL expose:

- `roles list|get|init|set|remove`
- `recipes list|get|add|set|remove`
- `launch-dossiers list|get|add|set|remove`
- `tools <tool> get`
- `tools <tool> setups list|get|add|remove`

The command family SHALL present these resources as provider-aligned native-agent material rather than ordinary Houmao project resources.

#### Scenario: Operator sees native-agent internals
- **WHEN** an operator runs `houmao-mgr internals native-agent --help`
- **THEN** the help output lists native-agent roles, recipes, launch dossiers, and tools
- **AND THEN** the help output presents the family as internal provider-aligned material rather than project specialist/profile management

### Requirement: Native-agent internals use explicit native-agent root selection
Direct `internals native-agent` commands SHALL resolve their target native-agent root without requiring or discovering a Houmao project.

The native-agent root resolution order SHALL be:

1. an explicit `--native-agent-root` option when supplied by the command,
2. `HOUMAO_NATIVE_AGENT_ROOT` when set to a non-empty absolute path,
3. an actionable missing-root error.

`HOUMAO_NATIVE_AGENT_ROOT` SHALL replace `HOUMAO_AGENT_DEF_DIR` for maintained native-agent internals. The system MAY continue to recognize `HOUMAO_AGENT_DEF_DIR` only as a temporary compatibility input with deprecation diagnostics.

#### Scenario: Explicit native-agent root is used without project discovery
- **WHEN** no Houmao project exists in the current directory or its parents
- **AND WHEN** an operator runs `houmao-mgr internals native-agent roles list --native-agent-root /tmp/native-agents`
- **THEN** the command reads roles from `/tmp/native-agents`
- **AND THEN** it does not search for or bootstrap a `.houmao` project overlay

#### Scenario: Missing native-agent root fails clearly
- **WHEN** no explicit native-agent root is supplied
- **AND WHEN** `HOUMAO_NATIVE_AGENT_ROOT` is unset
- **AND WHEN** an operator runs `houmao-mgr internals native-agent recipes list`
- **THEN** the command fails clearly
- **AND THEN** the error tells the operator to pass `--native-agent-root` or set `HOUMAO_NATIVE_AGENT_ROOT`

### Requirement: Launch dossiers replace internal launch-profile terminology
The native-agent internals surface SHALL use `launch dossier` for recipe-backed native launch defaults.

Launch dossiers SHALL remain provider-aligned native launch material. They SHALL NOT be described as Houmao project profiles, easy profiles, or ordinary user-facing agent profiles.

#### Scenario: Launch dossier help avoids profile terminology
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers --help`
- **THEN** the help output describes launch dossiers as recipe-backed native launch material
- **AND THEN** it does not call them project profiles or easy profiles

### Requirement: Projects may project catalog state into native-agent material
Houmao project commands SHALL be allowed to materialize catalog-backed specialists, profiles, credentials, skills, and tool setup selections into native-agent roles, recipes, launch dossiers, and tool trees for provider compatibility.

That projection SHALL be one-way from the project model for ordinary project workflows. Direct `internals native-agent` commands SHALL NOT mutate the project catalog only because they changed a native-agent root.

#### Scenario: Project launch uses native projection without exposing it as project state
- **WHEN** an operator launches a project profile
- **THEN** Houmao may materialize native-agent recipes or launch dossiers needed by the provider launch path
- **AND THEN** the ordinary command output still reports project specialist/profile/managed-agent concepts rather than native-agent internals

#### Scenario: Direct native edit does not rewrite project catalog
- **WHEN** an operator runs `houmao-mgr internals native-agent recipes set --native-agent-root /tmp/native-agents --name reviewer --tool codex`
- **THEN** the command mutates the selected native-agent root
- **AND THEN** it does not update any Houmao project catalog unless a separate project import or mutation command is run
