# agent-authorization-policy Specification

## Purpose

Let an agent's execution owner control who can use individual Houmao operations on its resources through a single retained authorization policy.

## Requirements

### Requirement: Policy Evaluates a Verified Caller and a Concrete Operation

Houmao SHALL authorize the canonical resource and declared action under the target agent's observed owner domain. It SHALL preserve verified caller provenance or explicit anonymous provenance. Direct grants and role assignments SHALL be scoped to one domain. A protected operation SHALL require a matching permission for every distinct protected effect it requests.

#### Scenario: One caller has different rights on two agents

- **WHEN** a caller has an operator role on one agent and an observation grant on another
- **THEN** each target evaluates permissions only within its own ownership domain
- **AND THEN** the observation grant cannot authorize control of the second agent

#### Scenario: Two operations share an HTTP route

- **WHEN** a caller invokes an endpoint that accepts prompt and interrupt requests
- **THEN** the server derives the action from the validated request intent
- **AND THEN** a prompt grant cannot authorize interruption

#### Scenario: A request changes several protected objects

- **WHEN** a caller seeks to change objects that require different permissions
- **THEN** the server verifies all required permissions before performing the effect

### Requirement: Credentials Establish Principals Independently of Permissions

Owner-enrolled keys SHALL identify stable operator, service, or logical agent principals. A `managed-self` credential SHALL identify the current generation of the selected target agent through verified runtime registration. Credential enrollment, permission assignment, and target ownership SHALL remain separately attributable.

#### Scenario: An operator rotates an enrolled key

- **WHEN** the owner enrolls a replacement key for the same principal and revokes its earlier key
- **THEN** the replacement proves the same principal and uses its current grants
- **AND THEN** the revoked enrollment and its outstanding proof cannot be reused

#### Scenario: A managed source changes generation

- **WHEN** a managed caller presents managed-self proof from an ended or replaced generation
- **THEN** the target rejects the retired managed-self credential
- **AND THEN** the logical agent's independently enrolled peer credentials and grants follow their own enrollment lifecycle

#### Scenario: Two principals use the same display label

- **WHEN** two enrolled principals have the same human-readable label
- **THEN** proof selects the enrolled identity by its credential binding
- **AND THEN** each principal receives only its own grants and roles

### Requirement: Owner Policy Has One Retained Authority

Houmao SHALL retain a versioned policy bound to each agent's observed owner domain. It SHALL retain principal and credential bindings, roster membership, grants, default permissions, per-principal fallback settings, and revisions across same-domain lifecycle changes. Gateway and supported direct passive operations SHALL use the same authority.

#### Scenario: The gateway is reattached or absent

- **WHEN** gateway reattachment or a supported direct passive operation resolves the retained owner domain
- **THEN** it applies the latest policy for that domain
- **AND THEN** discovery and runtime absence cannot substitute a different policy

#### Scenario: The retained policy is lost or unsupported

- **WHEN** a configured target's policy is missing, malformed, unsafe, or uses an unsupported schema
- **THEN** protected access fails closed with a policy error
- **AND THEN** the system does not initialize a substitute empty policy

### Requirement: A Verified Empty Roster Enables Gateway Administration

`agent-admin` SHALL grant every declared permission for supported client-facing operations in the selected owner domain. An empty verified roster SHALL supply this authority to every reachable caller. A qualified roster key SHALL supply direct `agent-admin` authority in a keyed domain. The configured default group can supply permissions separately. Admission SHALL preserve caller provenance and enforce operation, transport, and runtime prerequisites.

#### Scenario: An ordinary admin operation uses an empty roster

- **WHEN** the retained policy has a verified empty admin roster and a caller invokes a supported client-facing operation
- **THEN** `agent-admin` authorizes the operation subject to its normal prerequisites
- **AND THEN** the caller remains anonymous or the independently verified principal in diagnostics

#### Scenario: Admin authority covers all declared client-facing effects

- **WHEN** a current admin or a caller admitted under an empty roster requests a supported mail attachment, plugin operation, or peer file operation
- **THEN** the same authority supplies every declared permission for the operation and its effects
- **AND THEN** the selected target, declared capabilities, and native readiness still govern execution

#### Scenario: A nonadmin uses scoped permissions

- **WHEN** a verified nonadmin with an explicit non-admin group calls a target with a nonempty admin roster
- **THEN** public route policy and applicable scoped permissions govern the call without applying the default group

#### Scenario: Two keys identify one principal

- **WHEN** a principal with one admin-enrolled key signs with a separately enrolled ordinary key on the keyed target
- **THEN** the request uses the principal's applicable scoped or default permissions
- **AND THEN** any default permissions remain separate from the other key's roster qualification

#### Scenario: A caller supplies bad proof in open mode

- **WHEN** a request comes with expired, malformed, or mismatched proof
- **THEN** ingress rejects the proof without applying the anonymous permission

### Requirement: Roster Transitions Change Open Admission Atomically

First admin enrollment SHALL require proposed-key proof and atomic confirmation of the current empty roster. Current admin keys and verified local owner authority SHALL be able to add or remove per-key admin enrollment. Removing the final admin enrollment by roster change or credential revocation SHALL reopen administrator authority to all callers. Earlier open admissions SHALL remain bound to their open epoch.

#### Scenario: Two first-key enrollments compete

- **WHEN** two callers present valid first-key proof against the same empty revision
- **THEN** only one enrollment commits
- **AND THEN** the other attempt cannot enroll a second admin using the earlier revision

#### Scenario: The last admin removes its enrollment

- **WHEN** the final admin key enrollment is removed from a valid retained policy, even if ordinary keys remain
- **THEN** new requests can use full `agent-admin` authority through open admission
- **AND THEN** an earlier open admission cannot regain authority after an intervening keyed epoch

#### Scenario: An owner rotates the final admin key

- **WHEN** the owner explicitly enrolls the replacement in the admin roster before removing the former final admin key
- **THEN** the target remains keyed throughout rotation

#### Scenario: Anonymous access attempts routine roster management

- **WHEN** an unsigned caller invokes roster management without the first-enrollment proof for an empty roster
- **THEN** the gateway refuses the mutation before changing the roster

### Requirement: The Owner Manages Scoped Policy Independently of Gateway Control

The verified local execution owner SHALL be able to initialize policy and enroll, inspect, grant, and revoke scoped access without a live gateway. Grants SHALL name explicit principals, resources and actions or a supported role, and support an optional expiry. The owner SHALL administer this policy through verified local authority.

#### Scenario: The owner narrows an existing caller

- **WHEN** the owner replaces a nonadmin's operator role with an exact `agent.status.read` grant and disables default fallback for that principal on a target with a nonempty admin roster
- **THEN** the same current credential can still read the status for the granted target
- **AND THEN** a later prompt or interrupt requires an applicable permission

#### Scenario: A gateway admin attempts to create a scoped grant

- **WHEN** a caller relies on `agent-admin` for a scoped-policy mutation requiring verified local owner authority
- **THEN** the mutation is refused before changing the policy

#### Scenario: An existing installation has only retired authorization data

- **WHEN** the owner upgrades a target that has the former roster format
- **THEN** protected use requires explicit provisioning in the new schema
- **AND THEN** the owner can provision a populated roster or deliberately select a fresh empty roster

#### Scenario: The owner enrolls an offline or cross-account agent

- **WHEN** the target's verified owner supplies an authenticated public key for an explicitly selected logical agent principal
- **THEN** the owner can enroll the key and grant declared operations in the target domain
- **AND THEN** enrollment requires no source runtime, account access, or gateway

#### Scenario: A scoped grant reaches its expiration

- **WHEN** the only permission for a nonadmin's requested action on a target with a nonempty admin roster expires
- **THEN** new use of that action is refused without requiring a policy edit, service restart, or credential revocation

### Requirement: Managed Peers Use the Same Scoped Policy

A peer grant SHALL bind a stable logical agent principal in the target's owner policy. Admission SHALL verify a current peer key enrollment and possession proof without consulting the source UID, execution context, generation, tmux, or liveness. The target binding and policy SHALL be current. Discovery SHALL convey no permission.

#### Scenario: An enrolled source and target are on different tmux servers

- **WHEN** an enrolled peer on another OS account or tmux server presents valid proof for a granted target operation
- **THEN** authorization uses the retained logical principal and verified target domain
- **AND THEN** a source registry record, runtime, or reachable source gateway is unnecessary

#### Scenario: A peer relaunches or rotates its key

- **WHEN** a logical peer relaunches or the target owner explicitly enrolls a replacement key for the same principal
- **THEN** the peer's grant remains applicable to that principal
- **AND THEN** a revoked enrollment and its outstanding proofs cannot authorize a request

#### Scenario: A source name or key is reused

- **WHEN** another source reuses an agent ID, display name, or public key associated with an earlier enrollment
- **THEN** that reuse creates neither a new credential binding nor a grant for a different principal
- **AND THEN** changing the binding requires explicit owner enrollment

#### Scenario: A peer calls outside its grant

- **WHEN** an enrolled nonadmin peer uses valid proof for an ungranted resource or action on a target with a nonempty admin roster
- **THEN** the target denies the request before effects

### Requirement: Effect Admission Rechecks Current Authority

Houmao SHALL recheck sensitive mutations at the owner-controlled point of handoff and order handoff against relevant policy mutation. Revalidation SHALL cover the exact caller, credential, admitted authority, target binding, action, and resource. A completed handoff SHALL retain its execution contract and attributable outcome.

#### Scenario: The owner revokes a permission before handoff

- **WHEN** the caller loses the required permission for a queued request before its mutation handoff
- **THEN** Houmao refuses the pending request before effects

#### Scenario: An admitted admin key loses its roster entry

- **WHEN** a request admitted through named-admin authority reaches handoff after the exact signing key's admin enrollment was removed
- **THEN** Houmao refuses that admission before effects, including if the roster is now empty or the key has since been enrolled again
- **AND THEN** a new request can use current policy and proof

#### Scenario: A mutation handoff wins a revocation race

- **WHEN** the owner authorizes and commits an exact handoff before the permission is revoked
- **THEN** that admitted operation may settle under its execution contract
- **AND THEN** later attempts require current authorization

#### Scenario: A receipt or stream outlives its original authority

- **WHEN** a caller seeks further protected data after its permission expires or is revoked
- **THEN** Houmao refuses further disclosure under that permission
- **AND THEN** authorized owner inspection remains available for retained outcomes

### Requirement: Existing Execution Authority Remains Independent of Gateway Grants

Direct local manager and executor operations, and owner-scoped policy administration, SHALL use verified execution owner authority. Internal backing entrances SHALL require their bound service authority. `agent-admin` SHALL apply to supported client-facing operations in the selected owner domain.

#### Scenario: An owner operates a target without an attached gateway

- **WHEN** an owner uses an authorized direct local prompt or lifecycle operation on the recorded target
- **THEN** the operation uses the owner binding and native admission without requiring gateway proof

#### Scenario: An HTTP caller claims owner or service identity

- **WHEN** a caller supplies a principal, sender, executor, or service identity in mutable request data
- **THEN** that claim cannot change the admitted caller or confer execution, service, or policy-management authority

#### Scenario: A caller reaches an internal backing entrance

- **WHEN** a caller presents only `agent-admin` authority, including under an empty admin roster, to a service backing entrance
- **THEN** the entrance requires its own bound service credential before dispatch

### Requirement: The System Controls Built-In Group Membership

The built-in catalog SHALL contain the three assignable agent roles, `managed-self`, and `agent-admin`. The system SHALL control membership in `managed-self` and `agent-admin`. Public routes SHALL follow their deployment settings. The former `gateway-admin` name SHALL refer to the same roster authority as `agent-admin`. Managed-self registration SHALL leave the roster and open epoch unchanged.

#### Scenario: Self registration leaves Bob open

- **WHEN** Bob registers a managed-self key while his verified admin roster is empty
- **THEN** Bob and anonymous callers retain open `agent-admin` permissions on supported client-facing operations
- **AND THEN** a request signed by Bob's managed-self key records Bob's managed runtime as the caller

#### Scenario: A first administrator enrolls after Bob registers

- **WHEN** Bob's first administrator enrolls after Bob registers his managed-self key
- **THEN** new requests signed by Bob's key use `managed-self` and applicable public route policy
- **AND THEN** admission under the preceding open epoch remains subject to the roster transition fence

#### Scenario: An owner attempts to assign a system-controlled group

- **WHEN** an owner attempts to create, overwrite, or assign a system-controlled group through ordinary role administration
- **THEN** the command rejects the operation and identifies the group's system-controlled membership mechanism

### Requirement: Managed Runtime Registration Uses Verified Local Authority

The verified execution owner SHALL prepare a fresh Ed25519 key and its public registration for each managed generation. Provisioning SHALL work independently of any listener. Registration SHALL bind the key to its owner, target, and generation. Gateway and passive ingress SHALL accept managed-self proof only for the live current generation and its current registration revision.

#### Scenario: A combined launch prepares registration before startup

- **WHEN** the owner reserves a new generation to launch Bob and attach his gateway
- **THEN** Houmao commits the private key record and public registration before starting Bob's native runtime or attaching his gateway

#### Scenario: A supported join adopts an existing live session

- **WHEN** Bob's verified execution owner joins a supported session and establishes a managed generation
- **THEN** Houmao prepares its key and public registration before making the generation available for managed-self proof

#### Scenario: A gateway attaches after the runtime starts

- **WHEN** Bob starts with the gateway detached and an operator later attaches it
- **THEN** the gateway uses the registration prepared by Bob's verified execution owner
- **AND THEN** another detach and reattach within that generation uses the same registration with fresh proof for the new listener

#### Scenario: The passive server serves the live runtime without a gateway

- **WHEN** the current managed-self signer proves a qualified operation on its own target through the passive server while the agent gateway is detached
- **THEN** the passive server resolves the current runtime registration and checks the target's retained policy
- **AND THEN** the operation neither starts a gateway nor uses a backing service credential as client proof

#### Scenario: A prepared generation is unavailable for self proof

- **WHEN** the owner creates the key and registration before the generation becomes live and current
- **THEN** the prepared registration becomes usable for self proof only after Houmao verifies that generation as live and current

#### Scenario: The current key is unavailable on a keyed target

- **WHEN** a managed-self call selects a keyed gateway but the current runtime's registration or private key record is unavailable
- **THEN** the call reports unavailable self authorization without substituting an enrolled peer or administrator credential

#### Scenario: A managed-self key collides with an enrolled key

- **WHEN** an enrollment attempts to qualify the current managed-self public key as a peer or administrator, or registration presents a public key already enrolled for those purposes
- **THEN** the gateway or owner policy operation rejects the conflicting use

### Requirement: Managed-Self Private Keys Use the Owner's SQLite Store

`authorization.sqlite3` SHALL hold `managed-self` private keys in a separate table keyed by generation and key ID. Verified owner execution alone SHALL load a private key and check it against its active public registration in the same snapshot. Houmao SHALL validate ownership, `0700` directories, and `0600` database and sidecar files before use. Environment variables SHALL carry only runtime locators. The database and sidecars SHALL stay outside shared artifacts and remote exports.

#### Scenario: A fresh worker signs for its current generation

- **WHEN** a headless turn starts a fresh worker or Bob recovers under the same verified generation
- **THEN** the self client resolves the current registration and loads the same owner-private key record to sign its bound request challenge

#### Scenario: Different owners run on the same host

- **WHEN** Bob and Carol run under different Linux user IDs and Carol supplies Bob's runtime locator
- **THEN** the lookup requires Bob's execution-owner authority and access to his private key record
- **AND THEN** Carol's process cannot obtain managed-self proof from the locator

#### Scenario: Two agents share an execution account

- **WHEN** Bob and Carol run under the same Linux user ID
- **THEN** normal key selection scopes each agent's key to its own target and generation
- **AND THEN** their credential stores share the trust boundary of that user ID

#### Scenario: A remote operation attempts to export a key

- **WHEN** a remote artifact, file, or owner-file attachment operation selects `authorization.sqlite3` or a SQLite sidecar containing credential data
- **THEN** Houmao refuses the export

#### Scenario: An ingress verifies a managed-self signature

- **WHEN** the gateway or passive server checks managed-self proof for the live current generation
- **THEN** it verifies the signature using the active public registration and its revision

### Requirement: Managed Self Registration Is Exclusive

A gateway target SHALL allow at most one active `managed-self` key for its current generation. Replacement or revocation SHALL require effective `agent-admin` authority or proof from the current key. Recovery of a committed key that is unavailable or revoked SHALL require effective `agent-admin` authority. Replacement SHALL verify candidate possession and generation binding.

#### Scenario: Two keys try to register for the same generation

- **WHEN** two distinct keys attempt initial registration for the same verified generation
- **THEN** at most one key is registered and the other attempt cannot change it without current replacement authority

#### Scenario: The current signer rotates its key

- **WHEN** Bob proves the currently registered key and the replacement candidate proves possession for the same verified runtime
- **THEN** the registrar atomically replaces the binding
- **AND THEN** the predecessor cannot authorize further effects under its retired registration

#### Scenario: The default grants managed-self permissions

- **WHEN** a caller with permissions solely through a `managed-self` default attempts to replace the registered key
- **THEN** the caller has no key replacement authority and the current registration remains active

#### Scenario: A committed key record is missing or its registration is revoked

- **WHEN** the committed private key record is unavailable or the active public registration has been revoked within the same generation
- **THEN** an admin can recover the binding subject to the current runtime and candidate checks
- **AND THEN** the generation retains the recorded registration state and requires recovery authority after restart

#### Scenario: An authorized relaunch establishes a new generation

- **WHEN** an authorized relaunch establishes a new verified runtime generation
- **THEN** the verified execution owner prepares a fresh key for the new generation
- **AND THEN** the gateway rejects outstanding proof for the previous generation

### Requirement: Managed-Self Registration Changes Commit with Owner Policy

Houmao SHALL validate and commit the private key record, active public registration, and its revision in one durable owner policy transaction against the expected generation and revision. A revocation SHALL atomically invalidate the key record and retain the generation's registration history and revocation marker.

#### Scenario: Key replacement stops before the registration commits

- **WHEN** the policy transaction for a replacement key is interrupted or fails before commit
- **THEN** the prior registration and key remain active
- **AND THEN** receipt of proof under the staged key cannot activate that key

#### Scenario: A replacement commits before an interruption

- **WHEN** the owner policy transaction commits a key replacement and the process exits before returning its result
- **THEN** reopening the owner store resolves the new private key and matching active public registration and revision together
- **AND THEN** proof tied to the predecessor remains invalid

#### Scenario: The committed credential store cannot be read

- **WHEN** a committed database is missing or corrupt, or its active registration references missing or invalid private material
- **THEN** the affected signing operation reports unavailable self authority and retains the selected caller
- **AND THEN** recovery requires verified owner action without automatically creating a key, registration, or policy

### Requirement: Managed Self Authorizes Its Own Runtime Effects

The catalog SHALL classify every supported client-facing effect as non-admin or admin-exclusive. In keyed mode `managed-self` SHALL authorize every supported non-admin effect on the caller's verified own target. Admin-exclusive effects SHALL require `agent-admin` authority. All effects SHALL retain their resource, transport, and runtime prerequisites.

#### Scenario: Bob checks and refreshes his common resources

- **WHEN** Bob requests native home or refresh operations against his own attached gateway with current managed-self proof
- **THEN** authorization supplies `native.observe`, `native.refresh.observe`, and `native.refresh.apply` on the `native` resource as required
- **AND THEN** native capabilities and idle admission still determine whether refresh can run

#### Scenario: Bob sends his own ordinary mail

- **WHEN** Bob sends ordinary email from his current mailbox binding using managed-self proof
- **THEN** the gateway admits the declared sender operation for that binding
- **AND THEN** the mail backend governs delivery and placement using any applied recipient mail rules

#### Scenario: Bob uses a supported direct native operation on himself

- **WHEN** Bob invokes a non-admin effect on his own target with verified `managed-self` proof
- **THEN** admission applies the registered effect and the usual native prerequisites without requiring a peer role assignment

#### Scenario: Bob attempts to administer his own roster

- **WHEN** Bob invokes a key enrollment or removal effect using only his `managed-self` key on his keyed target
- **THEN** the admin-exclusive effect is refused before the roster changes
- **AND THEN** an applicable `agent-admin` key can use the supported roster operation

#### Scenario: Alice targets Bob with a managed runtime key

- **WHEN** Alice calls Bob using the key registered for Alice's managed runtime
- **THEN** that proof supplies no managed-self or peer authority on Bob's target
- **AND THEN** Alice's independently enrolled peer key is eligible for Bob's explicit assignments

### Requirement: Owners Assign Versioned Built-In Agent Roles

The owner SHALL be able to assign `builtin:agent-requester`, `builtin:agent-maintainer`, and `builtin:agent-operator` to enrolled principals on one target. These roles SHALL form a cumulative sequence in that order. Assignments SHALL preserve their catalog version or exact effect set, subject to retirement of the ordinary mail delivery effect. Local roles, direct grants, expiry, and revocation SHALL remain available.

#### Scenario: Alice observes Bob's operational state

- **WHEN** Alice proves the identity granted only `agent.status.read` on keyed Bob with fallback and public prompting disabled
- **THEN** the grant supplies only `agent.status.read` on `agent`
- **AND THEN** Bob refuses protected effects for which Alice lacks an applicable grant

#### Scenario: Alice can request work without direct control

- **WHEN** Alice holds only `builtin:agent-requester` on keyed Bob
- **THEN** she can read his status and submit a wrapped work request under `agent.request.submit`
- **AND THEN** verbatim prompt, command invocation, interruption, and private output effects require other authority

#### Scenario: Alice maintains Bob's common plugins

- **WHEN** Alice holds only `builtin:agent-maintainer` on keyed Bob
- **THEN** she retains requester effects and can inspect, draft, and publish updates to Bob's qualified owner-exposed common skills and MCP resources
- **AND THEN** direct prompts, command invocation, interruption, native extension packages, and gateway integration configuration require other authority

#### Scenario: Alice operates Bob's turn

- **WHEN** Alice holds only `builtin:agent-operator` on keyed Bob
- **THEN** she retains maintainer effects and receives `agent.prompt.direct`, `agent.command.invoke`, and `agent.interrupt` on `agent`
- **AND THEN** raw terminal input, override admission, model or session selection, stop, Web entry, private history, and owner-file attachment access retain their own applicable permissions

#### Scenario: A preexisting local role shares a built-in display name

- **WHEN** the owner has a local role called `agent-requester` at upgrade
- **THEN** assignments to that role retain their declared current effects
- **AND THEN** the owner uses `builtin:agent-requester` to select the separate built-in definition

#### Scenario: A new release expands a built-in role definition

- **WHEN** the installed catalog gains a new role version
- **THEN** an earlier assignment continues to apply its previously approved current permissions
- **AND THEN** inspection identifies the assigned version and the exact effect set

#### Scenario: An owner tries to assign the retired observer level

- **WHEN** the owner requests a new `builtin:agent-observer` assignment
- **THEN** the system refuses the assignment and identifies exact status permission and explicit fallback control as the supported configuration

### Requirement: Each Agent Retains a Configurable Default Permission Group

The target policy SHALL retain a default initialized to `agent-requester`. New selections SHALL accept the five current built-in groups. The setting SHALL pin the chosen catalog version or exact definition and retain it across same-domain lifecycle changes. Selecting a group SHALL confer its applicable effects without creating credentials, memberships, or roster entries.

#### Scenario: The administrator sets a different default on Bob

- **WHEN** Bob's administrator sets Bob's default to `agent-operator`
- **THEN** subsequent fallback admission uses Bob's configured operator permissions and inspection reports the configured group and version
- **AND THEN** the change affects only Bob's policy

#### Scenario: The default is a system-controlled group

- **WHEN** an authorized administrator selects `managed-self` or `agent-admin` as Bob's default
- **THEN** the setting accepts the selection and its applicable permission effects
- **AND THEN** admission preserves actual caller provenance and each effect's proof, resource, and runtime prerequisites

### Requirement: Changing the Default Permission Group Is Admin-Exclusive

Updating the retained default SHALL require `admin.default-group.set` on `policy` and current effective `agent-admin` authority, including eligible open-roster or admin-default admission. Houmao SHALL support the update while the agent is stopped or its gateway is detached, given verified retained owner authority. The update SHALL recheck admission and commit the setting, revision, and audit record together. It SHALL preserve the roster.

#### Scenario: A default requester tries to change the setting

- **WHEN** a caller relying on Bob's `agent-requester` default requests a different default
- **THEN** Bob refuses the change before updating the retained policy

#### Scenario: Bob has delegated admin effects through the default

- **WHEN** Bob's default is `agent-admin` and an otherwise unassigned caller qualifies for fallback and requests a new default
- **THEN** the caller is authorized to change it under the current default decision
- **AND THEN** the mutation does not enroll the caller's key or satisfy independent proof requirements for roster operations

#### Scenario: An admin changes Bob's default while he is stopped

- **WHEN** Bob is stopped and an authorized administrator selects his verified retained policy and sets the default to another supported group
- **THEN** the update commits without starting Bob or attaching a gateway
- **AND THEN** subsequent fallback decisions use the new retained revision
- **AND THEN** pending requests relying on the superseded default decision require fresh admission before handoff

#### Scenario: The retained authority changes before the admin mutation

- **WHEN** the selected owner binding or the admitted admin authority becomes invalid before a default change commits
- **THEN** the mutation fails and neither the earlier nor the replacement policy is updated by that attempt

### Requirement: Owners Bind Role Templates to Exact Resources

An owner SHALL be able to instantiate a named template into a target-local role using one exact canonical resource. Instantiation SHALL store the resolved action rows so later catalog changes do not widen assignments. Each expanded row SHALL use an effect declared for the selected resource kind. Wildcards, display names, and implicit cross-target bindings SHALL be rejected.

#### Scenario: The owner installs a mailbox role on one binding

- **WHEN** the owner instantiates `mailbox-reader` or `mailbox-sender` on an exact `mailbox:<channel>:<binding-digest>` resource
- **THEN** the reader template supplies `mail.list` and `mail.peek`, and the sender template supplies `mail.send`
- **AND THEN** delegated sending acts as that mailbox and requires a separate authorization for owner-file attachments

#### Scenario: The owner installs an AG-UI role on one thread

- **WHEN** the owner instantiates `ag-ui-viewer` or `ag-ui-runner` on an exact thread resource
- **THEN** the viewer template supplies `ag-ui.output.read` and the runner template supplies `ag-ui.output.read` and `ag-ui.input.submit`
- **AND THEN** other threads and verbatim direct execution still require their own applicable permissions

#### Scenario: The owner selects plugin actions for one instance

- **WHEN** the owner instantiates `plugin-actions` with explicit actions on a registered gateway plugin instance resource
- **THEN** the role contains only the selected valid actions on that instance binding
- **AND THEN** an action from another plugin or an undeclared action is rejected

#### Scenario: The owner reviews a template assignment

- **WHEN** the owner inspects a template-created role or explains an effect for an assigned principal
- **THEN** the result identifies the template, the exact resource and effects, and the assignment's expiry if set
- **AND THEN** inspection distinguishes retained permissions from live applicability where the provider is unavailable

### Requirement: The Former Prompt Grant Requires Explicit Replacement

The former broad `agent.prompt` action SHALL confer no work-request or native control permission after the policy split. Inspection SHALL identify any retained row that uses the retired action. The owner SHALL be able to replace it with explicitly selected current effects or supported built-in assignments.

#### Scenario: Alice retains Bob's old prompt grant

- **WHEN** Bob's retained policy contains only the former prompt grant for Alice's text and control operations
- **THEN** that grant does not authorize request, verbatim prompt, native command, or interrupt effects
- **AND THEN** Alice's enrollment, separately granted current effects, and applicable default remain independently evaluated
### Requirement: Verified Principals Can Use or Suppress Default Fallback

After open-roster, roster-key, and verified `managed-self` precedence, keyed policy SHALL use its default for eligible unsigned requests and verified callers eligible for fallback. A retained `builtin:` assignment, including an expired one, or a disabled fallback setting SHALL exclude its verified principal from the default. Active local roles and direct grants SHALL add their effects. Invalid supplied proof SHALL fail before fallback.

#### Scenario: Unenrolled Carol contacts Bob

- **WHEN** Carol calls keyed Bob while `agent-requester` is configured and she has no group assignment on Bob
- **THEN** Bob can admit status and wrapped work requests under the default without any Bob-local enrollment
- **AND THEN** Bob records Carol's independently verified identity when available, or anonymous provenance where the transport permits unsigned admission

#### Scenario: Alice has fallback disabled

- **WHEN** Bob resolves Alice's proof to an enrolled principal with fallback disabled
- **THEN** Bob evaluates Alice's request using applicable grants and assignments without applying his default

#### Scenario: Alice holds only an exact skill reviewer role

- **WHEN** keyed Bob retains `agent-requester` as the default and assigns verified Alice a `skill-reviewer` role on one exact mount without a `builtin:` group assignment
- **THEN** Alice receives `files.read` on that mount from the reviewer role
- **AND THEN** her verified work requests still qualify for the requester default while fallback is enabled
- **AND THEN** disabling fallback removes default work request effects for her verified identity and preserves her exact review grant

#### Scenario: A caller with fallback disabled originates a separate unsigned request

- **WHEN** Alice has fallback disabled for her enrolled principal and separately submits an eligible unsigned request to keyed Bob with the requester default
- **THEN** Bob applies the default's applicable effects with anonymous provenance
- **AND THEN** Bob derives no caller identity or grant from names supplied in the request

#### Scenario: Alice's explicit assignment expires

- **WHEN** Alice's retained `builtin:agent-requester` assignment expires while her exact review role remains active
- **THEN** the assignment supplies no effects and continues to suppress fallback
- **AND THEN** Alice retains the review role's exact permissions
- **AND THEN** removing Alice's last retained `builtin:` group assignment makes fallback applicable to subsequent calls if enabled for her principal

#### Scenario: A caller supplies invalid proof on keyed Bob

- **WHEN** a caller presents expired, malformed, or mismatched proof to keyed Bob
- **THEN** admission refuses it before selecting the default or applying anonymous permissions

### Requirement: Target Default and Principal Fallback Decisions Are Fenced at Handoff

Houmao SHALL bind fallback admission to the target's current default-setting revision and selected definition. It SHALL recheck the required authority and current fallback eligibility before protected handoff or continuing disclosure. A replaced default or a disabled fallback setting SHALL retire affected decisions even if the original setting is later restored.

#### Scenario: Bob narrows the default before a queued request runs

- **WHEN** a queued work request relied on Bob's default and Bob changes that setting before handoff
- **THEN** Houmao refuses the old admission before the protected effect
- **AND THEN** restoring the old group value still requires a fresh admission

#### Scenario: Bob disables Alice's fallback before handoff

- **WHEN** Bob admitted Alice's verified request through fallback and then disables fallback for her principal before handoff
- **THEN** Houmao refuses that admission before the protected effect
- **AND THEN** later re-enablement requires fresh admission for the effect

### Requirement: Administrators Can Disable Default Fallback for an Enrolled Principal

Changing an enrolled principal's default fallback setting SHALL require effective `agent-admin` authority for `admin.default-fallback.set` on `policy`. The mutation SHALL recheck the caller and target, then commit the setting, revision, and audit record together. Verified retained authority SHALL support the setting while the target is stopped or its gateway is detached. Policy inspection SHALL report the setting and its effect on the selected principal.

#### Scenario: An administrator grants status-only access to a peer

- **WHEN** Bob's owner grants Alice `agent.status.read` on `agent` and an authorized administrator disables fallback for her enrolled principal on keyed Bob
- **THEN** Alice's verified requests can read status and use other explicitly granted effects
- **AND THEN** an ungranted work request fails even if Bob's default is `agent-requester`

#### Scenario: An ordinary caller attempts to change fallback

- **WHEN** a caller lacks effective `agent-admin` authority for the mutation
- **THEN** the setting and the target's existing grants remain intact

#### Scenario: An administrator re-enables fallback

- **WHEN** an authorized administrator re-enables fallback for Alice
- **THEN** future requests from her verified identity can use the current default if otherwise eligible
- **AND THEN** her explicit grants and roster enrollment remain intact

### Requirement: Retiring the Observer Role Preserves Existing Status-Only Restrictions

Houmao SHALL convert retained `builtin:agent-observer` assignments into equivalent exact grants for `agent.status.read`, retaining expiry and disabling fallback for those principals. It SHALL preserve an existing `agent-observer` default as a retained exact status-only definition until an administrator selects a supported group. Updates SHALL preserve independent permissions and expose the effective definition and provenance in inspection.

#### Scenario: An existing observer is upgraded on a requester-default target

- **WHEN** Bob's policy upgrades with Alice assigned only `builtin:agent-observer` and Bob's default set to `agent-requester`
- **THEN** Alice's existing verified status access continues under an exact grant and her fallback remains disabled
- **AND THEN** Alice gains no wrapped work request or elevated gateway authority through the upgrade

#### Scenario: A retired observer assignment was already expired

- **WHEN** an upgraded policy contains an observer assignment whose expiry has passed and an unrelated active role for the same principal
- **THEN** the migrated observer assignment confers no status permission and preserves fallback suppression
- **AND THEN** the unrelated role's authority and expiry remain intact

#### Scenario: An existing default supplies status only

- **WHEN** Bob upgrades with `agent-observer` saved as his default
- **THEN** his retained default continues to supply only `agent.status.read` to eligible fallback callers
- **AND THEN** inspection identifies the retained exact effect and the administrator can replace it with a supported group
- **AND THEN** a new attempt to select `agent-observer` as a group is refused

### Requirement: Mail Delivery and Gateway Mailbox Effects Have Separate Authorities

Ordinary mail delivery SHALL use the selected backend's recipient rules and verified sender provenance where available. Gateway mailbox operations SHALL authorize the exact effect on the selected binding. Sender claims and delivery results SHALL confer no gateway permissions. The mail backend SHALL enforce its own placement decisions as defined by `gateway-recipient-mail-filtering`.

#### Scenario: A sender uses a permitted offline mailbox while Bob is detached

- **WHEN** an authenticated sender submits ordinary offline mail to a valid recipient whose gateway is detached or runtime is stopped
- **THEN** the offline transport uses its own sender and recipient checks to settle delivery
- **AND THEN** delivery depends only on the transport checks and any applied mail rules

#### Scenario: The provider accepts mail addressed to a keyed target

- **WHEN** an online transport accepts ordinary mail addressed to keyed Bob, including from an unenrolled sender
- **THEN** the provider's delivery rules determine the mailbox result
- **AND THEN** Houmao attributes sender metadata to the message and grants no request, send-as, read, or privileged control authority to that sender

#### Scenario: A caller lacks permission to send from Bob's mailbox

- **WHEN** Alice asks Bob's gateway to send from Bob's mailbox without the applicable binding-scoped permission
- **THEN** the gateway refuses before submitting mail on Bob's behalf

#### Scenario: A sender claims a different identity in a message header

- **WHEN** mail carries Alice's address or display name without independent evidence for the claimed identity
- **THEN** Houmao treats that data as message attribution and derives no verified gateway principal from it
- **AND THEN** any offline transport identity still comes from the supported sender authentication path

### Requirement: Mail Policy Control Requires Independent Mailbox-Owner Authority

On a protected binding, the mail backend SHALL require independently verified proof from an owner credential pinned to that binding to change delivery rules. Effective gateway administration SHALL authorize relay only. The mailbox-owner signing credential SHALL remain outside gateway authority, including on an open gateway.

#### Scenario: Open gateway administration submits an unauthorized policy change

- **WHEN** an unsigned caller can use open gateway administration and submits a mail-policy update without independently verified mailbox-owner proof
- **THEN** the backend leaves its policy and revision unchanged
- **AND THEN** the caller retains their effective gateway permissions for supported gateway operations

#### Scenario: A gateway tries to use an owner authorization for another binding or operation

- **WHEN** the expected backend, mailbox binding, or operation differs from what the mailbox owner signed
- **THEN** the backend refuses to apply the update

### Requirement: Mail Rules Are Authored Separately From Private Gateway Policy

The owner SHALL apply only explicit mailbox delivery rules to a mail backend. The gateway and backend SHALL keep private principal and credential bindings, role assignments, grants, roster membership, default permissions, and fallback settings out of the mail policy payload. A change to either policy SHALL require its own authorization and SHALL confer no implicit authority in the other system.

#### Scenario: Bob gives Alice status access only

- **WHEN** Bob grants Alice exact status access and disables her default gateway fallback
- **THEN** Bob's backend keeps its current mail rules
- **AND THEN** Alice's ordinary mail continues to follow the mail backend's rules

#### Scenario: Bob applies a mail rule for Alice

- **WHEN** Bob applies an explicit block rule matching Alice's supported sender identity
- **THEN** the backend receives only the mail rule and its required mailbox-owner authorization
- **AND THEN** the backend files matching new mail directly in Archive once the rule is committed
- **AND THEN** Bob's gateway policy retains its current principals, roles, and grants
