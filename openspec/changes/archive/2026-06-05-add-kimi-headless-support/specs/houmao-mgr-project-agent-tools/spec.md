## MODIFIED Requirements

### Requirement: `houmao-mgr internals native-agent tools` mirrors the project-local tool tree
`houmao-mgr` SHALL expose a project-local tool administration subtree shaped as:

```text
houmao-mgr internals native-agent tools <tool> get
houmao-mgr internals native-agent tools <tool> setups <verb>
```

At minimum, `internals native-agent tools` SHALL expose Houmao-owned tool families for:

- `claude`
- `codex`
- `gemini`
- `kimi`

At minimum, each supported tool family SHALL expose:

- `get`
- `setups`

The help text for this subtree SHALL present it as management for project-local tool content under `.houmao/agents/tools/<tool>/`.

This subtree SHALL NOT own credential CRUD, which SHALL route through `houmao-mgr project credentials <tool> ...`.

#### Scenario: Operator sees the internals native-agent tools tree
- **WHEN** an operator runs `houmao-mgr internals native-agent tools --help`
- **THEN** the help output lists the supported tool families
- **AND THEN** the help output presents `internals native-agent tools` as management for `.houmao/agents/tools/`

#### Scenario: Operator sees the setup verbs for one tool
- **WHEN** an operator runs `houmao-mgr internals native-agent tools claude --help`
- **THEN** the help output presents `get` and `setups`
- **AND THEN** those commands are described as operations on `.houmao/agents/tools/claude/`

#### Scenario: Operator sees the Kimi tool family
- **WHEN** an operator runs `houmao-mgr internals native-agent tools kimi --help`
- **THEN** the help output presents `get` and `setups`
- **AND THEN** those commands are described as operations on `.houmao/agents/tools/kimi/`

## ADDED Requirements

### Requirement: Starter Kimi adapter defines managed home, launch, skills, and auth projection
The starter agent definition SHALL include a Kimi tool adapter and default setup bundle suitable for managed headless launches.

The Kimi adapter SHALL declare:

- `tool: kimi`,
- home selector env var `KIMI_CODE_HOME`,
- default launch executable `kimi`,
- skills projection destination `skills`,
- setup projection destination `.`,
- auth file projection for Kimi config and credential storage, and
- an auth env allowlist for Kimi env-model and Kimi Code endpoint override variables.

The starter adapter SHALL NOT embed one operator-specific absolute executable path.

#### Scenario: Starter Kimi adapter uses portable executable by default
- **WHEN** a project initializes or refreshes starter agent tool content
- **THEN** the Kimi adapter declares launch executable `kimi`
- **AND THEN** host-specific paths such as `/home/huangzhe/.kimi-code/bin/kimi` are not written into the starter template

#### Scenario: Kimi auth projection accepts OAuth token storage
- **WHEN** a selected Kimi auth bundle provides `config.toml` and `credentials/kimi-code.json`
- **THEN** the build projects those files into the constructed Kimi runtime home according to the Kimi adapter mapping
- **AND THEN** the build manifest records the projected credential paths without exposing token values
