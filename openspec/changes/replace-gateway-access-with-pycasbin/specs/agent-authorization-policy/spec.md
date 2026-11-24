# Spec Delta

## Purpose

Let an agent's execution owner control who can use individual Houmao operations on its resources through a single retained authorization policy.

## ADDED Requirements

### Requirement: Policy Evaluates a Verified Caller and a Concrete Operation

Houmao SHALL authorize an operation using a verified caller, the target agent's observed ownership domain, a canonical resource, and a declared action. Direct grants and role assignments SHALL be scoped to one domain. A protected operation SHALL require a matching permission for every distinct protected effect it requests.

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

Owner-enrolled keys SHALL identify stable operator, service, or logical agent principals. A managed self credential SHALL identify the current generation of the selected target agent. Credential enrollment, permission assignment, and target ownership SHALL remain separately attributable.

#### Scenario: An operator rotates an enrolled key

- **WHEN** the owner enrolls a replacement key for the same principal and revokes its earlier key
- **THEN** the replacement proves the same principal and uses its current grants
- **AND THEN** the revoked enrollment and its outstanding proof cannot be reused

#### Scenario: A managed source changes generation

- **WHEN** a managed caller presents self proof from an ended or replaced generation
- **THEN** the target rejects the retired self credential
- **AND THEN** the logical agent's independently enrolled peer credentials and grants follow their own enrollment lifecycle

#### Scenario: Two principals use the same display label

- **WHEN** two enrolled principals have the same human-readable label
- **THEN** proof selects the enrolled identity by its credential binding
- **AND THEN** each principal receives only its own grants and roles

### Requirement: Owner Policy Has One Retained Authority

Houmao SHALL retain a versioned policy bound to each agent's observed owner domain. The policy SHALL retain principal and credential bindings, roster membership, grants, and revisions across same-domain lifecycle changes. Every gateway and passive operation acting on that domain SHALL use the same authority.

#### Scenario: The gateway is reattached or absent

- **WHEN** gateway reattachment or a supported direct passive operation resolves the retained owner domain
- **THEN** it applies the latest policy for that domain
- **AND THEN** discovery and runtime absence cannot substitute a different policy

#### Scenario: The retained policy is lost or unsupported

- **WHEN** a configured target's policy is missing, malformed, unsafe, or uses an unsupported schema
- **THEN** protected access fails closed with a policy error
- **AND THEN** the system does not initialize a substitute empty policy

### Requirement: A Verified Empty Roster Enables Gateway Administration

The gateway-admin role SHALL grant every declared permission for supported client-facing operations in the selected owner domain. A valid empty roster SHALL confer that role on all callers. In a keyed domain it SHALL require proof from a key explicitly enrolled in the admin roster. Admission SHALL preserve caller provenance and enforce operation and runtime prerequisites.

#### Scenario: An ordinary admin operation uses an empty roster

- **WHEN** the retained policy has a verified empty admin roster and a caller invokes a supported client-facing operation
- **THEN** the gateway-admin role authorizes the operation subject to its normal prerequisites
- **AND THEN** the caller remains anonymous or the independently verified principal in diagnostics

#### Scenario: Admin authority covers all declared client-facing effects

- **WHEN** a current admin or a caller admitted under an empty roster requests a supported mail attachment, plugin operation, or peer file operation
- **THEN** the same role supplies every declared permission for the operation and its effects
- **AND THEN** the selected target, declared capabilities, and native readiness still govern execution

#### Scenario: A nonadmin uses scoped permissions

- **WHEN** a verified nonadmin calls a target with a nonempty admin roster
- **THEN** public and applicable scoped permissions govern the call without conferring the gateway-admin role

#### Scenario: Two keys identify one principal

- **WHEN** a principal with one admin-enrolled key signs with a separately enrolled ordinary key on the keyed target
- **THEN** the request uses the principal's scoped grants
- **AND THEN** the ordinary key does not acquire the other key's admin authority

#### Scenario: A caller supplies bad proof in open mode

- **WHEN** a request comes with expired, malformed, or mismatched proof
- **THEN** ingress rejects the proof without applying the anonymous permission

### Requirement: Roster Transitions Change Open Admission Atomically

First admin enrollment SHALL require proposed-key proof and atomic confirmation of the current empty roster. Current admin keys and verified local owner authority SHALL be able to add or remove per-key admin enrollment. Removing the final admin enrollment by roster change or credential revocation SHALL reopen the role to all callers. Earlier open admissions SHALL remain bound to their open epoch.

#### Scenario: Two first-key enrollments compete

- **WHEN** two callers present valid first-key proof for the same empty revision
- **THEN** only one enrollment commits
- **AND THEN** the other attempt cannot enroll a second admin using the earlier empty roster

#### Scenario: The last admin removes its enrollment

- **WHEN** the final admin key enrollment is removed from a valid retained policy, even if ordinary keys remain
- **THEN** new requests can use the full gateway-admin role through open admission
- **AND THEN** an earlier open admission cannot regain authority after an intervening keyed epoch

#### Scenario: An owner rotates the final admin key

- **WHEN** the owner explicitly enrolls the replacement in the admin roster before removing the former final admin key
- **THEN** the target remains keyed throughout rotation

#### Scenario: Anonymous access attempts routine roster management

- **WHEN** an unsigned caller invokes roster management without the first-enrollment proof for an empty roster
- **THEN** the gateway refuses the mutation because the enrollment prerequisites are unmet

### Requirement: The Owner Manages Scoped Policy Independently of Gateway Control

The verified local execution owner SHALL be able to initialize policy and enroll, inspect, grant, and revoke scoped access without a live gateway. Grants SHALL name explicit principals, resources and actions or a supported role, and support an optional expiry. The owner SHALL administer this policy through verified local authority.

#### Scenario: The owner narrows an existing caller

- **WHEN** the owner replaces a nonadmin's operator role with a status-read grant on a target with a nonempty admin roster
- **THEN** the same current credential can still read the status for the granted target
- **AND THEN** a later prompt or interrupt requires an applicable permission

#### Scenario: A gateway admin attempts to create a scoped grant

- **WHEN** a caller relies on the gateway-admin role for a scoped-policy mutation requiring verified local owner authority
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

- **WHEN** the only permission for a nonadmin's requested action on a target with a nonempty roster expires
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

Direct local manager, executor, and policy operations SHALL use verified execution owner authority. Internal backing entrances SHALL require their bound service authority. The gateway-admin role SHALL apply to supported client-facing operations in the selected owner domain.

#### Scenario: An owner operates a target without an attached gateway

- **WHEN** an owner uses an authorized direct local prompt or lifecycle operation on the recorded target
- **THEN** the operation uses the owner binding and native admission without requiring gateway proof

#### Scenario: An HTTP caller claims owner or service identity

- **WHEN** a caller supplies a principal, sender, executor, or service identity in mutable request data
- **THEN** that claim cannot change the admitted caller or confer execution, service, or policy-management authority

#### Scenario: A caller reaches an internal backing entrance

- **WHEN** a caller presents only gateway-admin authority, including under an empty admin roster, to a service backing entrance
- **THEN** the entrance requires its own bound service credential before dispatch
