## ADDED Requirements

### Requirement: Resume-only local control does not reapply unattended provider-home mutations
For runtime-owned sessions whose resolved brain manifest requests `operator_prompt_mode = unattended`, resumed local control paths that do not start or relaunch a provider process SHALL NOT rewrite strategy-owned provider bootstrap files solely to inspect or control an already-live session.

At minimum, resumed local commands such as state queries, detail queries, prompt submission, interrupt submission, and local gateway lifecycle or status operations for an already-live session SHALL be able to reuse persisted launch metadata without re-running unattended file mutations against provider-owned bootstrap files such as Claude `settings.json` or `.claude.json`.

When a resumed path must prepare a new provider start or relaunch for that session, any strategy-owned provider-home mutation SHALL run only inside an explicit pre-start mutation phase rather than as an unconditional side effect of session resume.

#### Scenario: Read-only state query skips unattended provider-home mutation for a live session
- **WHEN** a developer runs `houmao-mgr agents state --agent-name gpu` against a live runtime-owned Claude local interactive session whose brain manifest requests `operator_prompt_mode = unattended`
- **THEN** the runtime resumes the session authority without rewriting strategy-owned Claude bootstrap files
- **AND THEN** the query does not fail merely because another local control command is touching the same runtime home

#### Scenario: Gateway status query skips unattended provider-home mutation for a live session
- **WHEN** a developer runs `houmao-mgr agents gateway status --agent-name gpu` against a live runtime-owned unattended Claude session
- **THEN** the runtime resolves the live gateway state without re-running provider-home mutation actions
- **AND THEN** the query does not depend on rewriting `settings.json` or `.claude.json` for that already-live session

### Requirement: Strategy-owned provider-home mutation is serialized and atomically committed
When the runtime must create, patch, or repair strategy-owned provider-home files for unattended start or relaunch, it SHALL serialize that mutation per runtime home and SHALL commit each finished file atomically so concurrent processes do not observe a truncated or partially written file.

This guarantee SHALL apply to every strategy-owned persisted file format used by the shared unattended launch-policy helpers, including JSON and TOML state.

If a previously strategy-owned file is blank or malformed due to a prior interrupted write, the runtime MAY repair that file only inside the serialized pre-start mutation phase for a declared owned path.

#### Scenario: Concurrent control paths do not observe a truncated strategy-owned JSON file
- **WHEN** two local processes address the same unattended runtime-owned session concurrently
- **AND WHEN** one process enters a pre-start mutation phase for a strategy-owned JSON file in that runtime home
- **THEN** the other process does not observe a zero-byte or partially written JSON file from that mutation
- **AND THEN** the other process does not fail with a malformed-state error caused only by an in-progress strategy-owned write

#### Scenario: Relaunch repair replaces the finished strategy-owned file atomically
- **WHEN** a relaunch path for an unattended runtime-owned Claude session must repair or rewrite strategy-owned `settings.json` or `.claude.json`
- **THEN** the runtime serializes that repair for the runtime home
- **AND THEN** each finished file becomes visible through one atomic replacement step rather than through truncate-then-write

#### Scenario: Blank strategy-owned file is repairable on the next provider-start phase
- **WHEN** a strategy-owned provider-home file for an unattended session is found blank during an explicit provider-start or relaunch phase
- **THEN** the runtime may rebuild that declared owned file from its strategy-owned baseline inside the serialized pre-start mutation phase
- **AND THEN** ordinary read-only resumed control does not need to perform that repair itself
