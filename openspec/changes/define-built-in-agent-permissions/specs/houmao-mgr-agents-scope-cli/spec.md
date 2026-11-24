# Spec Delta

## ADDED Requirements

### Requirement: Owner Commands Expose Assignable Built-in Roles

`agents single access` SHALL expose assignable built-in role identifiers, versions, and cumulative permissions. `role-assign` SHALL accept those identifiers for an enrolled target principal. `access list` and `access explain` SHALL report the current `default_permission_group` and distinguish default authority, explicit assignments, direct grants, and system authority. Inspection SHALL report assignment expiry. Built-in definitions SHALL remain reserved.

#### Scenario: Bob Assigns a State Observer

- **WHEN** Bob's execution owner runs `access role-assign alice builtin:agent-observer`
- **THEN** Alice receives the cataloged observer permissions on Bob
- **AND THEN** `access list` and `access explain` show the role and its resolved `agent.status.read` permission
- **AND THEN** with this role alone, `access explain` identifies why the incoming `agent.mail.deliver` effect is denied on keyed Bob

#### Scenario: Inspection Explains an Unassigned Caller

- **WHEN** Bob's owner inspects the retained policy and explains an effect for a verified caller with no explicit group
- **THEN** inspection shows Bob's current default group and identifies any permission supplied by that default

#### Scenario: Inspection Explains an Expired Group Assignment

- **WHEN** Bob's owner explains access for a verified caller with a retained expired `builtin:` group assignment
- **THEN** inspection shows the assignment and its expiry and explains why it still suppresses the default

#### Scenario: Alice Needs Common-Plugin Maintenance and Direct Controls

- **WHEN** Bob's owner assigns `builtin:agent-maintainer` to Alice
- **THEN** inspection shows the observer and requester effects plus the qualified common-plugin scope on Bob
- **AND THEN** selecting `builtin:agent-operator` grants the full cumulative set including verbatim input, native slash commands, and interruption from one assignment

#### Scenario: A Caller Attempts to Assign a System-Controlled Group

- **WHEN** the owner tries to assign `managed-self` or `agent-admin` through `role-assign`
- **THEN** the CLI refuses the assignment and identifies the applicable runtime registration or administrator enrollment path
- **AND THEN** policy inspection identifies the roster qualification and any separate default-derived `agent-admin` authority

### Requirement: Admin Commands Set the Target Default Group

`agents single ... access default-group set <group>` SHALL accept any of the six built-in names. It SHALL support a verified gateway, an explicitly selected verified passive endpoint, or an explicit owner-local `--retained` call. Each path SHALL require effective `agent-admin` authority and report the committed policy outcome. The retained paths SHALL support stopped and detached targets.

#### Scenario: An Admin Changes Bob's Default

- **WHEN** a caller with effective `agent-admin` authority selects Bob and sets the default to `agent-observer`
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

### Requirement: Outbound Mail Reports Recipient Policy Admission

An ordinary managed-agent mailbox send SHALL use the caller's verified sender binding and the selected recipient address. The CLI SHALL report the recipient transport's authorization result separately from accepted delivery. A denial or unavailable recipient policy SHALL preserve the original sender identity and fail without switching routes or credentials.

#### Scenario: Observer Alice Sends Mail to Detached Bob

- **WHEN** Alice uses her own authenticated mailbox to send ordinary mail to keyed Bob while her only assignment on Bob is `builtin:agent-observer`
- **THEN** the CLI reports Bob's recipient-policy refusal before delivery even if Bob's gateway is detached
- **AND THEN** it does not report the send accepted, retry through another mailbox channel, or use Bob's sender binding

#### Scenario: Requester Alice Sends Mail to Detached Bob

- **WHEN** Bob assigns Alice `builtin:agent-requester` and the qualified recipient transport confirms delivery
- **THEN** Alice can send from her own mailbox while Bob's gateway is detached
- **AND THEN** the CLI reports the accepted delivery with its existing receipt contract

#### Scenario: A New Sender Uses Bob's Default Without Enrollment

- **WHEN** Alice sends mail through a qualified sender transport to detached keyed Bob with the `agent-requester` default and no matching assignment
- **THEN** Bob evaluates the default before delivery without enrolling Alice in his policy
- **AND THEN** the CLI preserves Alice's verified sender binding and reports the recipient transport's result

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

## MODIFIED Requirements

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
