## MODIFIED Requirements

### Requirement: Native-agent internals expose direct brain build plumbing
`houmao-mgr internals native-agent` SHALL expose direct brain build plumbing shaped as:

```text
houmao-mgr internals native-agent brain build
```

The command SHALL build one local brain home from selected native-agent material and runtime build options. It SHALL use the selected native-agent root instead of a public `--agent-def-dir` option.

The `--preset` selector SHALL support:

- a bare preset name resolved from `presets/<name>.yaml` under the selected native-agent root,
- an absolute filesystem path to one preset YAML file,
- an existing relative filesystem path resolved from the invocation working directory.

When a selected preset explicitly declares `skills: []`, the command SHALL treat that as an intentional request to project no user fixture skills and SHALL NOT fail only because no `--skill` option was supplied.

When no selected preset supplies a skills list and no `--skill` option is supplied, the command SHALL continue to fail clearly with a missing skill input diagnostic.

#### Scenario: Operator builds brain from selected native-agent root
- **WHEN** `/tmp/native/presets/reviewer.yaml` exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent brain build --native-agent-root /tmp/native --preset reviewer`
- **THEN** the command builds a runtime brain home from `/tmp/native`
- **AND THEN** the output reports the generated home, launch helper, manifest, and runtime root

#### Scenario: Brain build is not presented as ordinary project workflow
- **WHEN** an operator runs `houmao-mgr project --help`
- **THEN** the help output does not list direct brain build commands
- **AND THEN** ordinary project launch remains available through `project agents launch`

#### Scenario: Brain build accepts an existing cwd-relative preset path
- **WHEN** the invocation cwd contains `tests/fixtures/plain-agent-def/presets/server-api-smoke-claude-default.yaml`
- **AND WHEN** an operator runs `houmao-mgr internals native-agent brain build --native-agent-root tests/fixtures/plain-agent-def --preset tests/fixtures/plain-agent-def/presets/server-api-smoke-claude-default.yaml`
- **THEN** the command resolves the preset from that existing cwd-relative path
- **AND THEN** it does not incorrectly append the full relative path under the native root `presets/` directory

#### Scenario: Brain build accepts explicit empty skills from preset
- **WHEN** a selected preset explicitly contains `skills: []`
- **AND WHEN** the operator does not pass any `--skill` option
- **THEN** the command treats the preset as selecting no user fixture skills
- **AND THEN** it continues resolving the remaining required inputs from the preset and CLI options

#### Scenario: Brain build still rejects missing skill input without preset skills
- **WHEN** no selected preset supplies a skills list
- **AND WHEN** the operator does not pass any `--skill` option
- **THEN** the command fails clearly with a missing skill input diagnostic
