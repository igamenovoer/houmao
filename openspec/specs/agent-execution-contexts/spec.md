# agent-execution-contexts Specification

## Purpose

Define how Houmao enters an externally provisioned execution context and preserves that context's ownership and control authority throughout a managed agent's lifecycle.

## Requirements

### Requirement: Execution profiles select existing contexts independently of agent backends

Houmao SHALL support trusted named execution profiles for the current account, passwordless delegation to an existing Linux account, an existing container, and an SSH-accessible host account. Execution selection SHALL remain independent of the agent backend. Houmao SHALL require externally provisioned accounts, delegation, target installations, project assets, and credential references; launch SHALL NOT provision them.

#### Scenario: Existing Linux account is selected without a password prompt

- **WHEN** an operator selects a configured execution profile for an existing Linux account with restricted passwordless delegation
- **THEN** Houmao enters that account without requesting the account's password or requiring the operator to have unrestricted root authority
- **AND THEN** the selected agent backend remains the backend resolved from the launch source

#### Scenario: Container and SSH profiles execute in their configured targets

- **WHEN** an operator selects a supported container or SSH execution profile with the required target installation and permissions
- **THEN** Houmao performs the operation in that configured container or host account
- **AND THEN** it reports the observed execution context separately from the transport name

#### Scenario: Missing prerequisites do not trigger provisioning

- **WHEN** the configured user, container, target installation, project source, or credential reference is unavailable
- **THEN** the operation reports the missing prerequisite
- **AND THEN** it does not create an account, start a replacement container, deploy project assets, or substitute caller-local assets

### Requirement: Only trusted configured execution routes can authorize delegation

Execution routes SHALL come from operator-controlled configuration and pass target-side admission under the configured OS transport authority. Agent content and request-supplied controller labels SHALL NOT grant delegation. The owner SHALL admit only supported operations within the granted scope and reject unexpected protocol versions, targets, or operation parameters before runtime mutation.

#### Scenario: Unconfigured target is rejected

- **WHEN** a launch request names an execution profile that is not configured for the operator
- **THEN** Houmao rejects it before entering another account or creating runtime state

#### Scenario: Project content cannot supply a delegation command

- **WHEN** a project definition or agent request supplies its own transport command or claims an authorized controller identity
- **THEN** that input does not establish execution authority
- **AND THEN** an unauthorized operation is rejected before changing agent state

#### Scenario: Revoked delegation prevents later control

- **WHEN** OS delegation for a previously launched agent is revoked
- **THEN** later lifecycle commands report authorization failure
- **AND THEN** Houmao does not retry as the caller or use an alternative account

### Requirement: Launch preparation and environment resolution occur in the owner context

Houmao SHALL resolve project definitions, working directories, native homes, credentials, runtime artifacts, and control endpoints within the selected execution context before preparing an agent. Identity environment SHALL reflect the observed target account. Bare-name environment references SHALL resolve there; explicit launch values SHALL retain their declared meaning. Ambient caller roots, credentials, and delegation material SHALL NOT be inherited implicitly.

#### Scenario: Target-only paths are valid launch inputs

- **WHEN** a selected project or workdir exists only in the target context
- **THEN** launch validates and uses that target path without requiring a corresponding caller-local path
- **AND THEN** newly created native-home and runtime files have the target account's ownership

#### Scenario: Caller and owner environments disagree

- **WHEN** the caller has different HOME, registry-root, credential, and bare-name launch environment values from the target account
- **THEN** owner-side resolution uses the target identity and explicitly configured target environment
- **AND THEN** caller-only values enter the launch only through an authorized explicit launch input

### Requirement: Execution bindings distinguish identity, ownership, and controller authority

Each newly managed agent SHALL persist an observed execution binding separate from its logical agent identity. The binding SHALL identify the execution context, host/container when applicable, account and actual UID/GID where available, owner-side state roots, execution-profile reference, and authorized lifecycle controller and scope. A request label alone SHALL NOT authenticate that controller.

#### Scenario: Binding records actual execution ownership

- **WHEN** an operator with a different UID launches an agent through an admitted execution profile
- **THEN** the agent's binding records the observed owner UID/GID and target context
- **AND THEN** agent identity, execution owner, and controller authority are distinguishable in inspection output

### Requirement: Existing agents remain bound to their admitted execution context

Later operations SHALL verify the recorded context and owner before resolving agent artifacts or admitting control. Editing an execution profile SHALL NOT retarget an existing agent. A replaced container, changed account, incompatible target, or missing binding SHALL produce an explicit mismatch or unsupported-state result. Relaunch SHALL preserve the binding while updating live generation and control handles.

#### Scenario: Profile edit cannot redirect a running agent

- **WHEN** a profile used at birth is changed to identify another account, host, container, or state root
- **THEN** a later command detects the mismatch with the saved binding and refuses to control the new target
- **AND THEN** it does not silently migrate the managed agent

#### Scenario: Relaunch preserves execution ownership

- **WHEN** an admitted relaunch replaces the agent's live generation
- **THEN** the replacement retains the logical agent ID and execution binding
- **AND THEN** the new live handles and generation are recorded by the same owner authority

### Requirement: Agent instances under one account retain independent credential bindings

Multiple agents SHALL be allowed to share one execution profile and OS account while retaining separate logical IDs, native homes, runtime state, and selected credential bindings, including distinct private keys where the native tool supports them. Preparing, refreshing, relaunching, or stopping one agent SHALL NOT rewrite another agent's bindings or shared account credential defaults. This contract SHALL NOT claim security isolation between processes sharing a UID.

#### Scenario: Two agents share an owner and use different private keys

- **WHEN** two agents launch under the same account with distinct supported private-key references
- **THEN** each agent's prepared native home and runtime use its selected credential binding
- **AND THEN** relaunching one agent preserves the other agent's home, credential selection, and live session
- **AND THEN** both agents retain the OS permissions of their shared account

### Requirement: Operator delegation credentials are excluded from agent execution

Houmao SHALL keep operator sudo/SSH/container delegation material outside agent homes, manifests, registry locators, and harness environments. Agent credential references SHALL select agent-owned materials rather than implicitly reuse transport authentication. Configured transport use SHALL NOT forward an operator SSH agent, container-control socket, or delegation environment into the launched harness.

#### Scenario: SSH transport authentication is not an agent credential

- **WHEN** the operator uses a private SSH key or local SSH agent to reach the owner context
- **THEN** the launched agent does not receive that key, SSH-agent forwarding, or operator delegation environment
- **AND THEN** its own credentials are resolved from its selected target-side references

### Requirement: Bounded operations use owner-side runtime authority

The execution contract SHALL support finite launch, inspect/state, resume, prompt, interrupt, stop, relaunch, home/status, and refresh operations when the selected backend supports them. Operations SHALL resolve agent identity and current generation in the owner context and fence mutations to that authority. Unsupported transport, backend, streaming, or terminal combinations SHALL return an explicit unsupported result without executing a caller-local substitute.

#### Scenario: Controls use the owner even when the caller has a matching session name

- **WHEN** the caller and target context have tmux sessions with the same name
- **AND WHEN** the operator inspects, interrupts, stops, resumes, or relaunches the delegated agent
- **THEN** each supported operation addresses only the recorded owner context and exact managed-agent authority

#### Scenario: Generation changes before a mutation is admitted

- **WHEN** the owner observes a different live generation after the caller resolves a target but before mutation admission
- **THEN** the mutation returns an authority conflict without acting on the replacement generation

#### Scenario: Interactive attach is unsupported by a bounded transport

- **WHEN** an operator requests an interactive terminal attach through a transport that supports finite requests only
- **THEN** Houmao reports that operation as unsupported
- **AND THEN** it does not attach to a caller-local tmux session

### Requirement: Owner-side tmux operations use an explicit server binding

Houmao SHALL use the recorded tmux server/socket and exact agent handles for owner-side launch, discovery, reconstruction, control, and cleanup. Context entry SHALL discard inherited TMUX and TMUX_PANE selectors. No lifecycle operation SHALL kill or restart the shared localhost tmux server or terminate an unrelated session. Test cleanup SHALL target only its explicitly isolated server and resources.

#### Scenario: Inherited operator tmux variables do not redirect delegation

- **WHEN** Houmao is invoked inside the operator's tmux session with TMUX and TMUX_PANE set
- **THEN** delegated launch and subsequent discovery/control use the explicitly selected owner-side tmux server
- **AND THEN** the operator's enclosing session remains untouched

#### Scenario: Stop preserves sibling agent and user sessions

- **WHEN** the selected owner-side server contains the addressed agent, a sibling agent, and an unrelated user session
- **THEN** stopping or cleaning the addressed agent affects only its validated resources
- **AND THEN** the tmux server and other sessions remain available

### Requirement: Inspection and home refresh preserve execution context and existing semantics

Inspection SHALL remain read-only and qualify owner-local paths with their execution context. Home/status and refresh SHALL run under the saved owner binding without caller-side manifest reconstruction. Refresh SHALL retain the native-agent-home-refresh contract: it SHALL NOT restart the agent or regenerate launch-profile-derived materials. Required restarts SHALL continue through relaunch.

#### Scenario: Remote home inspection returns a qualified path without local mutation

- **WHEN** an operator queries a remote agent's home and common-plugin status
- **THEN** the result identifies the owner context and its native-home path
- **AND THEN** it does not create caller-local homes, open the remote path locally, or refresh the agent

#### Scenario: Refresh runs under the owner without restarting

- **WHEN** an operator refreshes an agent after target-side skill or MCP changes
- **THEN** the owner-side native refresh behavior determines the applied, already-current, or unsupported outcome
- **AND THEN** no restart or launch-profile material regeneration occurs

### Requirement: Transport failure preserves uncertainty without replaying mutations

Execution requests SHALL have bounded transport deadlines and correlated results. Failures before admission SHALL be distinguishable from an indeterminate result after a mutation may have begun. Houmao SHALL NOT automatically replay an indeterminate launch, prompt, stop, refresh, or relaunch, or fall back to local control. Read-only owner inspection SHALL remain available to reconcile reachable state.

#### Scenario: Relaunch response is lost after admission

- **WHEN** the connection fails after the owner admits relaunch but before the result reaches the operator
- **THEN** Houmao reports an indeterminate operation with its correlation and target information
- **AND THEN** it does not automatically submit a second relaunch
- **AND THEN** a later owner-side inspection can report the current generation without mutating it

### Requirement: Execution transports do not broaden communication-only or public HTTP authority

Executor-managed lifecycle control SHALL require the configured owner's OS-authorized execution route. Existing communication-only imports SHALL retain their lifecycle restrictions unless separately admitted by owner authority. This feature SHALL NOT expose passwordless delegation through existing unauthenticated HTTP listeners or treat registry discovery as a grant of control rights.

#### Scenario: Communication-only import remains unable to relaunch

- **WHEN** an imported communication-only agent shares a name or remote address with an execution profile
- **THEN** that import does not gain resume, relaunch, stop, raw terminal, or cleanup authority
- **AND THEN** additional lifecycle access requires an independently authorized owner-context admission

#### Scenario: Public listener cannot request a user switch

- **WHEN** a request to an existing unauthenticated HTTP listener supplies an executor name or controller claim
- **THEN** that request does not grant cross-user, container, or SSH execution authority
