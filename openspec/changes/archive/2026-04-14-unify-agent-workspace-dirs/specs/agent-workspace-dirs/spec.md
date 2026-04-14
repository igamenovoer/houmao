## ADDED Requirements

### Requirement: Managed agents expose one workspace envelope with scratch and persist lanes
For each tmux-backed managed agent, Houmao SHALL resolve a per-agent workspace envelope rooted by default at `<active-overlay>/memory/agents/<agent-id>/`.

The workspace envelope SHALL contain a `scratch/` lane for short-lived local work and a `persist/` lane for durable agent memory when persistence is enabled.

The workspace envelope SHALL contain a first-class `houmao-memo.md` file for per-agent operational instructions, live-agent rules, loop initialization notes, delegation constraints, task-handling rules, obligations, and forbidden actions.

The scratch lane SHALL replace the previous session-scoped `job_dir` contract. The persist lane SHALL replace the previous single `memory_dir` contract.

#### Scenario: Default workspace derives from the active overlay and agent id
- **WHEN** managed agent `researcher` has authoritative agent id `researcher-id`
- **AND WHEN** the active overlay resolves as `/repo/.houmao`
- **THEN** the default workspace root is `/repo/.houmao/memory/agents/researcher-id/`
- **AND THEN** the default memo file is `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** the default scratch lane is `/repo/.houmao/memory/agents/researcher-id/scratch/`
- **AND THEN** the default persist lane is `/repo/.houmao/memory/agents/researcher-id/persist/`

#### Scenario: Disabled persistence keeps scratch available
- **WHEN** a managed agent is launched with persistence disabled
- **THEN** Houmao still creates and publishes the workspace root
- **AND THEN** Houmao still creates and publishes the memo file
- **AND THEN** Houmao still creates and publishes the scratch lane
- **AND THEN** Houmao does not create or publish a persist lane for that launch

#### Scenario: Memo file is not overwritten
- **WHEN** managed agent `researcher` already has `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND WHEN** Houmao starts or relaunches that managed agent
- **THEN** Houmao preserves the existing memo file content
- **AND THEN** Houmao does not replace it with a default template

### Requirement: Managed agent workspace environment variables use lane names
For every tmux-backed managed session, Houmao SHALL publish `HOUMAO_AGENT_STATE_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_SCRATCH_DIR` into the live session environment.

When persistence is enabled, Houmao SHALL publish `HOUMAO_AGENT_PERSIST_DIR` into the live session environment.

When persistence is disabled, Houmao SHALL omit `HOUMAO_AGENT_PERSIST_DIR`.

Houmao SHALL NOT publish `HOUMAO_JOB_DIR` or `HOUMAO_MEMORY_DIR` for the new workspace contract.

#### Scenario: Enabled persistence publishes all workspace variables
- **WHEN** a managed session resolves workspace root `/repo/.houmao/memory/agents/researcher-id`
- **AND WHEN** persistence is enabled at `/repo/.houmao/memory/agents/researcher-id/persist`
- **THEN** the live environment contains `HOUMAO_AGENT_STATE_DIR=/repo/.houmao/memory/agents/researcher-id`
- **AND THEN** the live environment contains `HOUMAO_AGENT_MEMO_FILE=/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** the live environment contains `HOUMAO_AGENT_SCRATCH_DIR=/repo/.houmao/memory/agents/researcher-id/scratch`
- **AND THEN** the live environment contains `HOUMAO_AGENT_PERSIST_DIR=/repo/.houmao/memory/agents/researcher-id/persist`

#### Scenario: Disabled persistence omits persist env
- **WHEN** a managed session resolves persistence as disabled
- **THEN** the live environment contains `HOUMAO_AGENT_STATE_DIR`
- **AND THEN** the live environment contains `HOUMAO_AGENT_MEMO_FILE`
- **AND THEN** the live environment contains `HOUMAO_AGENT_SCRATCH_DIR`
- **AND THEN** the live environment does not contain `HOUMAO_AGENT_PERSIST_DIR`
- **AND THEN** the live environment does not contain `HOUMAO_MEMORY_DIR`

### Requirement: Workspace file operations are lane-scoped and path-contained
All CLI, gateway, and pair-server workspace file operations SHALL address either the `scratch` lane or the `persist` lane.

Workspace lane operations SHALL accept only relative paths, SHALL reject absolute paths, SHALL reject `..` traversal, and SHALL verify that the resolved target remains inside the selected lane root after symlink resolution.

Workspace memo operations SHALL operate only on the fixed `houmao-memo.md` file under the workspace root and SHALL NOT allow arbitrary workspace-root file paths.

Operations against the persist lane SHALL fail clearly when persistence is disabled for the addressed managed agent.

#### Scenario: Traversal path is rejected
- **WHEN** an operator requests workspace file path `../manifest.json` in the `scratch` lane
- **THEN** the operation fails before reading or writing any file
- **AND THEN** the failure explains that workspace paths must stay within the selected lane

#### Scenario: Disabled persist lane is unavailable
- **WHEN** managed agent `researcher` has persistence disabled
- **AND WHEN** an operator requests a persist-lane file operation
- **THEN** the operation fails without creating a persist directory
- **AND THEN** the failure explains that the persist lane is disabled

### Requirement: Houmao exposes supported workspace operations through CLI and gateway surfaces
Houmao SHALL provide supported operator entrypoints to resolve, list, read, write, append, delete, and clear lane-scoped workspace files.

Houmao SHALL provide supported operator entrypoints to resolve, read, replace, and append the fixed `houmao-memo.md` file.

The live gateway SHALL expose equivalent lane-scoped workspace routes for attached agents, and the pair server SHALL proxy those routes for managed agents resolved through the server.

#### Scenario: CLI resolves workspace paths without shelling into the agent
- **WHEN** an operator runs a supported workspace path command for managed agent `researcher`
- **THEN** the command reports the workspace root, scratch lane, and persist lane when persistence is enabled
- **AND THEN** the command reports the memo file path
- **AND THEN** the operator does not need to inspect the session manifest manually to discover those paths

#### Scenario: Gateway reads a scratch file
- **WHEN** an attached gateway receives a request to read `scratch` file `edge-loops/ledger.json`
- **AND WHEN** the resolved target is contained inside `HOUMAO_AGENT_SCRATCH_DIR`
- **THEN** the gateway returns the file content through the workspace API

#### Scenario: Gateway appends to the agent memo
- **WHEN** an attached gateway receives a request to append initialization rules to the memo
- **THEN** the gateway appends that content to `<workspace-root>/houmao-memo.md`
- **AND THEN** the request does not accept an arbitrary workspace-root path
