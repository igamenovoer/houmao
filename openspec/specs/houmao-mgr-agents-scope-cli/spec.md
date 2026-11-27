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
- `agents self` operates on the caller's verified managed runtime,
- `agents external` operates on external-agent registry/reference onboarding for agents whose lifecycle is not controlled by this user's `houmao-mgr`.

`agents single` and `agents self` SHALL NOT be aliases with different selectors. Their command sets SHALL differ where operation authority differs.

#### Scenario: Operator sees explicit agent scopes
- **WHEN** an operator runs `houmao-mgr agents --help`
- **THEN** the help output lists `global`, `single`, `self`, and `external`
- **AND THEN** it does not list direct commands such as `launch`, `list`, `join`, `gateway`, `mail`, or `turn` at the `agents` root

#### Scenario: No scope exposes manual session adoption
- **WHEN** an operator inspects the help or attempts a direct `join` command at the `agents` root or within `global`, `single`, `self`, or `external`
- **THEN** help omits manual session adoption and the invocation fails as an unsupported command
- **AND THEN** no invocation creates a managed identity, manifest, or gateway authority for the current tmux session

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

`agents global` SHALL NOT expose manual session adoption.

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
- **AND THEN** the invocation fails without selecting or adopting a tmux session

#### Scenario: Single command rejects missing selector inside tmux
- **WHEN** an operator runs `houmao-mgr agents single gateway prompt --prompt ping` inside a managed tmux session without a group-level selector
- **THEN** the command fails clearly because `agents single` requires an explicit selected agent
- **AND THEN** the diagnostic points the operator to either supply a single-agent selector or use `houmao-mgr agents self gateway prompt`

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

`agents self mail` SHALL derive routing from the verified manifest and current mailbox binding. The CLI SHALL preserve gateway authorization and binding checks and use runtime-owned mailbox authority for eligible local fallback. Ordinary mailbox operations SHALL respect the backend's placement controls on a protected binding.

#### Scenario: A Web agent completes a notifier round after launch

- **WHEN** a managed Web agent with an attached authorized gateway verifies identity and processes its notified mail with the definition directory unavailable
- **THEN** `agents self mail` can report status, list, read, and reply using the current binding
- **AND THEN** ordinary archive succeeds only where the selected binding permits ordinary placement changes
- **AND THEN** mailbox commands use the verified runtime and current binding to establish the target

#### Scenario: The notified mailbox binding changes

- **WHEN** a mailbox request carries a stale expected binding ID
- **THEN** the command rejects the request before operating on the replacement mailbox

#### Scenario: Ordinary CLI archive targets a protected binding

- **WHEN** an agent tries an ordinary move, archive, or placement-changing mark on a protected binding
- **THEN** the CLI reports that the selected binding reserves placement for its backend
- **AND THEN** a detached gateway or available local route leaves the backend's placement controls in force

### Requirement: Selected-Agent Access Commands Use Verified Owner Authority

`agents single access` SHALL expose policy initialization, principal and credential administration, grant and revoke, list, and explain operations for the selected agent under verified local owner authority. The default-group setter SHALL use its admin-exclusive permission, including on the explicit owner-local path.

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

`agents single` SHALL expose `files` operations for the selected agent ID or name. It SHALL verify the attached endpoint through the shared client and support trusted remote coordinates. It SHALL select the caller signer independently of the target or select unsigned input before submission. The gateway SHALL check current authority and the operation's existing resource prerequisites.

#### Scenario: A source edits a target on another tmux server

- **WHEN** a caller selects an agent by ID or name and explicitly selects the enrolled logical peer's key
- **THEN** the CLI uses the selected signer and target's verified gateway independently of the source agent's runtime, gateway, or tmux placement
- **AND THEN** the file command does not require a tmux socket argument or a source runtime lookup when the signer is explicit

#### Scenario: Only a remote endpoint is available

- **WHEN** the caller selects a target and supplies trusted remote coordinates for its URL, owner context, generation, and gateway presence
- **THEN** the client verifies those coordinates and deployment trust before sending signed or unsigned input
- **AND THEN** a listener or generation mismatch prevents the command from sending protected input

#### Scenario: Peer routing or authority is unavailable

- **WHEN** the target has no verified attached gateway, a selected signer fails proof, or policy refuses the selected caller's file operation
- **THEN** the CLI reports the failure
- **AND THEN** it performs no unsigned retry, local-file or terminal fallback, gateway attachment, or target lifecycle action

#### Scenario: An unsigned caller addresses an open gateway

- **WHEN** the caller selects a verified live target in open mode without selecting a signer
- **THEN** the CLI uses the common unsigned request path and the gateway checks its current open authority and ordinary operation prerequisites
- **AND THEN** a failed explicit proof is refused even if unsigned access would have been allowed

#### Scenario: An unsigned caller addresses a keyed gateway

- **WHEN** a caller selects unsigned input for a file operation on a verified keyed target
- **THEN** the gateway checks the current default group's authority on the exact mount and applies the operation's existing prerequisites
- **AND THEN** caller attribution and anonymous draft lease requirements follow the existing unsigned operation contract

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

Human-readable `agents single state` SHALL show the retained roster mode and default permission definition when the CLI can verify the selected local owner policy. It SHALL identify a named group and its version or the retained exact-effect default. The added view SHALL preserve the structured state response and keep roster membership, signer labels, fingerprints, and key paths out of state.

#### Scenario: The owner inspects a local agent with a detached gateway

- **WHEN** plain or fancy state output renders a selected local agent with an available current owner policy
- **THEN** it reports the retained mode and default definition without requiring a live gateway

#### Scenario: A caller lacks current local owner evidence

- **WHEN** a human-readable state command resolves a remote or delegated target, or cannot verify the selected local policy
- **THEN** it renders the normal state with no inferred policy values
- **AND THEN** unavailable policy evidence does not prevent delivery of otherwise available operational state

#### Scenario: A caller requests machine-readable state

- **WHEN** the state command runs with `--print-json` or produces a collected structured result
- **THEN** it produces the existing structured state shape without a new owner-policy lookup

### Requirement: Owner Commands Expose Assignable Built-in Roles

`agents single access` SHALL expose assignable built-in role identifiers, versions, and cumulative permissions. `role-assign` SHALL accept those identifiers for an enrolled target principal. `access list` and `access explain` SHALL distinguish the retained default definition, default fallback for the principal, explicit assignments, direct grants, and system authority. Inspection SHALL report assignment expiry. Built-in definitions SHALL remain reserved.

#### Scenario: Bob Assigns a State Observer

- **WHEN** Bob's authorized owner grants Alice `agent.status.read` on `agent` and disables her default fallback
- **THEN** Alice's verified access includes status read
- **AND THEN** `access list` and `access explain` show the direct permission and explain why no work-request authority comes from Bob's default

#### Scenario: Inspection Explains an Unassigned Caller

- **WHEN** Bob's owner inspects retained access for a verified caller eligible for the default
- **THEN** inspection shows Bob's retained default definition and identifies any permissions it supplies

#### Scenario: Inspection Explains an Expired Group Assignment

- **WHEN** Bob's owner explains access for a verified caller with a retained expired `builtin:` group assignment
- **THEN** inspection shows the assignment and its expiry and explains why it still suppresses the default

#### Scenario: Alice Needs Common-Plugin Maintenance and Direct Controls

- **WHEN** Bob's owner assigns `builtin:agent-maintainer` to Alice
- **THEN** inspection shows status read, attributed requests, and the qualified common-plugin scope on Bob
- **AND THEN** selecting `builtin:agent-operator` grants the full cumulative set including verbatim input, native slash commands, and interruption from one assignment

#### Scenario: A Caller Attempts to Assign a System-Controlled Group

- **WHEN** the owner tries to assign `managed-self` or `agent-admin` through `role-assign`
- **THEN** the CLI refuses the assignment and identifies the applicable runtime registration or administrator enrollment path
- **AND THEN** policy inspection identifies the roster qualification and any separate default-derived `agent-admin` authority

#### Scenario: A caller attempts to assign the retired observer tier

- **WHEN** the owner invokes `role-assign` with `builtin:agent-observer`
- **THEN** the command rejects it before changing policy
- **AND THEN** inspection can explain migrated exact grants and fallback settings without listing observer as assignable

### Requirement: Admin Commands Set the Target Default Group

`agents single ... access default-group set <group>` SHALL accept `agent-requester`, `agent-maintainer`, `agent-operator`, `managed-self`, or `agent-admin`. It SHALL support a verified gateway, an explicitly selected verified passive endpoint, or an explicit owner-local `--retained` call. Each path SHALL require effective `agent-admin` authority and report the committed policy outcome. The retained paths SHALL support stopped and detached targets.

#### Scenario: An Admin Changes Bob's Default

- **WHEN** a caller with effective `agent-admin` authority selects Bob and sets the default to `agent-operator`
- **THEN** the command verifies Bob's endpoint, submits the requested setting, and reports the committed value and revision
- **AND THEN** an owner inspecting the retained policy sees the new value without a new enrollment or roster change

#### Scenario: An Admin Changes the Default While Bob Is Stopped

- **WHEN** a caller with current admin authority selects an owner-local `--retained` call or the verified direct passive endpoint for stopped Bob
- **THEN** the command changes the retained setting and reports its committed value and revision
- **AND THEN** it leaves Bob stopped and uses the existing unsigned or SSH proof rules for the selected path

#### Scenario: A Local Owner Lacks Admin Authority for the Setter

- **WHEN** a verified local execution owner invokes `--retained` without effective `agent-admin` authority on the selected policy
- **THEN** the command refuses the mutation before updating the retained policy

#### Scenario: A Default Grants the Admin Setter

- **WHEN** Bob's current default is `agent-admin` and a caller with no explicit group uses a supported admission path for the setter
- **THEN** the selected path can authorize the operation through the current default
- **AND THEN** the result preserves the actual caller provenance and identifies the default as the source of authority

#### Scenario: A Non-Admin Attempts to Set the Default

- **WHEN** a caller lacking effective `agent-admin` authority attempts to change the setting
- **THEN** the selected path refuses the request without changing Bob's retained policy
- **AND THEN** the command reports the refusal without retrying through another identity, an unsigned request, or another path

#### Scenario: Bob has a migrated exact-effect default

- **WHEN** Bob's retained default was migrated from the retired status-only tier
- **THEN** inspection reports status read as its retained effect
- **AND THEN** the setter accepts only supported group names for a subsequent default change

### Requirement: Owner Commands Instantiate Exact Resource Role Templates

`access role-put` SHALL accept `--template` with `--resource` to create an owner-named role from a catalog template. `plugin-actions` SHALL also take explicit `--action` values. The resulting role SHALL retain its template version and concrete resource/action pairs. The ordinary `--permission` form SHALL remain available.

#### Scenario: Bob Delegates Draft Editing

- **WHEN** Bob's owner uses `role-put bob-skills-editor --template skill-editor --resource files:<mount-id>` and assigns that role to Alice
- **THEN** `access list` identifies the template and exact mount
- **AND THEN** `access explain` shows that the role contributes `files.read` and `files.edit`
- **AND THEN** inspection continues to report the configured default as the group source when Alice has no retained `builtin:` group assignment
- **AND THEN** this narrow template does not add the broader `builtin:agent-maintainer` role

#### Scenario: Bob Selects Plugin Actions

- **WHEN** Bob's owner selects the `plugin-actions` template, one exact plugin instance resource, and one or more declared `--action` values
- **THEN** the role records only those resource/action pairs

#### Scenario: Bob Configures a Known Resource While Detached

- **WHEN** Bob's owner binds a template to an exact known resource whose live applicability cannot be checked
- **THEN** the CLI can retain the concrete permissions and report live applicability as unresolved
- **AND THEN** it leaves gateway attachment to the owner

#### Scenario: A Template Binding Has Conflicting Inputs

- **WHEN** the owner combines `--permission` and `--template`, omits the resource, or uses a resource of the wrong kind
- **THEN** the CLI refuses the command before changing retained policy

### Requirement: Single Scope Sends Work Requests Without Recipient Enrollment

`agents single request --text` SHALL submit typed `submit_work_request` to a verified gateway or an explicitly selected verified direct passive endpoint. It SHALL select its path and proof before submission. A signed request SHALL use the managed caller's stable peer signer or an explicit owned source. An unsigned request SHALL support eligible open or default admission without enrollment.

#### Scenario: Alice Requests Work From Bob Across Accounts

- **WHEN** Alice runs `houmao-mgr agents single --agent-id <bob-id> request --text "Review PR 42"` with Bob's trusted endpoint coordinates as needed
- **THEN** the command verifies Bob's gateway and signs with Alice's configured peer credential
- **AND THEN** it reports the request reference and known admission or handoff without including Bob's private output

#### Scenario: An Operator Chooses a Source Explicitly

- **WHEN** the verified source owner passes `--source-agent-id` for a configured peer signer
- **THEN** the CLI can use that signer independently of the selected target and the source gateway's availability

#### Scenario: A New Agent Submits an Unsigned Work Request

- **WHEN** a new Alice invokes the request command on keyed Bob using an explicit unsigned selection or with no applicable signing source selected
- **THEN** the command verifies Bob's endpoint and submits one typed request without requiring Bob to enroll Alice
- **AND THEN** Bob evaluates his current policy, and the CLI reports admission or refusal under the existing request and handoff disclosure contract

#### Scenario: Carol Requests Work From Detached Bob Through Passive Ingress

- **WHEN** Carol selects a verified passive endpoint for Bob and Bob has a qualified detached native path
- **THEN** the command submits the typed work request with the selected proof or unsigned admission
- **AND THEN** it reports the passive request reference and known admission or handoff without revealing Bob's private output

#### Scenario: The Request Lane Is Unavailable

- **WHEN** the selected path is unavailable, the selected proof fails, or the target refuses the work-request effect
- **THEN** the CLI reports the outcome on that path
- **AND THEN** it performs no unsigned, other-path, native prompt, terminal input, or mail retry

### Requirement: Self Gateway Commands Use Current Runtime Proof

`agents self files` SHALL use the verified current runtime's attached gateway and accept an exact mount without a target or signer override. Self file and gateway-backed refresh commands SHALL resolve the registered private key from the verified owner's `authorization.sqlite3` for the current generation. Environment variables SHALL serve only as runtime locators, and command output SHALL omit private key material. Explicitly selected unsigned calls SHALL follow applicable admission rules.

#### Scenario: Bob Updates His Own Qualified Mount

- **WHEN** Bob runs `agents self files` in his verified runtime and his keyed gateway exposes an owner-selected qualified mount with non-admin file effects
- **THEN** the CLI signs with Bob's current managed-self key and applies the existing lease, draft, and publication commands under that target's policy
- **AND THEN** publication still checks the current base and native readiness
- **AND THEN** explicit `agents single ... files --self-signer` still selects the managed source's stable peer key

#### Scenario: Bob Checks Native Freshness Against a Keyed Gateway

- **WHEN** Bob runs `agents self refresh --check` or `agents self refresh` with a current managed-self registration
- **THEN** the command signs gateway observations and authorized refresh with that runtime's key and preserves existing native admission and result semantics

#### Scenario: Bob Schedules Publication During His Turn

- **WHEN** Bob uses `agents self files push --when-idle` with a saved candidate and its expected base
- **THEN** the CLI uses current managed-self proof and reports accepted pending work or the known outcome with its operation ID
- **AND THEN** `agents self files status <operation-id>` reports the retained publication, activation, and readiness evidence when available
- **AND THEN** an immediate push keeps its existing `busy` result and a later attempt uses a fresh operation ID

#### Scenario: A New Worker Runs a Self Command

- **WHEN** a new headless turn worker or recovered process invokes a self command within Bob's verified current generation
- **THEN** the command resolves the active key ID and registration revision for that generation and signs with the matching SQLite credential in the verified owner's agent scope
- **AND THEN** an available peer or admin key supplies no proof for the self command

#### Scenario: The Registered Self Key Is Unavailable

- **WHEN** the owner-private database is unreadable or the committed key is missing, fails validation, or cannot prove the current managed-self registration
- **THEN** the signed self command returns an explicit error without creating a key, substituting credentials, or retrying unsigned

#### Scenario: The Caller Explicitly Selects Open Admission

- **WHEN** the verified gateway has an empty admin roster and the caller selects unsigned input for an eligible operation
- **THEN** the operation follows the open admission rules independently of managed-self registration

#### Scenario: Bob Checks Freshness With a Detached Gateway

- **WHEN** Bob invokes self refresh or check while the gateway is detached
- **THEN** the CLI preserves the existing local native inspection, verified no-op, and qualified automatic behaviors
- **AND THEN** an operation requiring a gateway reports that prerequisite without attaching one
### Requirement: Admin Commands Set a Principal's Default Fallback

`agents single ... access default-fallback set PRINCIPAL enabled|disabled` SHALL update the selected principal's retained fallback setting. It SHALL support a verified gateway, an explicitly selected verified passive endpoint, and explicit owner-local `--retained` access. Each path SHALL require the admin-exclusive `admin.default-fallback.set` effect on `policy` and report the committed setting and revision.

#### Scenario: Bob keeps Alice's access to exact grants while detached

- **WHEN** Bob's administrator selects an owner-local retained path or the verified direct passive endpoint and disables fallback for Alice
- **THEN** the change commits without starting Bob or attaching his gateway
- **AND THEN** inspection shows the boolean setting for Alice and the reason her verified access excludes the default

#### Scenario: The caller lacks administrative authority

- **WHEN** the selected path refuses a caller's request to change fallback
- **THEN** the command reports the refusal without changing policy or retrying through another authority

### Requirement: Outbound Mail Reports the Selected Transport Outcome

An ordinary managed-agent mailbox send SHALL use the authorized sender binding and selected recipient address. The CLI SHALL preserve the original sender and channel and distinguish confirmed offline deposit from provider-confirmed online submission. Sender-facing results SHALL omit recipient rules, final placement, wake-up, and processing.

#### Scenario: Alice sends offline mail to detached Bob

- **WHEN** Alice uses her own verified sender binding and the offline registry accepts delivery to Bob's valid address while his gateway is detached
- **THEN** the CLI reports confirmed deposit through the offline transport
- **AND THEN** the same authorized send works whether or not Bob has enrolled Alice's key

#### Scenario: The selected online provider confirms submission

- **WHEN** the sender's provider confirms an ordinary online submission
- **THEN** the CLI reports provider-confirmed submission and leaves recipient placement and agent wake-up unspecified

#### Scenario: The recipient backend archives matching incoming mail

- **WHEN** an offline deposit is confirmed and an applied recipient rule files that mail directly in Archive
- **THEN** the CLI reports the confirmed deposit with the same sender-visible contract as mail deposited to Inbox
- **AND THEN** the result includes no recipient policy or placement details

#### Scenario: Transport refuses the request or cannot confirm the result

- **WHEN** the selected sender binding or transport refuses the operation or reports an uncertain outcome
- **THEN** the CLI preserves the reported outcome and original sender binding
- **AND THEN** it does not retry through another channel, switch credentials, or submit a different message
### Requirement: Agents self scope operates on the verified current managed runtime
`houmao-mgr agents self` SHALL expose maintained operations whose target is the caller's single verified local managed agent.

At minimum, `agents self` SHALL expose:

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

`agents self` SHALL require a verified current identity established through a supported Houmao launch.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Commands that act on a terminal SHALL verify the owning tmux session. Supported headless self commands SHALL accept their verified runtime-owned manifest locator without tmux. Hermes service and TUI self commands that use native runtime authority SHALL accept verified detached daemon callers.

`agents self` commands SHALL NOT accept `--agent-id`, `--agent-name`, or `--current-session` because the target is the current managed-agent identity by definition.

`agents self prompt` and `agents self interrupt` SHALL use the supported control path for the current managed session without accepting explicit agent selectors.

`agents self relaunch` SHALL refresh the active tmux-backed surface for the caller's current managed session. It SHALL require resolvable current-session manifest authority. It SHALL NOT perform selected-agent registry lookup, stopped relaunchable-record revival, degraded/stale active-record recovery, or cross-session targeting.

`agents self` SHALL NOT expose selected-agent lifecycle controls that terminate or clean up the caller's own tmux-backed runtime. In particular, `agents self stop` and `agents self cleanup` SHALL NOT be maintained public paths.

#### Scenario: Self identity requires an existing managed runtime
- **WHEN** an operator runs `houmao-mgr agents self identity` inside a manually started tmux session that lacks verified managed launch authority
- **THEN** the command fails and explains that a verified managed runtime is required
- **AND THEN** it leaves the manual process and its files untouched

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
- **AND THEN** it omits manual adoption and destructive lifecycle commands `stop` and `cleanup`
- **AND THEN** the documentation directs selected-agent stopped/degraded relaunch recovery, stop, and cleanup to `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`

#### Scenario: A Detached Hermes Tool Uses the Self Scope

- **WHEN** a current managed Hermes service or TUI tool invokes `agents self identity`, `agents self state`, or a supported self mail command outside tmux
- **THEN** the command targets the verified current managed runtime without accepting an explicit agent selector
- **AND THEN** terminal-specific operations continue to require their own supported authority
