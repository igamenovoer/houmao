# Managed Agent Scope CLI Delta

## ADDED Requirements

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

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Outbound Mail Reports Recipient Policy Admission

**Reason**: The selected mail transport owns delivery. Recipient gateway roles govern protected gateway actions.

**Migration**: Use the sender's authorized mailbox binding and interpret the selected transport outcome as described in Outbound Mail Reports the Selected Transport Outcome. Apply owner-authorized recipient rules to file matching future deliveries directly in Archive.
