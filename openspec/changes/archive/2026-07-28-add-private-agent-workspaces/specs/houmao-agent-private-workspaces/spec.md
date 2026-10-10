## ADDED Requirements

### Requirement: Definitions declare optional private workspace contracts
The Agent Definition instance-contract schema SHALL support an optional Private Agent Workspace Contract with stable semantic labels, default relative paths, path kinds, required posture, materialization policy, activation mode, and workdir mode.

#### Scenario: Definition omits the contract
- **WHEN** an agent launches from a definition without a workspace contract
- **THEN** Houmao SHALL use project-root behavior and SHALL create no private workspace

#### Scenario: Contract is optional
- **WHEN** deployment selects project-root mode for an optional contract
- **THEN** launch SHALL create no workspace root, TOML manifest, SQLite index, or Git exclude state

### Requirement: Private state and execution workdir are independent
Enabling a private workspace SHALL NOT change the process workdir unless the contract explicitly selects `workdir_mode = "private-root"`.

#### Scenario: Auxiliary private storage is enabled
- **WHEN** the contract selects a private workspace with `workdir_mode = "project-root"`
- **THEN** the agent SHALL run in the user project and SHALL receive the separate private state root

#### Scenario: Private workdir is explicit
- **WHEN** the contract and deployment select `workdir_mode = "private-root"`
- **THEN** the resolved private root SHALL become the execution workdir

### Requirement: Workspace TOML stores stable identity and topology
`houmao-agent-workspace.toml` SHALL store schema, workspace and agent identity, project and deployment identity, contract identity and digest, semantic bindings, tracking posture, SQLite filename, and SQLite schema version.

#### Scenario: Indexed records change
- **WHEN** workspace SQLite adds or revises a record
- **THEN** the TOML manifest SHALL remain unchanged

#### Scenario: Manifest contains database digest
- **WHEN** validation finds a mutable database digest or generation in TOML
- **THEN** it SHALL reject the manifest schema

### Requirement: Workspace SQLite indexes growing records
`houmao-agent-workspace.sqlite` SHALL own its schema, current generation, repeated workspace identity, record metadata, payload paths and digests, and projection metadata.

#### Scenario: Database belongs to another workspace
- **WHEN** SQLite metadata does not match TOML workspace identity
- **THEN** validation SHALL reject the pair without adopting records

#### Scenario: Payload drifts
- **WHEN** an indexed payload differs from its recorded digest
- **THEN** doctor SHALL report payload drift

### Requirement: Semantic bindings remain confined and contract-compatible
Each semantic label SHALL map to one confined relative path of the declared kind. Instance mutation SHALL not add, remove, or redefine contract labels.

#### Scenario: Human changes an artifact path
- **WHEN** an admin remaps `workspace.artifacts` to another safe relative directory
- **THEN** verified-self lookup SHALL return the new path without rewriting static skills

#### Scenario: Binding escapes the root
- **WHEN** a proposed path is absolute, traverses above the root, or crosses a symlink boundary
- **THEN** mutation SHALL reject it

### Requirement: Launch prepares private workspaces recoverably
Managed launch SHALL prepare the workspace through idempotent journaled states and SHALL record the association in canonical instance state before process start.

#### Scenario: Fresh private launch succeeds
- **WHEN** the selected root is unowned and the contract is valid
- **THEN** Houmao SHALL create TOML, SQLite, required semantic paths, Git posture, and the instance association before starting the process

#### Scenario: Process start fails
- **WHEN** process startup fails after workspace publication
- **THEN** Houmao SHALL record the failed attempt and SHALL remove only fresh operation-owned content when ownership and user-mutation checks permit

#### Scenario: Compatible preserved instance relaunches
- **WHEN** the same instance relaunches with the same workspace-contract digest
- **THEN** Houmao SHALL revalidate and reuse its existing workspace

### Requirement: Private workspaces are local-untracked by default
In a Git project, `local-untracked` SHALL verify that the root is absent from the index and effectively ignored, then maintain an owned `.git/info/exclude` entry.

#### Scenario: Root is already tracked
- **WHEN** launch selects local-untracked posture for an indexed path
- **THEN** preparation SHALL stop without running `git rm --cached`

#### Scenario: Human opts into tracking
- **WHEN** an admin explicitly selects `tracked-permitted`
- **THEN** Houmao SHALL remove only its owned exclude entry and SHALL not stage or commit content

### Requirement: Verified agents resolve paths but do not mutate workspaces
Verified-self commands SHALL resolve declared semantic paths and inspect read-only topology. Mutation SHALL require an explicit admin target.

#### Scenario: Static skill resolves artifacts
- **WHEN** a verified managed agent asks for `workspace.artifacts`
- **THEN** Houmao SHALL return the current confined path for that agent

#### Scenario: Managed self requests a remap
- **WHEN** actor posture is managed agent
- **THEN** the route SHALL reject manifest mutation

### Requirement: Ordinary removal preserves user workspace content
Stopping, preserving, or ordinarily removing an agent SHALL preserve its private workspace by default. Destructive cleanup SHALL be explicit and drift-checked.

#### Scenario: Workspace contains drift
- **WHEN** destructive cleanup finds changed or unowned content
- **THEN** it SHALL stop and report the conflicting paths

### Requirement: Private workspaces remain distinct from multi-agent workspaces
The private workspace route SHALL not replace the standard multi-agent worktree and shared-knowledge workflow.

#### Scenario: User requests a team worktree
- **WHEN** the requested workspace is shared by several agents
- **THEN** routing SHALL use the maintained multi-agent workspace routine
