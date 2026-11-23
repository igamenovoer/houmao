# Spec Delta

## ADDED Requirements

### Requirement: Self identity returns from the verified runtime manifest
`agents self identity` SHALL return its public identity payload from the verified runtime manifest and its location. It SHALL resolve identity without constructing a runtime controller, opening the agent definition directory, or querying the gateway.

#### Scenario: A Web agent verifies its own identity
- **WHEN** a Kimi Web or DSH Web agent has a valid managed session and `HOUMAO_AGENT_DEF_DIR` is absent
- **THEN** `houmao-mgr --print-json agents self identity` returns the manifest's identity, mode, tool, backend, and runtime binding
- **AND THEN** the command succeeds with the definition directory unavailable

#### Scenario: The selected manifest cannot establish current ownership
- **WHEN** the manifest is missing, foreign, malformed, or from a stale registry generation
- **THEN** the identity command returns a resolution error before routing substantive work

### Requirement: Self inspection uses manifest-published agent details
Supported `agents self` inspection commands SHALL use the verified manifest for agent metadata and bindings. State, gateway, turn, mailbox, memory, and native-resource inspection SHALL obtain live or stored observations through the corresponding runtime sources identified by that manifest.

#### Scenario: Self inspection runs without launch definitions
- **WHEN** an agent queries its home, state, gateway status, turn evidence, mailbox, memory, or native refresh check after its definition directory becomes unavailable
- **THEN** it receives the manifest-backed agent details and the observations available for that session
- **AND THEN** absent evidence has the command's existing unavailable or unknown meaning

### Requirement: Self mail uses verified runtime routing for notifier rounds
`agents self mail` SHALL derive routing from the verified manifest and current mailbox binding. The CLI SHALL preserve existing gateway authorization and binding checks. It SHALL use runtime-owned mailbox authority for eligible local fallback.

#### Scenario: A Web agent completes a notifier round after launch
- **WHEN** a managed Web agent with an attached authorized gateway verifies identity and processes its notified mail with the definition directory unavailable
- **THEN** `agents self mail` can report status, list, read, reply, and archive using the current binding
- **AND THEN** mailbox commands do not rewrite tmux or reload launch definitions to establish the target

#### Scenario: The notified mailbox binding changes
- **WHEN** a mailbox request carries a stale expected binding ID
- **THEN** the command rejects the request before operating on the replacement mailbox

## MODIFIED Requirements

### Requirement: Agents command family exposes explicit global, single, self, and external scopes
`houmao-mgr agents` SHALL be a public command namespace that exposes explicit `global`, `single`, `self`, and `external` subcommand groups.

`houmao-mgr agents` SHALL NOT expose direct lifecycle, gateway, mail, mailbox, memory, turn, cleanup, launch, join, or external-reference action commands at the same nesting level as `global`, `single`, `self`, and `external`.

The `agents` help output SHALL explain that:

- `agents global` operates on no individual agent or on multiple local managed agents as a registry/fleet,
- `agents single` operates on exactly one explicitly selected local managed-agent identity,
- `agents self` operates on the caller's verified managed runtime and can adopt the current tmux session through `join`,
- `agents external` operates on external-agent registry/reference onboarding for agents whose lifecycle is not controlled by this user's `houmao-mgr`.

`agents single` and `agents self` SHALL NOT be aliases with different selectors. Their command sets SHALL differ where operation authority differs.

#### Scenario: Operator sees explicit agent scopes
- **WHEN** an operator runs `houmao-mgr agents --help`
- **THEN** the help output lists `global`, `single`, `self`, and `external`
- **AND THEN** it does not list direct commands such as `launch`, `list`, `join`, `gateway`, `mail`, or `turn` at the `agents` root

### Requirement: Agents self scope owns current tmux-session membership and self operations
`houmao-mgr agents self` SHALL expose maintained operations whose target is the caller's single verified local managed agent.

At minimum, `agents self` SHALL expose:

- `join`
- `identity`
- `state`
- `prompt`
- `interrupt`
- `relaunch`
- `gateway`
- `mail`
- `mailbox`
- `memory`
- `turn`

`agents self join` SHALL adopt the current tmux session into the Houmao managed-agent registry as one local managed-agent identity.

`agents self join` MAY accept new-identity fields such as `--agent-name` and optional `--agent-id`. Those fields SHALL create or assign the current tmux session's managed identity and SHALL NOT select another existing agent.

`agents self` commands other than `join` SHALL require a verified current managed runtime. Tmux-backed commands SHALL resolve the owning tmux session. Supported headless self commands SHALL accept their verified runtime-owned manifest locator without tmux.

`agents self` commands other than `join` SHALL NOT accept `--agent-id`, `--agent-name`, or `--current-session` because the target is the current managed-agent identity by definition.

`agents self prompt` and `agents self interrupt` SHALL use the supported control path for the current managed session without accepting explicit agent selectors.

`agents self relaunch` SHALL refresh the active tmux-backed surface for the caller's current managed session. It SHALL require resolvable current-session manifest authority. It SHALL NOT perform selected-agent registry lookup, stopped relaunchable-record revival, degraded/stale active-record recovery, or cross-session targeting.

`agents self` SHALL NOT expose selected-agent lifecycle controls that terminate or clean up the caller's own tmux-backed runtime. In particular, `agents self stop` and `agents self cleanup` SHALL NOT be maintained public paths.

#### Scenario: Self join adopts current tmux session
- **WHEN** an operator runs `houmao-mgr agents self join --agent-name local-shell` inside a tmux session that is not yet registered as a managed agent
- **THEN** the command adopts the current tmux session into the Houmao managed-agent registry
- **AND THEN** subsequent `houmao-mgr agents self identity` resolves the new identity from the same current tmux session

#### Scenario: Self command resolves current tmux identity
- **WHEN** an agent runs `houmao-mgr agents self identity` inside its own registered managed tmux session
- **THEN** the command locates the runtime manifest through the current session and verifies it
- **AND THEN** the output reports the manifest's identity without requiring `--agent-id` or `--agent-name`

#### Scenario: Self relaunch refreshes active current session
- **WHEN** an agent runs `houmao-mgr agents self relaunch` inside its own registered managed tmux session
- **THEN** the command resolves current-session manifest authority
- **AND THEN** it refreshes the active tmux-backed primary surface for that current managed session
- **AND THEN** it does not perform selected-agent stopped-record revival or degraded/stale registry recovery

#### Scenario: Self command fails outside managed session
- **WHEN** an operator runs `houmao-mgr agents self mail status` with no verified current managed runtime
- **THEN** the command fails clearly
- **AND THEN** the diagnostic explains what owning session or runtime-owned context is required

#### Scenario: Self scope omits destructive lifecycle controls
- **WHEN** an operator runs `houmao-mgr agents self --help`
- **THEN** the help output lists current-session `prompt`, `interrupt`, and `relaunch`
- **AND THEN** it does not list destructive lifecycle commands `stop` or `cleanup`
- **AND THEN** the documentation directs selected-agent stopped/degraded relaunch recovery, stop, and cleanup to `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`
