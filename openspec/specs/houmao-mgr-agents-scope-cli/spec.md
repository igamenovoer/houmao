# houmao-mgr-agents-scope-cli Specification

## Purpose
TBD - created by archiving change split-agents-global-self-cli. Update Purpose after archive.
## Requirements
### Requirement: Agents command family exposes explicit global, single, self, and external scopes
`houmao-mgr agents` SHALL be a public command namespace that exposes explicit `global`, `single`, `self`, and `external` subcommand groups.

`houmao-mgr agents` SHALL NOT expose direct lifecycle, gateway, mail, mailbox, memory, turn, cleanup, launch, join, or external-reference action commands at the same nesting level as `global`, `single`, `self`, and `external`.

The `agents` help output SHALL explain that:

- `agents global` operates on no individual agent or on multiple local managed agents as a registry/fleet,
- `agents single` operates on exactly one explicitly selected local managed-agent identity,
- `agents self` operates on exactly one local managed agent held by the caller's current tmux session, including adopting that session through `join`,
- `agents external` operates on external-agent registry/reference onboarding for agents whose lifecycle is not controlled by this user's `houmao-mgr`.

`agents single` and `agents self` SHALL NOT be aliases with different selectors. Their command sets SHALL differ where operation authority differs.

#### Scenario: Operator sees explicit agent scopes
- **WHEN** an operator runs `houmao-mgr agents --help`
- **THEN** the help output lists `global`, `single`, `self`, and `external`
- **AND THEN** it does not list direct commands such as `launch`, `list`, `join`, `gateway`, `mail`, or `turn` at the `agents` root

### Requirement: Agents global scope owns zero-or-many local registry operations
`houmao-mgr agents global` SHALL expose maintained operations whose target cardinality is no individual managed agent or multiple local managed agents across projects.

At minimum, `agents global` SHALL expose:

- `list`

`agents global` MAY expose future fleet operations such as stopping all local managed agents when the operation targets multiple agents and does not require a single selected-agent identity.

`agents global` SHALL NOT expose exactly-one-agent operations such as selected-agent `prompt`, `interrupt`, `stop`, `relaunch`, `gateway`, `mail`, `mailbox`, `memory`, `turn`, or `cleanup`.

`agents global` commands SHALL NOT accept single-agent selectors such as `--agent-id` or `--agent-name`. Filter options that still select zero-or-many local managed agents remain allowed.

`agents global` SHALL NOT expose `launch` because first birth is source-scoped rather than global management.

`agents global` SHALL NOT expose `join` because current-session adoption belongs to `agents self join`.

`agents global` SHALL NOT expose `external` because remotely owned or communication-only references belong to `agents external`.

#### Scenario: Global list spans local managed agents across projects
- **WHEN** an operator runs `houmao-mgr agents global list`
- **THEN** the command lists already registered local managed agents from the shared registry rather than only from the current project overlay
- **AND THEN** the result may include local managed agents launched from multiple project overlays
- **AND THEN** remotely owned communication-only references remain under `houmao-mgr agents external list`

#### Scenario: Global multi-agent operation does not select one agent
- **WHEN** a future operator runs a maintained fleet operation such as `houmao-mgr agents global stop-all`
- **THEN** the command targets multiple local managed agents through fleet semantics
- **AND THEN** it does not accept `--agent-id` or `--agent-name`

#### Scenario: Global help omits single-target commands
- **WHEN** an operator runs `houmao-mgr agents global --help`
- **THEN** the help output does not list `prompt`, `interrupt`, `stop`, `relaunch`, `gateway`, `mail`, `mailbox`, `memory`, `turn`, or `cleanup`
- **AND THEN** it does not list `launch`, `join`, or `external`

### Requirement: Agents single scope owns explicitly selected one-agent operations
`houmao-mgr agents single` SHALL expose maintained operations for one explicitly selected local managed-agent identity.

`agents single` SHALL require exactly one group-level selector:

```text
--agent-id <id>
--agent-name <name>
```

At minimum, `agents single` SHALL expose:

- `state`
- `prompt`
- `interrupt`
- `stop`
- `relaunch`
- `gateway`
- `mail`
- `mailbox`
- `memory`
- `turn`
- `cleanup`

Nested `agents single` subcommands SHALL use the group-level selected identity. They SHALL NOT require the selected agent id or name to be repeated on every nested leaf command.

`agents single` SHALL be the maintained public surface for selected-agent lifecycle controls that can mutate, interrupt, terminate, restart, or clean up the selected tmux-backed managed-agent runtime, including direct `prompt`, `interrupt`, `stop`, `relaunch`, and `cleanup` commands.

`agents single` SHALL NOT infer the current tmux session when the group-level selector is omitted.

`agents single` SHALL NOT expose current-session membership commands such as `join` or the future inverse `leave`.

#### Scenario: Single prompt uses group-level selector
- **WHEN** an operator runs `houmao-mgr agents single --agent-id agent-123 prompt --prompt ping`
- **THEN** the command targets managed agent `agent-123`
- **AND THEN** the `prompt` leaf does not require another `--agent-id` option

#### Scenario: Single stop uses explicit selected-agent authority
- **WHEN** an operator runs `houmao-mgr agents single --agent-id agent-123 stop`
- **THEN** the command targets managed agent `agent-123` through the explicit selected-agent selector
- **AND THEN** the command does not infer or target the caller's current tmux session

#### Scenario: Single mail read uses group-level selector
- **WHEN** an operator runs `houmao-mgr agents single --agent-name worker-a mail read --message-ref msg-1`
- **THEN** the command reads message `msg-1` for managed agent `worker-a`
- **AND THEN** it does not resolve the target from the caller's current tmux session

#### Scenario: Single scope does not expose current-session join
- **WHEN** an operator runs `houmao-mgr agents single --agent-id agent-123 join`
- **THEN** the command is not a maintained public path
- **AND THEN** the diagnostic or help output points current-session adoption to `houmao-mgr agents self join`

#### Scenario: Single command rejects missing selector inside tmux
- **WHEN** an operator runs `houmao-mgr agents single gateway prompt --prompt ping` inside a managed tmux session without `--agent-id` or `--agent-name`
- **THEN** the command fails clearly because `agents single` requires an explicit selected agent
- **AND THEN** the diagnostic points the operator to either supply a single-agent selector or use `houmao-mgr agents self gateway prompt`

### Requirement: Agents self scope owns current tmux-session membership and self operations
`houmao-mgr agents self` SHALL expose maintained operations whose target is the single local managed agent held by the caller's current tmux session.

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

`agents self join` MAY accept new-identity fields such as `--agent-name` and optional `--agent-id`; those fields SHALL create or assign the current tmux session's managed identity and SHALL NOT select another existing agent.

`agents self` commands other than `join` SHALL fail clearly when invoked outside a tmux session that resolves to a registered managed-agent runtime identity.

`agents self` commands other than `join` SHALL NOT accept `--agent-id`, `--agent-name`, or `--current-session` because the target is the current managed-agent identity by definition.

`agents self prompt` SHALL submit a prompt to the current managed-agent tmux session without accepting explicit agent selectors.

`agents self interrupt` SHALL interrupt the current managed-agent tmux session without accepting explicit agent selectors.

`agents self relaunch` SHALL refresh the active tmux-backed surface for the caller's current managed session. It SHALL require resolvable current-session manifest authority. It SHALL NOT perform selected-agent registry lookup, stopped relaunchable-record revival, degraded/stale active-record recovery, or cross-session targeting.

`agents self` SHALL NOT expose selected-agent lifecycle controls that terminate or clean up the caller's own tmux-backed runtime. In particular, `agents self stop` and `agents self cleanup` SHALL NOT be maintained public paths.

#### Scenario: Self join adopts current tmux session
- **WHEN** an operator runs `houmao-mgr agents self join --agent-name local-shell` inside a tmux session that is not yet registered as a managed agent
- **THEN** the command adopts the current tmux session into the Houmao managed-agent registry
- **AND THEN** subsequent `houmao-mgr agents self identity` resolves the new identity from the same current tmux session

#### Scenario: Self command resolves current tmux identity
- **WHEN** an agent runs `houmao-mgr agents self identity` inside its own registered managed tmux session
- **THEN** the command resolves the current managed-agent identity from tmux/session metadata
- **AND THEN** the output reports that identity without requiring `--agent-id` or `--agent-name`

#### Scenario: Self relaunch refreshes active current session
- **WHEN** an agent runs `houmao-mgr agents self relaunch` inside its own registered managed tmux session
- **THEN** the command resolves current-session manifest authority
- **AND THEN** it refreshes the active tmux-backed primary surface for that current managed session
- **AND THEN** it does not perform selected-agent stopped-record revival or degraded/stale registry recovery

#### Scenario: Self command fails outside managed session
- **WHEN** an operator runs `houmao-mgr agents self mail status` outside a registered managed tmux session
- **THEN** the command fails clearly
- **AND THEN** the diagnostic explains that `agents self` requires a current managed-agent tmux session

#### Scenario: Self scope omits destructive lifecycle controls
- **WHEN** an operator runs `houmao-mgr agents self --help`
- **THEN** the help output lists current-session `prompt`, `interrupt`, and `relaunch`
- **AND THEN** it does not list destructive lifecycle commands `stop` or `cleanup`
- **AND THEN** the documentation directs selected-agent stopped/degraded relaunch recovery, stop, and cleanup to `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`

### Requirement: Agents external scope owns external-agent registry/reference onboarding
`houmao-mgr agents external` SHALL expose maintained operations for bringing external agents into Houmao's shared registry as externally owned communication-only references.

At minimum, `agents external` SHALL expose:

- `register`
- `list`
- `get`
- `verify`
- `remove`

External references SHALL remain distinct from local managed-agent runtime identities. Their lifecycle SHALL remain under the external owner rather than this user's `houmao-mgr`.

`agents external` SHALL NOT expose local runtime control commands such as `prompt`, `interrupt`, `stop`, `relaunch`, `gateway`, `turn`, or `cleanup`.

#### Scenario: External register imports communication-only reference
- **WHEN** an operator runs `houmao-mgr agents external register --agent-name remote-reviewer`
- **THEN** the command registers a remotely owned or communication-only agent reference
- **AND THEN** it does not adopt the current tmux session as a local managed-agent runtime
- **AND THEN** it does not give this user's `houmao-mgr` lifecycle authority over the external runtime

#### Scenario: External help omits local runtime controls
- **WHEN** an operator runs `houmao-mgr agents external --help`
- **THEN** the help output lists `register`, `list`, `get`, `verify`, and `remove`
- **AND THEN** it does not list `prompt`, `interrupt`, `stop`, `relaunch`, `gateway`, `turn`, or `cleanup`

### Requirement: Current-session gateway and mail behavior moves to agents self
Current-session gateway, mail, mailbox, memory, and turn operations SHALL be represented through `houmao-mgr agents self ...` command paths.

Explicit one-agent gateway, mail, mailbox, memory, and turn operations SHALL be represented through `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`.

#### Scenario: Self gateway prompt replaces implicit selected-agent prompt
- **WHEN** an agent wants to prompt its own managed session from inside the owning tmux session
- **THEN** the maintained command path is `houmao-mgr agents self gateway prompt`
- **AND THEN** `houmao-mgr agents single gateway prompt` requires an explicit group-level selector

#### Scenario: Self mail read replaces implicit agents mail read
- **WHEN** an agent wants to read its own mailbox message from inside the owning tmux session
- **THEN** the maintained command path is `houmao-mgr agents self mail read --message-ref <ref>`
- **AND THEN** no `--agent-id`, `--agent-name`, or `--current-session` option is required

