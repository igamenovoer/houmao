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
- `agents self` operates on the caller's verified managed runtime and can adopt the current tmux session through `join`,
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

### Requirement: Scoped Agent Commands Expose Native Home Inspection

`agents single` and `agents self` SHALL expose `home` for one active managed agent. Single scope SHALL use its group-level selector; self scope SHALL use the current registered session without selectors. Plain output SHALL identify the native home path, and root `--print-json` SHALL expose the typed descriptor. Inspection SHALL NOT build, launch, or repair a home.

#### Scenario: Operator Reads a Selected Agent Home
- **WHEN** an operator runs `houmao-mgr agents single --agent-id agent-123 home`
- **THEN** the command reports the authoritative home of active agent `agent-123`
- **AND** the leaf accepts no second target selector

#### Scenario: Agent Reads Its Own Home
- **WHEN** an agent runs `houmao-mgr agents self home` inside its registered session
- **THEN** it receives that agent's native home without an explicit target override

#### Scenario: Structured Home Inspection Is Requested
- **WHEN** root `--print-json` is used with a scoped home command
- **THEN** output contains the selected agent, backend/tool, native home path, and known selector variable
- **AND** it excludes credentials, file contents, and ambient environment

#### Scenario: Selected Home Cannot Be Established
- **WHEN** the active runtime has no authoritative native-home mapping
- **THEN** the command exits nonzero without guessing or creating a home

### Requirement: Scoped Agent Commands Expose Read Only Common State

Scoped `refresh --check` SHALL inspect skills/MCP as common-plugin without initiating reload or forced discovery. It SHALL expose capabilities, inventory coverage, per-resource freshness, evidence, boundaries, and health. It SHALL report native automatic updates independently of Houmao receipts and SHALL provide no common native-special-plugin inventory or freshness API.

#### Scenario: Operator Checks a Selected Agent
- **WHEN** an operator runs `houmao-mgr agents single --agent-id agent-123 refresh --check`
- **THEN** the command performs read-only common observation for that active agent
- **AND** it does not initiate native invalidation, reload, worker startup, or a model turn

#### Scenario: Agent Checks During Its Own Active Turn
- **WHEN** an agent invokes `houmao-mgr agents self refresh --check` during active work
- **THEN** it receives the available observation or explicit evidence limitation without waiting for its turn to finish

#### Scenario: Automatic Update Is Observed
- **WHEN** the body already applied external skill/MCP edits without a Houmao refresh receipt
- **THEN** check mode reports the evidenced current state without requiring that receipt

#### Scenario: Observation Is Incomplete
- **WHEN** check mode cannot establish full common freshness
- **THEN** it preserves pending or unknown per-resource results and exits nonzero
- **AND** it does not quietly perform a refresh to improve the answer

### Requirement: Scoped Agent Commands Expose Native Refresh

Single/self `refresh` SHALL observe common state before selecting verified no-op, automatic discovery, or native reload. The native operation SHALL be permitted to refresh native-special-plugin and other native resources. Output SHALL preserve common observations and native outcomes without claiming common-only or atomic effects, applying launch profiles, or restarting the agent.

#### Scenario: Operator Refreshes a Selected Agent
- **WHEN** an operator runs `houmao-mgr agents single --agent-name worker-a refresh`
- **THEN** refresh targets the uniquely resolved active agent and reports its typed common/native results without relaunch fallback

#### Scenario: Native Updates Make Refresh Redundant
- **WHEN** common observation establishes complete current state before manual refresh
- **THEN** the command reports `method=noop` and `outcome=already_current`
- **AND** it initiates no native refresh or provider work

#### Scenario: Native Reload Also Updates Extensions
- **WHEN** the qualified native operation reloads skills/MCP and native-specific extensions together
- **THEN** the command accepts its broader effects and reports the verified common result
- **AND** it does not claim to verify every native extension

#### Scenario: Agent Requests Mutating Reload During Its Active Turn
- **WHEN** an agent's current work prevents native reload admission
- **THEN** self refresh returns busy immediately without interruption, deferred queueing, or waiting for that same turn

#### Scenario: Single Scope Has No Selector
- **WHEN** single refresh or check has no group-level selector
- **THEN** usage or target resolution fails without inferring the caller's session

#### Scenario: Self Scope Is Outside a Registered Session
- **WHEN** self refresh or check is invoked outside a registered managed session
- **THEN** it fails without selecting another agent or server default

### Requirement: Refresh CLI Preserves Freshness Outcome and Exit Semantics

Check SHALL exit 0 only for complete confirmed common freshness. Refresh SHALL exit 0 for already-current, confirmed common refresh, or fully qualified automatic coverage with explicit future boundaries. Other outcomes SHALL exit nonzero. Both output modes SHALL preserve freshness, health, native effects, and safe limitations without equating unknown evidence with current state.

#### Scenario: Automatic Discovery Is Deferred
- **WHEN** qualified discovery covers common resources on the next step, turn, or load
- **THEN** refresh exits 0 with that boundary
- **AND** it does not claim that future activation already occurred

#### Scenario: Common Resources Require Relaunch
- **WHEN** a common resource remains restart-required after other changes applied
- **THEN** refresh exits nonzero and preserves the applied effects and pending remainder
- **AND** guidance points to separate relaunch without changing its conversation-selection policy

#### Scenario: Only a Native Extension Remains Pending
- **WHEN** common freshness and native readiness are confirmed but unrelated native extension code remains pending
- **THEN** that pending diagnostic alone does not make the common command fail
- **AND** output makes no claim of full native extension freshness

#### Scenario: Native Outcome Is Uncertain
- **WHEN** native completion or readiness cannot be established
- **THEN** refresh exits nonzero with its uncertainty and safe effect evidence
- **AND** cached common metadata does not turn that result into success

#### Scenario: Structured Observation Is Requested
- **WHEN** root `--print-json` is used with refresh or check
- **THEN** typed output preserves current/pending/unknown common state, scope, boundaries, and separate native diagnostics
- **AND** it contains no raw private configuration or credential-derived fingerprints

### Requirement: Refresh CLI Has No Restart or Installation Authority

Scoped refresh SHALL reject force, restart, installation, source-directory, desired-revision, replacement-content, and arbitrary-command options. Global/external scope SHALL NOT gain these single-runtime home/refresh controls. Existing relaunch SHALL retain manifest-backed generation and conversation selection as a separate command.

#### Scenario: Caller Attempts Forced Restart
- **WHEN** a caller supplies `--restart` or `--force` with refresh or check
- **THEN** usage validation fails before native effects

#### Scenario: Caller Attempts Installation
- **WHEN** a caller supplies package/source/replacement-content options
- **THEN** the command rejects them and leaves external update ownership with the caller

#### Scenario: Scope Help Shows Distinct Actions
- **WHEN** an operator reads single/self help and refresh help
- **THEN** home, refresh/check, and relaunch remain distinct supported operations
- **AND** global/external help does not offer the new body home/refresh controls

#### Scenario: Explicit Relaunch Follows Existing Policy
- **WHEN** an operator separately invokes relaunch
- **THEN** its existing launch-material generation and chat-session rules apply
- **AND** the refresh feature neither replaces those rules nor promises exact continuation by default

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
