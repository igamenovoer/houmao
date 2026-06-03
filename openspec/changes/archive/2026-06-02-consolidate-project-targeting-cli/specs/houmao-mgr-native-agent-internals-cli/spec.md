## ADDED Requirements

### Requirement: Native-agent internals expose direct credential management
`houmao-mgr internals native-agent` SHALL expose direct native-agent credential management shaped as:

```text
houmao-mgr internals native-agent credentials <tool> <verb>
```

At minimum, the credentials family SHALL expose tool lanes for `claude`, `codex`, and `gemini`, and verbs `list`, `get`, `add`, `set`, `rename`, `remove`, and `login` when those verbs are retained for direct native-agent roots.

Credential commands SHALL operate on the selected native-agent root and SHALL NOT discover or mutate a Houmao project catalog.

#### Scenario: Operator sees native credential internals
- **WHEN** an operator runs `houmao-mgr internals native-agent credentials --help`
- **THEN** the help output lists the supported tool lanes
- **AND THEN** the help output presents the command family as direct native-agent credential management

#### Scenario: Native credential command does not discover project
- **WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** `/tmp/native/tools/codex/auth/work/` exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent credentials codex get --native-agent-root /tmp/native --name work`
- **THEN** the command reads credential material from `/tmp/native`
- **AND THEN** it does not mutate `/repo/.houmao/catalog.sqlite`

### Requirement: Native-agent internals expose direct brain build plumbing
`houmao-mgr internals native-agent` SHALL expose direct brain build plumbing shaped as:

```text
houmao-mgr internals native-agent brain build
```

The command SHALL build one local brain home from selected native-agent material and runtime build options. It SHALL use the selected native-agent root instead of a public `--agent-def-dir` option.

#### Scenario: Operator builds brain from selected native-agent root
- **WHEN** `/tmp/native/presets/reviewer.yaml` exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent brain build --native-agent-root /tmp/native --preset reviewer`
- **THEN** the command builds a runtime brain home from `/tmp/native`
- **AND THEN** the output reports the generated home, launch helper, manifest, and runtime root

#### Scenario: Brain build is not presented as ordinary project workflow
- **WHEN** an operator runs `houmao-mgr project --help`
- **THEN** the help output does not list direct brain build commands
- **AND THEN** ordinary project launch remains available through `project agents launch`
