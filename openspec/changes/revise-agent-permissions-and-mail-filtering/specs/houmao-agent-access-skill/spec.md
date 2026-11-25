# Agent Access Skill Delta

## ADDED Requirements

### Requirement: Access Guidance Teaches Peer Roles and Exact Status Access

The access routine SHALL teach explicit target-scoped assignment, inspection, expiry, and revocation of the cumulative `agent-requester`, `agent-maintainer`, and `agent-operator` roles. Its examples SHALL identify the exact effect, verified actor, and target. The routine SHALL teach an explicit `agent.status.read` grant and disabled principal fallback for status-only access.

#### Scenario: Alice Has an Exact Status Grant

- **WHEN** Bob's owner needs to let verified Alice inspect readiness under a keyed policy
- **THEN** the routine uses `access grant alice agent agent.status.read` and `access default-fallback set alice disabled` for Bob
- **AND THEN** it uses `access explain` to verify the exact grant and the refusal of inherited work-request authority
- **AND THEN** detailed state, usage, transcripts, and artifacts require separate authority

#### Scenario: Alice Can Request Work

- **WHEN** Bob's owner wants Alice to submit attributed work requests in addition to reading status
- **THEN** the routine uses `builtin:agent-requester` and explains how to inspect `agent.status.read` and `agent.request.submit`
- **AND THEN** it explains that ordinary mail uses the sender's verified mailbox and that Bob's mailbox backend applies its own placement rules

#### Scenario: Alice Can Maintain Common Plugins

- **WHEN** Bob's owner wants Alice to update qualified common skills and MCP resources as well as communicate through requester routes
- **THEN** the routine uses `builtin:agent-maintainer` and explains its draft, commit, and publish effects on qualified common resources
- **AND THEN** it keeps gateway plugin instance access, opaque native-special plugins, and direct session control outside the role

#### Scenario: Alice Can Control the Turn

- **WHEN** Bob's owner also wants to permit verbatim prompts, supported native slash commands, or interruption
- **THEN** the routine uses `builtin:agent-operator` and shows its inherited communication and common-plugin maintenance permissions
- **AND THEN** it keeps raw keys and session, model, or admission overrides separately authorized

#### Scenario: Alice Is Delegated Agent Administration

- **WHEN** Bob's owner intends to authorize Alice for `agent-admin` on Bob
- **THEN** the routine guides qualification of Alice's intended SSH key on Bob's existing administrator roster
- **AND THEN** it keeps retained policy administration in Bob's verified execution-owner context

### Requirement: Access Guidance Teaches Default and Principal Fallback Administration

The access routine SHALL teach the retained default, initial `agent-requester` group, and admin-exclusive `access default-group set <group>` and `access default-fallback set <principal> enabled|disabled` commands. It SHALL teach how policy inspection distinguishes signed identity, explicit permissions, per-principal suppression, unsigned admission, open-roster administration, and default-derived permissions.

#### Scenario: Alice Contacts Bob Without Enrollment

- **WHEN** Alice has no explicit assignment or enrollment with keyed Bob
- **THEN** the routine describes the available `agent-requester` default effects and verifies the selected target and operation
- **AND THEN** it explains that a retained `builtin:` group assignment or disabled fallback suppresses the default for the verified caller and that eligible unsigned input uses the configured default

#### Scenario: Bob Inspects the Default for Unsigned Work Requests

- **WHEN** Bob's owner inspects Alice's exact status grant and disabled fallback alongside the `agent-requester` default
- **THEN** the routine explains that Bob denies work requests under Alice's verified status-only policy and admits eligible unsigned work requests under the default
- **AND THEN** it identifies unsigned admission as a separate target policy decision

#### Scenario: Bob Changes the Default Through Agent Administration

- **WHEN** Bob's admin wants to change the default
- **THEN** the routine uses the verified target and `access default-group set <group>` with a current canonical built-in name
- **AND THEN** it identifies `managed-self` and `agent-admin` as available defaults under their existing prerequisites
- **AND THEN** it checks the committed setting and explains that an `agent-admin` default gives otherwise-unassigned eligible callers the setter permission without qualifying an admin key

#### Scenario: Bob's Admin Updates Fallback While He Is Stopped

- **WHEN** Bob's admin needs to change the retained default or a principal's fallback setting while Bob is stopped or his gateway is detached
- **THEN** the routine selects the explicit owner-local or verified direct passive path and uses the same effective admin requirement
- **AND THEN** it explains that the update governs subsequent gateway permission decisions without starting Bob or attaching a gateway

#### Scenario: A Built-in Assignment Expires

- **WHEN** Bob's owner inspects Alice's expired explicit `builtin:` group assignment
- **THEN** the routine distinguishes expiration of assigned effects from removal of the retained assignment
- **AND THEN** it explains that default fallback can apply after the last retained `builtin:` assignment is removed if fallback is enabled for Alice

#### Scenario: Bob Inspects a Migrated Status-Only Default

- **WHEN** Bob's owner inspects an earlier observer default retained as an exact status-only policy
- **THEN** the routine explains the status-only effects shown by inspection
- **AND THEN** it uses the current catalog for any replacement

## MODIFIED Requirements

### Requirement: Access Guidance Binds Resource Templates Explicitly

The access routine SHALL teach `role-put --template --resource` and subsequent role assignment for exact skill mounts, mailbox bindings, AG-UI threads, and plugin instances. It SHALL expose concrete effects and template version through policy inspection.

#### Scenario: Alice Proposes a Skill Update and Bob Publishes It

- **WHEN** Bob delegates editing but retains publication authority
- **THEN** the routine binds `skill-editor` to Bob's exact discovered `files:<mount-id>` for Alice and shows how a separate `skill-publisher` assignment on that mount authorizes publication
- **AND THEN** it routes draft, commit, and publication operations to `houmao-agent-files`

#### Scenario: Alice Reviews a Skill and Keeps Ordinary Contact

- **WHEN** Bob assigns Alice `skill-reviewer` on one mount and keeps the requester default
- **THEN** the routine explains that the reviewer role adds exact mount access and leaves Alice eligible for default work-request authority under her verified identity
- **AND THEN** it shows how disabling fallback for Alice removes default-derived effects while keeping her review access

#### Scenario: Alice Sends Ordinary Email to Bob

- **WHEN** Alice needs to email Bob from Alice's address
- **THEN** the routine routes the send through Alice's own verified mailbox and Bob's recipient address
- **AND THEN** it explains that the selected transport handles submission or deposit and that Bob's mailbox backend owns placement
- **AND THEN** it explains that the `mailbox-sender` template delegates sending with Bob's exact binding

#### Scenario: Bob Applies His Mailbox Placement Policy

- **WHEN** Bob wants to see Alice's gateway status grant separately from his rule for Alice's mail
- **THEN** the routine shows gateway policy inspection for the verified principal and mailbox policy inspection for the explicit sender address on the selected backend binding
- **AND THEN** it explains that the backend matches sender metadata and that gateway grants depend on verified gateway identities
- **AND THEN** it explains that the gateway can relay an owner-signed rule update through `POST /v1/mail/{channel}/policy/apply` and that a capable backend independently verifies the operation before applying it
- **AND THEN** it explains that the backend files matching new mail directly into Archive, leaves existing Inbox items in place when a rule changes, and leaves archived items in Archive when a sender is unblocked
- **AND THEN** it explains that an authorized native mailbox view shows the same backend placement and that a protected binding keeps placement authority outside ordinary gateway credentials

#### Scenario: Bob Delegates Plugin Access

- **WHEN** Bob's owner selects a plugin instance and an exact declared action such as reading the CCCC binding
- **THEN** the routine places the selected action on the one canonical instance resource with `--template plugin-actions` and `--action`
- **AND THEN** it explains the difference between retained role membership and current live applicability

## REMOVED Requirements

### Requirement: Access Guidance Teaches the Built-in Role Catalog

**Reason**: The built-in observer level and its mail-delivery example have been retired.

**Migration**: Teach the remaining peer roles and configure status-only access through an exact grant and disabled fallback.

### Requirement: Access Guidance Teaches Default-Group Administration

**Reason**: Per-principal fallback replaces the observer assignment as a way to limit default-derived effects.

**Migration**: Teach inspection and administration of the target default and each principal's fallback setting.
