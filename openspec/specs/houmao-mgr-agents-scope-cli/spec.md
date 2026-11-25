# houmao-mgr-agents-scope-cli Specification

## Purpose
`houmao-mgr agents` routes commands by target scope across the local registry, a selected local agent, the caller's verified agent, and external communication references. Scope determines which commands can inspect a native home, check resource freshness, or request native refresh.
## Requirements

### Requirement: Agents command family exposes explicit global, single, self, and external scopes
`houmao-mgr agents` SHALL be a public command namespace that exposes explicit `global`, `single`, `self`, and `external` subcommand groups.

`houmao-mgr agents` SHALL NOT expose direct lifecycle, gateway, mail, mailbox, memory, turn, cleanup, launch, join, or external-reference action commands at the same nesting level as `global`, `single`, `self`, and `external`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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
`agents single` SHALL use one group-level agent ID or name. Local gateway commands also accept a unique fresh tmux alias. Nested commands SHALL use the selected target without inferring it from the caller's session.

#### Scenario: Acceptance criteria

- **WHEN** a caller selects an agent for `state`, `prompt`, `interrupt`, `stop`, `relaunch`, `gateway`, `mail`, `mailbox`, `memory`, `turn`, or `cleanup`
- **THEN** the command uses the group-level selection
- **AND THEN** current-session membership operations such as `join` belong to `agents self`

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
- **WHEN** an operator runs `houmao-mgr agents single gateway prompt --prompt ping` inside a managed tmux session without a group-level selector
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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

Explicit one-agent gateway, mail, mailbox, memory, and turn operations SHALL be represented through `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`. Local gateway commands may also use the group-level tmux session alias.

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

### Requirement: Selected-Agent Access Commands Use Verified Owner Authority

`agents single access` SHALL expose policy initialization, principal and credential administration, grant and revoke, list, and explain operations for the selected agent. The CLI SHALL resolve the observed owner binding before administrative effects. General policy changes and privileged inspection SHALL use verified local owner authority.

#### Scenario: An owner manages policy while the gateway is detached

- **WHEN** a verified owner selects the target and enrolls a principal or grants it a declared operation
- **THEN** the CLI updates that target's retained policy
- **AND THEN** the target gateway need not be attached

#### Scenario: An owner enrolls an offline or cross-account agent

- **WHEN** the verified target owner selects a logical agent principal and provides its authenticated peer public key
- **THEN** the CLI can enroll that key and assign scoped target operations
- **AND THEN** it requires no source runtime, registry record, or access to the source account

#### Scenario: The owner explicitly provisions a replacement policy

- **WHEN** a configured target has former authorization data and its owner initializes policy using a new-schema seed or an explicit empty selection
- **THEN** the CLI validates and initializes the new retained state for the selected domain
- **AND THEN** the command reports whether the resulting admin roster is open or keyed

#### Scenario: An owner inspects a scoped decision

- **WHEN** a verified owner lists grants or explains the effective permission for a principal, resource, and action
- **THEN** the command reports safe principal, assignment, and policy-revision evidence
- **AND THEN** it does not disclose private signing material, challenge state, or provider credentials

### Requirement: Selected-Agent Admin Commands Preserve First Enrollment and Live Roster Changes

The access command family SHALL expose per-key admin enrollment and removal separately from owner-local credential revocation. Remote first-key enrollment SHALL prove the proposed key. Subsequent remote roster changes SHALL prove a current admin-enrolled key and bind that proof to the selected target's roster operation.

#### Scenario: A remote operator enrolls the first key

- **WHEN** the target reports an available empty roster and a caller explicitly requests first-key enrollment
- **THEN** the CLI obtains and signs the exact first-enrollment challenge for that target
- **AND THEN** it reports the enrolled identity or the current enrollment conflict

#### Scenario: A signed admin removes the last key

- **WHEN** a caller using the final enrolled admin key removes that key's roster entry
- **THEN** the command reports the new open roster state
- **AND THEN** it does not repeat the mutation using anonymous authority

#### Scenario: The operator rotates the only admin key

- **WHEN** the operator enrolls the replacement explicitly as admin before removing the old admin entry
- **THEN** the CLI reports keyed access throughout rotation, even if both keys identify the same principal

### Requirement: Peer Caller Proof Selects Source and Target Independently

`agents self access public-key` SHALL export the logical agent ID, selected peer public key, and fingerprint from protected source configuration. The source owner SHALL be able to configure and select a stable peer credential locally. Peer requests SHALL select that signer independently of the selected target and verify the target endpoint before signing.

#### Scenario: Peer identity is exported without a gateway

- **WHEN** a managed caller requests its peer public identity with its source gateway detached
- **THEN** the CLI returns the configured peer public key, fingerprint, and logical agent ID
- **AND THEN** it omits all private key material and paths

#### Scenario: The target and source use different tmux servers

- **WHEN** an enrolled logical peer invokes a supported operation on a target in another account or tmux server
- **THEN** the CLI signs with the configured peer key and binds proof to the verified target
- **AND THEN** the target requires no source lookup or source gateway

#### Scenario: An owner selects a peer signer while its agent is stopped

- **WHEN** the source owner selects protected signer configuration for a logical agent whose runtime is stopped
- **THEN** the CLI can sign an authorized target request with that peer credential
- **AND THEN** signing does not use a current-generation self key or a credential from the selected target

### Requirement: Peer File Commands Select Target and Source Independently

`agents single` SHALL expose `files` operations for the selected agent ID or name. It SHALL verify the attached endpoint through the shared client and support trusted remote coordinates when needed. It SHALL select the caller signer independently of the target or send an unsigned request under verified open mode.

#### Scenario: A source edits a target on another tmux server

- **WHEN** a caller selects an agent by ID or name and explicitly selects the enrolled logical peer's key
- **THEN** the CLI uses the selected signer and target's verified gateway independently of the source agent's runtime, gateway, or tmux placement
- **AND THEN** the file command does not require a tmux socket argument or a source runtime lookup when the signer is explicit

#### Scenario: Only a remote endpoint is available

- **WHEN** the caller selects a target and supplies trusted remote coordinates for its URL, owner context, generation, and gateway presence
- **THEN** the client verifies those coordinates and deployment trust before signing
- **AND THEN** a listener or generation mismatch prevents the command from sending protected input

#### Scenario: Peer routing or authority is unavailable

- **WHEN** the target has no verified attached gateway, a selected signer fails proof, or keyed mode requires a signer that the caller has not selected
- **THEN** the CLI reports that failure before file operations
- **AND THEN** it performs no unsigned retry, local-file or terminal fallback, gateway attachment, or target lifecycle action

#### Scenario: An unsigned caller addresses an open gateway

- **WHEN** the caller selects a verified live target in open mode without selecting a signer
- **THEN** the CLI uses the common unsigned request path and the gateway checks its current open authority and ordinary operation prerequisites
- **AND THEN** a failed explicit proof is refused even if unsigned access would have been allowed

#### Scenario: A scoped peer calls from an isolated OS account

- **WHEN** a keyed non-admin on a separate account selects its enrolled signer and a target mount
- **THEN** the gateway applies only its effective permissions for that mount, including denying an ungranted operation with the same valid proof
- **AND THEN** the CLI needs no target filesystem access, source runtime lookup, or shared execution context

### Requirement: Peer File Commands Expose Read-Only Inspection

`files` SHALL expose `mounts`, `list`, `read`, `diff`, `status`, and `history`. Inspection SHALL use explicit logical paths and applicable revision, draft, or operation references. Published content, candidates, and receipts require current `files.read`. Draft inspection requires the current draft lease and `files.edit`. Inspection SHALL initiate no edit, commit, push, or activation.

#### Scenario: A caller discovers and inspects an authorized mount

- **WHEN** a peer requests mount discovery, file listing, or file content
- **THEN** the CLI returns the authorized mount and its canonical resource ID, or the authorized entries for the selected revision or draft
- **AND THEN** owner-private paths and other callers' drafts remain undisclosed

#### Scenario: A target has no eligible skill projection

- **WHEN** a target lacks the owner-enabled and qualified DSH Web skill mount
- **THEN** discovery omits that mount or reports its availability limit
- **AND THEN** the CLI offers no upgrade, attach, or lifecycle fallback

### Requirement: Peer File Commands Expose Explicit Draft and Push Steps

`files` SHALL expose `lease open`, `lease renew`, `write`, `delete`, `mkdir`, `rename`, `commit`, `abort`, and `push`. Draft mutations SHALL name the applicable lease and logical paths. Anonymous drafts SHALL use the secret lease capability obtained at open. Commit SHALL save the selected draft. Push alone SHALL request publication using the immutable candidate, expected published base, and operation ID.

#### Scenario: A peer commits a draft while the target works

- **WHEN** a peer opens and renews an authorized lease, edits the draft, and commits it
- **THEN** the CLI reports the saved commit ID for later review or push
- **AND THEN** the target continues using its published revision

#### Scenario: The target is busy when the peer pushes

- **WHEN** the gateway refuses the push before publication because the target is busy
- **THEN** the CLI reports the candidate and operation ID with the busy outcome
- **AND THEN** a later explicit attempt of that candidate uses a new operation ID

#### Scenario: A named administrator publishes a retained anonymous candidate

- **WHEN** the authorized administrator selects an immutable candidate saved by an unsigned caller and supplies the exact expected published base
- **THEN** the CLI submits a new signed push and returns a receipt with the current publisher's identity
- **AND THEN** the saved commit retains its anonymous author and target committer

### Requirement: Peer File Writes Return Inspectable Receipts

File mutations SHALL return receipts with applicable references and actual caller attribution. Push results SHALL report publication, activation, and readiness separately. Plain output SHALL show inspection references, and root `--print-json` SHALL expose the typed result. The CLI SHALL give anonymous lease capabilities to the initiating caller and exclude them from ordinary status, history, and logs.

#### Scenario: A push response is lost

- **WHEN** the CLI cannot confirm the outcome after submitting a push
- **THEN** it reports an unconfirmed result with the original operation ID
- **AND THEN** a caller with current `files.read` can use `files status` on that ID without dispatching publication again

#### Scenario: A peer inspects an earlier commit

- **WHEN** the caller selects a saved commit from `files history` or a commit receipt
- **THEN** `files diff` can inspect its recorded changes without replaying the commit or push

### Requirement: File Grants Use Shared Access Administration

The CLI SHALL use `agents single access` for owner-local enrollment, grant, revoke, and inspection of mount permissions. Managed callers SHALL use the existing `agents self access public-key` command to export public signing identity for enrollment. File commands SHALL use the shared credential and policy contracts.

#### Scenario: An owner enrolls or revokes source access

- **WHEN** the verified local owner enrolls a public SSH key for a stable logical peer principal and grants selected `files.read`, `files.edit`, or `files.push` permissions for a mount
- **THEN** shared access inspection reports retained enrollments and grants subject to their current expiry and revocation
- **AND THEN** the scoped peer in keyed mode receives only its effective grants and roles independently of its runtime generation

#### Scenario: An owner inspects a retained grant while the target is detached

- **WHEN** the owner inspects the permission for a mount whose live availability cannot be verified
- **THEN** the CLI can show the retained assignment and reports live applicability as unresolved

#### Scenario: A peer attempts to administer grants

- **WHEN** a caller presents only a scoped file grant or gateway-admin proof to manage the target's general policy
- **THEN** the command refuses access without changing owner state

#### Scenario: A source prepares owner enrollment

- **WHEN** a managed caller requests its public signing identity through `agents self access public-key`
- **THEN** the CLI returns the logical agent's public key and fingerprint for trusted enrollment without exposing private key material or paths or requiring a source gateway
- **AND THEN** exporting the key creates no grant

#### Scenario: Source runtime authority is stale

- **WHEN** a caller cannot establish its managed self context for public-key export
- **THEN** self export fails without disclosing or substituting a signing identity

#### Scenario: An enrolled signer works without current self context

- **WHEN** a caller outside a verified self context uses an explicitly selected already-enrolled signer for a file request
- **THEN** the file command uses that signer directly and the target applies its retained credential and mount policy

### Requirement: Owner Access Feedback Explains the Recorded Grant

Successful `agents single access grant` and `revoke` commands SHALL describe the direct grant change and its admission implications at the committed policy revision. Feedback SHALL use stderr and preserve the existing stdout result and exit behavior. Owner inspection SHALL continue to distinguish direct grants from effective decisions.

#### Scenario: A grant changes on an open roster

- **WHEN** the verified owner adds, updates, or revokes a direct grant and the committed snapshot has an open roster
- **THEN** the command reports the recorded grant change and explains that open admission still supplies authority for supported operations at that policy revision
- **AND THEN** the existing JSON result reports the committed revision and mode

#### Scenario: A grant changes on a keyed roster

- **WHEN** the verified owner changes a direct grant and the committed snapshot has a keyed roster
- **THEN** the command directs the owner to `access explain` for the selected principal, resource, and action
- **AND THEN** the feedback makes no allow or deny claim based solely on the direct grant change

### Requirement: Open Policy Initialization Points to First-Admin Enrollment

When `agents single access init` reports a valid open roster, it SHALL use stderr to identify the existing `access admin-add --first` workflow and its verified attached gateway prerequisite. Initialization SHALL keep its existing result and exit behavior.

#### Scenario: An existing open roster is inspected during initialization

- **WHEN** the owner runs `access init` and the existing policy is already initialized with an open roster
- **THEN** the command reports the retained policy and gives first-admin enrollment guidance
- **AND THEN** it creates no key and makes no roster change

#### Scenario: A detached target initializes an open policy

- **WHEN** the verified owner initializes an empty roster without a live gateway
- **THEN** initialization succeeds under its existing contract
- **AND THEN** the enrollment guidance explains that an attached gateway is needed for the suggested command

### Requirement: Selected File Commands Explain Missing Signer Selection

When a keyed endpoint is verified and a selected-agent file command lacks an explicit signer or unsigned selection, the CLI SHALL name the roster mode and show where to supply `--signer`. The CLI SHALL preserve the operator's explicit caller selection and the existing behavior for open or unavailable policy.

#### Scenario: A keyed mount read or push has no caller selection

- **WHEN** `agents single ... files` selects a verified keyed endpoint for `mounts`, `read`, or `push` without a signer or `--unsigned`
- **THEN** the command fails with guidance showing `files --signer <key>` before the file subcommand
- **AND THEN** it points the verified local owner to `access list` for enrollment details
- **AND THEN** it sends no file request and reveals no roster contents or private key path

#### Scenario: The operator explicitly chooses an identity or unsigned admission

- **WHEN** the file command selects a signer or `--unsigned`
- **THEN** the command uses that selection and the existing gateway decision
- **AND THEN** any refusal terminates the attempt without selecting another credential or retrying unsigned

### Requirement: File Authorization Refusals Identify the Attempted Effect

File command diagnostics SHALL retain the HTTP status and report any recognized reason from the existing gateway access error. Diagnostics SHALL identify the requested action, resource, and caller selection where known. They SHALL distinguish selected caller evidence from verified attribution and exclude private input.

#### Scenario: A keyed peer push is denied

- **WHEN** the selected gateway refuses the peer's push with HTTP 403 and `insufficient_authority`
- **THEN** stderr identifies the HTTP status, reason, requested `files.push`, exact `files:<mount-id>`, and caller selection
- **AND THEN** it suggests that the target owner use `access explain` to inspect the decision
- **AND THEN** the command retains its existing nonzero exit and sends no retry

#### Scenario: An access error has limited evidence

- **WHEN** the response is missing a recognized reason or has an invalid error payload
- **THEN** the diagnostic retains the HTTP status and safe request context
- **AND THEN** it prints neither the response body nor an inferred reason or principal

### Requirement: Busy File Push Feedback Explains Explicit Recovery

On a confirmed busy push receipt, the CLI SHALL explain on stderr that the candidate remains saved and a new attempt needs a fresh operation ID. It SHALL suggest `--when-idle` only for the verified owning managed runtime. Existing receipt fields and exit behavior SHALL determine the machine-readable result.

#### Scenario: Managed self immediately pushes during a turn

- **WHEN** a signed `agents self files push` returns a busy receipt attributed to managed self
- **THEN** stderr suggests an explicit `--when-idle` attempt using the saved candidate, recorded base, and a fresh operation ID
- **AND THEN** stdout retains the busy receipt and the command exits nonzero without queuing work

#### Scenario: A peer, owner, or unsigned caller receives busy

- **WHEN** a busy receipt comes from a selected-agent command or an unsigned self command
- **THEN** stderr advises an explicit new attempt once the target is ready
- **AND THEN** the guidance does not offer managed-self scheduling

#### Scenario: A push returns a queued or unconfirmed result

- **WHEN** the service confirms a queued intent or the CLI cannot confirm an attempt
- **THEN** the CLI preserves the existing outcome and operation ID
- **AND THEN** it does not present that outcome as busy or suggest retrying it as a new busy attempt

### Requirement: Selected Agent State Shows Verified Owner Policy in Human Output

Human-readable `agents single state` SHALL show the retained roster mode and default permission group and version when the CLI can verify the selected local owner policy. The added view SHALL preserve the structured state response and keep roster membership, signer labels, fingerprints, and key paths out of state.

#### Scenario: The owner inspects a local agent with a detached gateway

- **WHEN** plain or fancy state output renders a selected local agent with an available current owner policy
- **THEN** it reports the retained mode and group without requiring a live gateway

#### Scenario: A caller lacks current local owner evidence

- **WHEN** a human-readable state command resolves a remote or delegated target, or cannot verify the selected local policy
- **THEN** it renders the normal state with no inferred policy values
- **AND THEN** unavailable policy evidence does not prevent delivery of otherwise available operational state

#### Scenario: A caller requests machine-readable state

- **WHEN** the state command runs with `--print-json` or produces a collected structured result
- **THEN** it produces the existing structured state shape without a new owner-policy lookup
