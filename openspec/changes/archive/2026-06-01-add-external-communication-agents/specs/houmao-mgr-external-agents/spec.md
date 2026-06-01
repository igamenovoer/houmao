## ADDED Requirements

### Requirement: External agents can be registered as communication-only managed targets
`houmao-mgr agents external register` SHALL create a durable local external-agent record for an already-running remote Houmao agent served by a reachable maintained `houmao-passive-server`.

Registration SHALL require a local name, remote passive-server API base URL, and remote agent reference. The command SHALL verify the remote authority by using the maintained pair-authority health probe and SHALL resolve the remote agent reference through the remote managed-agent identity API before persisting the record.

The persisted record SHALL store external communication metadata only: local name, local external-agent id, remote pair API base URL, remote agent reference, gateway expectation, lifecycle owner `remote`, verification timestamp, and cached remote identity. It SHALL NOT require or synthesize local manifest paths, session roots, agent-definition directories, tmux sessions, gateway process paths, or local runtime leases.

#### Scenario: Register a reachable remote gateway-enabled agent
- **WHEN** an operator runs `houmao-mgr agents external register --name remote-james --api-base-url http://remote-host:9891 --agent-ref james --gateway-enabled`
- **AND WHEN** the remote URL is a supported `houmao-passive-server`
- **AND WHEN** the remote authority resolves managed agent `james`
- **THEN** the command writes an external communication-only record under the local registry
- **AND THEN** the record stores `local_name = "remote-james"`, `remote_agent_ref = "james"`, `pair_api_base_url = "http://remote-host:9891"`, `gateway_expected = true`, and `lifecycle_owner = "remote"`
- **AND THEN** the record does not contain local manifest, tmux, runtime root, or local lifecycle authority fields

#### Scenario: Registration rejects unsupported or unreachable remote authority
- **WHEN** an operator registers an external agent with an unreachable URL or a URL whose health probe is not the maintained passive-server authority
- **THEN** the command fails before writing an external record
- **AND THEN** the error identifies the unreachable or unsupported remote base URL

#### Scenario: Registration rejects local lifecycle name collision
- **WHEN** a local lifecycle-managed agent already uses friendly name `remote-james`
- **AND WHEN** an operator attempts to register an external agent with `--name remote-james`
- **THEN** the command fails without replacing the local lifecycle record
- **AND THEN** the error explains that local lifecycle-managed agents take precedence over external communication-only aliases

### Requirement: External agent records can be inspected, verified, and removed
`houmao-mgr agents external` SHALL provide local registry management commands for external records.

At minimum, the command family SHALL support:
- `register` to create or replace an external communication-only record when replacement is explicitly allowed,
- `list` to show registered external records without contacting remote authorities,
- `get` to show one external record and its cached identity metadata,
- `verify` to contact the remote authority, refresh cached identity and verification timestamp, and report gateway availability when expected,
- `remove` to delete only the local external communication-only record.

Removing an external record SHALL NOT send stop, cleanup, detach, or lifecycle requests to the remote authority.

#### Scenario: List external records without remote polling
- **WHEN** an operator runs `houmao-mgr agents external list`
- **THEN** the command reads local external records from the registry
- **AND THEN** it does not contact each remote `pair_api_base_url`
- **AND THEN** it shows each local name, local external-agent id, remote base URL, remote agent reference, gateway expectation, and last verification time

#### Scenario: Verify refreshes cached identity
- **WHEN** an operator runs `houmao-mgr agents external verify --agent-name remote-james`
- **AND WHEN** the stored remote authority is reachable and resolves the stored remote agent reference
- **THEN** the command refreshes the cached remote identity and `verified_at_utc`
- **AND THEN** it reports success without changing local lifecycle ownership

#### Scenario: Remove deletes only the local import
- **WHEN** an operator runs `houmao-mgr agents external remove --agent-name remote-james`
- **THEN** the local external-agent record is removed
- **AND THEN** no remote lifecycle, gateway attach/detach, cleanup, or tmux command is sent

### Requirement: External agents participate in communication-safe managed-agent commands
External communication-only records SHALL be selectable through the normal explicit managed-agent selectors after registration. When an external record is selected, communication-safe commands SHALL route through the record's stored remote pair API base URL and remote agent reference.

At minimum, external targets SHALL support:
- `houmao-mgr agents list`,
- `houmao-mgr agents state`,
- `houmao-mgr agents prompt`,
- `houmao-mgr agents interrupt`,
- `houmao-mgr agents gateway status`,
- `houmao-mgr agents gateway prompt`,
- `houmao-mgr agents gateway interrupt`,
- pair-backed `houmao-mgr agents mail ...` operations when the remote authority supports them.

#### Scenario: Prompt routes to the remote managed-agent request API
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-name remote-james --prompt "continue"`
- **AND WHEN** `remote-james` resolves to an external communication-only record
- **THEN** the command submits the prompt to the remote authority stored in `pair_api_base_url`
- **AND THEN** it addresses the remote managed agent using the stored `remote_agent_ref`
- **AND THEN** it does not attempt to load a local runtime controller or local manifest

#### Scenario: State routes to the remote managed-agent state API
- **WHEN** an operator runs `houmao-mgr agents state --agent-name remote-james`
- **AND WHEN** the external record's remote authority is reachable
- **THEN** the command returns the remote managed-agent state response
- **AND THEN** the rendered output identifies the target as external communication-only or remote lifecycle-owned

#### Scenario: Gateway prompt uses the remote gateway prompt control route
- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-name remote-james --prompt "check inbox"`
- **AND WHEN** `remote-james` resolves to an external communication-only record
- **THEN** the command submits gateway prompt control through the remote passive-server pair API
- **AND THEN** it does not attach or create a local gateway process

#### Scenario: Remote mail operation preserves remote authority semantics
- **WHEN** an operator runs a supported `houmao-mgr agents mail ...` command against `--agent-name remote-james`
- **THEN** the command calls the remote pair-backed mail route for the stored remote agent reference
- **AND THEN** unsupported mailbox configuration or remote route failures are reported using the remote authority's error semantics

### Requirement: External agents reject lifecycle and raw local-control commands
External communication-only targets SHALL reject commands that require local lifecycle ownership, local tmux authority, local runtime artifacts, or gateway process ownership.

At minimum, external targets SHALL reject:
- `houmao-mgr agents stop`,
- `houmao-mgr agents relaunch`,
- local cleanup actions that operate on runtime-owned artifacts,
- `houmao-mgr agents gateway attach`,
- `houmao-mgr agents gateway detach`,
- `houmao-mgr agents gateway send-keys`,
- current-session and target-tmux-session selector flows.

The rejection message SHALL identify the target as external communication-only, name the remote lifecycle owner by base URL and remote agent reference, and list the locally supported communication-safe operations.

#### Scenario: Stop is rejected for external target
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name remote-james`
- **AND WHEN** `remote-james` resolves to an external communication-only record
- **THEN** the command fails without sending a remote stop request
- **AND THEN** the error explains that lifecycle is owned by the remote Houmao authority

#### Scenario: Gateway attach is rejected for external target
- **WHEN** an operator runs `houmao-mgr agents gateway attach --agent-name remote-james`
- **AND WHEN** `remote-james` resolves to an external communication-only record
- **THEN** the command fails without sending a remote attach request
- **AND THEN** the error explains that gateway process ownership is remote and local attach is unsupported

#### Scenario: Raw gateway send-keys is rejected for external target
- **WHEN** an operator runs `houmao-mgr agents gateway send-keys --agent-name remote-james --sequence "hello"`
- **AND WHEN** `remote-james` resolves to an external communication-only record
- **THEN** the command fails without sending raw control input
- **AND THEN** the error points to gateway prompt as the supported communication path

### Requirement: External agent output distinguishes local alias from remote identity
Managed-agent list, state, and external inspection output SHALL make the external communication-only ownership boundary visible.

List output SHALL show the local alias used for selection, the local external-agent id, the remote base URL, and the remote agent reference or remote tracked id. State output SHALL preserve the remote state details while indicating that the local target is a communication-only import whose lifecycle owner is remote.

#### Scenario: Agents list includes external target with remote ownership
- **WHEN** an operator runs `houmao-mgr agents list`
- **AND WHEN** the registry contains external communication-only record `remote-james`
- **THEN** the list includes `remote-james`
- **AND THEN** the row identifies remote lifecycle ownership or external communication-only management
- **AND THEN** the row does not show local manifest, session root, or tmux session metadata for that target

#### Scenario: Remote state failure preserves local record
- **WHEN** an operator runs `houmao-mgr agents state --agent-name remote-james`
- **AND WHEN** the stored remote authority is unreachable
- **THEN** the command reports the connection failure and remote base URL
- **AND THEN** the local external-agent record remains registered for later verification or removal
