## MODIFIED Requirements

### Requirement: The restored demo SHALL generate a run-local agent-definition directory for each run
Each live-watch or recorded-capture run SHALL generate a local working tree under the run root and SHALL build from a generated agent-definition directory inside that working tree instead of building directly from a repository-wide plain direct-dir fixture root.

The generated agent-definition directory SHALL be derived from the tracked demo-local `inputs/agents/` tree.

#### Scenario: Live watch builds from the generated local agent tree
- **WHEN** an operator starts a live-watch run for Claude or Codex
- **THEN** the workflow creates a generated agent-definition directory under that run’s working tree
- **AND THEN** the runtime build for that run uses the generated local agent-definition directory rather than a repository-wide plain direct-dir fixture root

#### Scenario: Recorded capture builds from the generated local agent tree
- **WHEN** an operator starts a recorded-capture run for one configured scenario
- **THEN** the workflow creates a generated agent-definition directory under that run’s working tree
- **AND THEN** the runtime build for that run uses the generated local agent-definition directory rather than a repository-wide plain direct-dir fixture root

### Requirement: The restored demo SHALL materialize a demo-local `default` auth alias for the selected tool
The restored demo run workflow SHALL create a generated working tree for each run and SHALL materialize one demo-local auth alias named `default` for the selected tool by linking or projecting to a host-local fixture auth bundle under `tests/fixtures/auth-bundles/<tool>/`.

Tracked demo presets MAY therefore continue to declare `auth: default`.

If the expected host-local auth source for the selected tool is absent, the demo SHALL fail before launch with a clear error identifying the missing path.

#### Scenario: Claude run creates a local default auth alias
- **WHEN** an operator starts the restored demo for Claude
- **THEN** the generated working tree contains `tools/claude/auth/default` for that run
- **AND THEN** that alias resolves to one host-local fixture auth source under `tests/fixtures/auth-bundles/claude/`

#### Scenario: Codex run creates a local default auth alias
- **WHEN** an operator starts the restored demo for Codex
- **THEN** the generated working tree contains `tools/codex/auth/default` for that run
- **AND THEN** that alias resolves to one host-local fixture auth source under `tests/fixtures/auth-bundles/codex/`

#### Scenario: Missing local auth source fails during preflight
- **WHEN** an operator starts the restored demo for one supported tool
- **AND WHEN** the expected host-local fixture auth source for that tool is absent
- **THEN** the demo fails before launch
- **AND THEN** the error identifies the missing auth source path
