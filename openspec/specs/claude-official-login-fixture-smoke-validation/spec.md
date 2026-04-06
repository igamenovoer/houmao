## Purpose
Define the local-only Claude `official-login` fixture contract and the reproducible smoke-validation flow for vendor login-state launches.

## Requirements

### Requirement: Repository defines one local-only `official-login` Claude auth fixture for vendor-login smoke validation
The repository SHALL reserve `tests/fixtures/agents/tools/claude/auth/official-login/` as the supported local-only Claude vendor-login smoke bundle.

That bundle SHALL use the current Claude adapter filenames:

- `files/.credentials.json`
- `files/.claude.json`

`files/.credentials.json` SHALL be copied opaquely from vendor Claude login-state and SHALL NOT be normalized into a Houmao-specific format.

`files/.claude.json` SHALL be a valid JSON object and MAY be minimized to only the seed state needed for Houmao-managed unattended startup, including `{}`.

The supported `official-login` lane SHALL NOT require `claude_state.template.json`.

Repository fixture guidance SHALL describe `official-login` as local-only host state and SHALL NOT instruct maintainers to commit plaintext secret material.

#### Scenario: Fixture guidance describes the `official-login` local-only bundle with current filenames
- **WHEN** a maintainer reads the fixture guidance for `tests/fixtures/agents/tools/claude/auth/official-login/`
- **THEN** that guidance identifies `files/.credentials.json` and `files/.claude.json` as the supported vendor-login smoke inputs
- **AND THEN** it describes `claude_state.template.json` as unnecessary for this lane
- **AND THEN** it marks the bundle as local-only host state that must not be committed in plaintext

#### Scenario: Maintainer can populate `official-login` from a vendor Claude config root
- **WHEN** a maintainer prepares `tests/fixtures/agents/tools/claude/auth/official-login/` from an existing Claude login
- **THEN** they can copy vendor `.credentials.json` into `files/.credentials.json`
- **AND THEN** they can provide a minimized valid JSON object as `files/.claude.json`
- **AND THEN** the resulting bundle matches the current Claude adapter projection contract

### Requirement: Repository provides a reproducible `official-login` Claude smoke launch flow
The repository SHALL provide one reproducible local smoke-validation flow that launches a Claude agent from a fresh temporary workdir using the `official-login` auth bundle.

That flow SHALL:

- use a launch workdir under `tmp/<subdir>`
- set `HOUMAO_AGENT_DEF_DIR` to the `tests/fixtures/agents` root
- launch the existing `server-api-smoke` Claude preset through maintained `houmao-mgr agents launch`
- run with `--provider claude_code`
- override auth selection to `--auth official-login`
- use `--headless` and `--yolo` so the check is non-interactive and reproducible

The expected outcome SHALL be a successful Claude launch that uses the fresh temp workdir as the session workdir and does not depend on `claude_state.template.json`.

#### Scenario: Smoke flow launches from a fresh temp workdir with the local fixture root
- **WHEN** a maintainer runs the supported `official-login` smoke-validation flow
- **THEN** the command executes from a workdir under `tmp/`
- **AND THEN** it sets `HOUMAO_AGENT_DEF_DIR` to `tests/fixtures/agents`
- **AND THEN** it launches `server-api-smoke` with `--provider claude_code --auth official-login --headless --yolo`

#### Scenario: Smoke flow proves projected vendor login-state works without a state template
- **WHEN** `official-login` contains `files/.credentials.json` and a minimized `files/.claude.json`
- **AND WHEN** the smoke-validation flow launches Claude from a fresh temp workdir
- **THEN** the launch succeeds without requiring `claude_state.template.json`
- **AND THEN** the runtime uses the projected vendor login-state files for the isolated Claude home
