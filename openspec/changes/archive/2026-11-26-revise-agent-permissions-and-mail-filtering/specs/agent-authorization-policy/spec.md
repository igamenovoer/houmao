# Agent Authorization Policy Delta

## ADDED Requirements

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

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Inbound Mail Uses the Recipient's Current Policy

**Reason**: The recipient mail backend controls delivery and placement using its own rules. The target's gateway roles and `agent.mail.deliver` are retired as mail delivery controls.

**Migration**: Use transport sender authentication for submission and owner-authorized backend mail rules for recipient placement. Use exact gateway mailbox permissions for ordinary operations on a binding.

### Requirement: The Default Covers Callers Without an Explicit Group

**Reason**: Fallback eligibility now includes a separate setting on each verified principal.

**Migration**: Use explicit grants and the principal's fallback setting to restrict verified callers.

### Requirement: Default Permission Decisions Are Fenced at Handoff

**Reason**: Mail deposit now follows transport authority and fallback has a per-principal revision.

**Migration**: Use current target and principal fallback evidence at protected gateway handoff.
