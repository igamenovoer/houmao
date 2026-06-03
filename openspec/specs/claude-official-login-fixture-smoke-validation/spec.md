## Purpose
Define the local-only Claude `official-login` fixture contract and the reproducible smoke-validation flow for vendor login-state launches.
## Requirements
### Requirement: Repository defines one local-only `official-login` Claude auth fixture for vendor-login smoke validation
The repository SHALL reserve `tests/fixtures/auth-bundles/claude/official-login/` as the supported local-only Claude vendor-login smoke bundle.

That bundle SHALL use the current Claude adapter filenames:

- `files/.credentials.json`
- `files/.claude.json`

`files/.credentials.json` SHALL be copied opaquely from vendor Claude login-state and SHALL NOT be normalized into a Houmao-specific format.

`files/.claude.json` SHALL be a valid JSON object and MAY be minimized to only the seed state needed for Houmao-managed unattended startup, including `{}`.

The supported `official-login` lane SHALL NOT require `claude_state.template.json`.

Repository fixture guidance SHALL describe `official-login` as local-only host state and SHALL NOT instruct maintainers to commit plaintext secret material.

#### Scenario: Fixture guidance describes the `official-login` local-only bundle with current filenames
- **WHEN** a maintainer reads the fixture guidance for `tests/fixtures/auth-bundles/claude/official-login/`
- **THEN** that guidance identifies `files/.credentials.json` and `files/.claude.json` as the supported vendor-login smoke inputs
- **AND THEN** it describes `claude_state.template.json` as unnecessary for this lane
- **AND THEN** it marks the bundle as local-only host state that must not be committed in plaintext

#### Scenario: Maintainer can populate `official-login` from a vendor Claude config root
- **WHEN** a maintainer prepares `tests/fixtures/auth-bundles/claude/official-login/` from an existing Claude login
- **THEN** they can copy vendor `.credentials.json` into `files/.credentials.json`
- **AND THEN** they can provide a minimized valid JSON object as `files/.claude.json`
- **AND THEN** the resulting bundle matches the current Claude adapter projection contract

### Requirement: Repository provides a reproducible `official-login` Claude smoke launch flow
The repository SHALL provide one reproducible local smoke-validation flow that launches a Claude agent from a fresh temporary workdir using the `official-login` auth bundle.

That flow SHALL:

- use a launch workdir under `tmp/<subdir>`
- source prompt material from the existing `server-api-smoke` role in `tests/fixtures/plain-agent-def/`
- source local-only auth material from `tests/fixtures/auth-bundles/claude/official-login/`
- create a fresh temporary Houmao project overlay for the smoke run
- materialize the `official-login` credential into that temporary project through maintained project credential or specialist creation commands
- create or update a temporary project specialist for the `server-api-smoke` prompt
- launch the temporary specialist through maintained `houmao-mgr project agents launch`
- override auth selection to `official-login` when the launch path does not already bind that credential
- use `--headless`, while the selected launch posture remains unattended, so the check is non-interactive and reproducible
- stop and clean up the launched local managed agent through `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`

The supported flow SHALL NOT use retired root-level `houmao-mgr agents launch`, `houmao-mgr agents stop`, or `houmao-mgr agents cleanup` command paths.

The expected outcome SHALL be a successful Claude launch that uses the fresh temp workdir as the session workdir and does not depend on `claude_state.template.json`.

#### Scenario: Smoke flow launches from a fresh temp workdir with a temporary project overlay
- **WHEN** a maintainer runs the supported `official-login` smoke-validation flow
- **THEN** the command executes from a workdir under `tmp/`
- **AND THEN** it creates one temporary Houmao project overlay for the smoke run
- **AND THEN** it sources prompt material from `tests/fixtures/plain-agent-def/roles/server-api-smoke/system-prompt.md`
- **AND THEN** it materializes `official-login` from `tests/fixtures/auth-bundles/claude/official-login/` into that temporary project
- **AND THEN** it launches the smoke specialist through `houmao-mgr project agents launch --headless`

#### Scenario: Smoke flow proves projected vendor login-state works without a state template
- **WHEN** `official-login` contains `files/.credentials.json` and a minimized `files/.claude.json`
- **AND WHEN** the smoke-validation flow launches Claude from a fresh temp workdir with a temporary project overlay
- **THEN** the launch succeeds without requiring `claude_state.template.json`
- **AND THEN** the runtime uses the projected vendor login-state files for the isolated Claude home

#### Scenario: Smoke flow uses scoped selected-agent cleanup
- **WHEN** the smoke-validation flow has launched one local managed agent and captured its `agent_id`
- **THEN** it stops that agent with `houmao-mgr agents single --agent-id <agent_id> stop`
- **AND THEN** any maintained session cleanup uses `houmao-mgr agents single --agent-id <agent_id> cleanup session`
- **AND THEN** the flow does not call root-level `houmao-mgr agents stop` or `houmao-mgr agents cleanup`

