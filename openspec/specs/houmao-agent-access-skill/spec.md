# houmao-agent-access-skill Specification

## Purpose

Guide operators and managed peers through retained gateway policy, SSH key enrollment, and authorized calls to a selected agent.

## Requirements

### Requirement: The Agent Access Routine Preserves Actor and Target Scope
Houmao SHALL expose `agent-access` as the `houmao-agent-access` child of `houmao-shared-routines` for both actor entrypoints. It SHALL provide read-only help and distinguish execution-owner policy changes, live gateway administrator operations, and verified peer operations.

#### Scenario: Managed Agent Requests a Grant
- **WHEN** a caller in the managed-agent frame asks to grant itself access to a peer
- **THEN** the routine explains the target owner's enrollment and grant workflow
- **AND THEN** it preserves the managed-agent frame and avoids attempting owner-local administration

#### Scenario: User Asks Where to Configure a Model Credential
- **WHEN** the task concerns a model-provider login or API credential
- **THEN** the routine hands off to the provider credential workflow without changing gateway policy

### Requirement: Owner Policy Guidance Uses the Retained Target Policy
The routine SHALL teach selection of the target by identity and execution owner, explicit initialization, principal and public-key enrollment, scoped grants and roles, inspection, explanation, revocation, and rotation. It SHALL identify which owner-local operations are available with the gateway detached.

#### Scenario: Owner Grants a Peer Permission to Read a Mount
- **WHEN** the target owner supplies a verified peer public key and an exact mount resource
- **THEN** the routine guides the owner through retaining the principal, enrolling the key, granting `files.read` on `files:<mount-id>`, and checking the grant with `access explain`
- **AND THEN** it distinguishes retained policy from whether the live gateway can verify the mount

### Requirement: Roster Guidance Describes Open and Keyed Modes
The routine SHALL teach that a verified initialized empty roster grants all supported gateway permissions to reachable callers, subject to operation prerequisites. It SHALL describe the first-key and last-key transitions, proof of possession, and the distinction between administrator qualification and credential enrollment.

#### Scenario: Operator Rotates the Only Administrator Key
- **WHEN** the operator intends to keep the gateway in keyed mode during rotation
- **THEN** the routine teaches adding the replacement administrator before removing the old qualification
- **AND THEN** it identifies revocation separately when the old key must lose all ability to prove its principal

### Requirement: Peer Guidance Uses Verified Gateway Coordinates
The routine SHALL teach configuring the source's signer from its owner context, exporting only public identity from verified self, and using scoped `access request` for supported signed JSON requests. It SHALL use trusted target identity, URL, context, generation, presence, and applicable TLS trust without exposing private signing material.

#### Scenario: Managed Peer Calls a Gateway Across Accounts
- **WHEN** a verified managed peer has trusted target coordinates and an enrolled key for the requested effect
- **THEN** the routine uses the configured source signer and selected target gateway independently of the source gateway or tmux topology
- **AND THEN** it reports a stale or unauthorized selection without silently changing the target, credential, or transport

### Requirement: Access Guidance Teaches the Built-in Role Catalog

The access routine SHALL teach explicit target-scoped assignment, inspection, expiry, and revocation of the cumulative `agent-observer`, `agent-requester`, `agent-maintainer`, and `agent-operator` roles. Its examples SHALL identify the exact role, verified actor, target, and permitted operation.

#### Scenario: Alice's Verified Role Grants Observation Rights

- **WHEN** Bob's owner needs to let Alice inspect readiness under a keyed policy
- **THEN** the routine uses `builtin:agent-observer` on Bob's retained policy and explains how to inspect `agent.status.read`
- **AND THEN** it shows how explicit observer assignment replaces the configured default for Alice's verified identity, denying mail delivery and work requests under that identity
- **AND THEN** detailed state, usage, transcripts, and artifacts require separate authority

#### Scenario: Alice Can Send Mail and Request Work

- **WHEN** Bob's owner wants Alice to send ordinary mail and attributed work requests in addition to reading status
- **THEN** the routine uses `builtin:agent-requester` and explains how to inspect `agent.mail.deliver` and `agent.request.submit`
- **AND THEN** it identifies the caller's own sender binding and Bob's retained recipient policy

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

### Requirement: Access Guidance Teaches Default-Group Administration

The access routine SHALL teach the retained `default_permission_group`, initial `agent-requester` value, and admin-exclusive `access default-group set <group>` command. It SHALL explain the relationship among signed identity, explicit assignment, unsigned admission, open-roster administration, and default-derived permissions. It SHALL show how to distinguish those sources in policy inspection.

#### Scenario: Alice Contacts Bob Without Enrollment

- **WHEN** Alice has no explicit assignment or enrollment with keyed Bob
- **THEN** the routine describes the available `agent-requester` default effects and verifies the selected target and operation
- **AND THEN** it explains that a retained `builtin:` group assignment replaces the default for the verified caller and that eligible unsigned input uses the configured default

#### Scenario: Bob Inspects the Default for Unsigned Work Requests

- **WHEN** Bob's owner inspects an explicit observer assignment alongside the `agent-requester` default
- **THEN** the routine explains that Bob denies work requests under the verified observer role and admits eligible unsigned work requests under the default
- **AND THEN** it explains that Bob's administrator can lower the target's default to restrict this anonymous access

#### Scenario: Bob Changes the Default Through Agent Administration

- **WHEN** Bob's admin wants to change the default
- **THEN** the routine uses the verified target and `access default-group set <group>` with the chosen canonical built-in name
- **AND THEN** it checks the committed setting and explains that an `agent-admin` default gives otherwise-unassigned callers the setter permission without qualifying an admin key

#### Scenario: Bob's Admin Changes His Default While He Is Stopped

- **WHEN** Bob's admin needs to change the retained default while Bob is stopped or his gateway is detached
- **THEN** the routine selects the explicit owner-local or verified direct passive path and uses the same effective admin requirement
- **AND THEN** it explains that the updated default governs subsequent mail decisions without starting Bob or attaching a gateway

#### Scenario: An Observer Assignment Expires

- **WHEN** Bob's owner inspects Alice's expired explicit `builtin:` group assignment
- **THEN** the routine distinguishes expiration of assigned effects from removal of the retained assignment
- **AND THEN** it explains that the current default can apply after the last retained `builtin:` group assignment is removed

### Requirement: Access Guidance Binds Resource Templates Explicitly

The access routine SHALL teach `role-put --template --resource` and subsequent role assignment for exact skill mounts, mailbox bindings, AG-UI threads, and plugin instances. It SHALL expose concrete effects and template version through policy inspection.

#### Scenario: Alice Proposes a Skill Update and Bob Publishes It

- **WHEN** Bob delegates editing but retains publication authority
- **THEN** the routine binds `skill-editor` to Bob's exact discovered `files:<mount-id>` for Alice and shows how a separate `skill-publisher` assignment on that mount authorizes publication
- **AND THEN** it routes draft, commit, and publication operations to `houmao-agent-files`

#### Scenario: Alice Reviews a Skill and Keeps Ordinary Contact

- **WHEN** Bob assigns Alice `skill-reviewer` on one mount and keeps the requester default
- **THEN** the routine explains that the reviewer role adds exact mount access and leaves Alice eligible for default contact under her verified identity
- **AND THEN** it shows how an explicit observer group can narrow verified contact while keeping her review access

#### Scenario: Alice Sends Ordinary Email to Bob

- **WHEN** Alice needs to email Bob from Alice's address
- **THEN** the routine routes the send through Alice's own verified mailbox and Bob's recipient address
- **AND THEN** it explains that Bob's retained policy authorizes inbound delivery at the recipient transport even while Bob's gateway is detached
- **AND THEN** a qualified sender with no retained `builtin:` group assignment can receive the current default without recipient enrollment
- **AND THEN** it distinguishes that permission from the `mailbox-sender` template, which delegates sending with Bob's binding

#### Scenario: Bob Delegates Plugin Access

- **WHEN** Bob's owner selects a plugin instance and an exact declared action such as reading the CCCC binding
- **THEN** the routine places the selected action on the one canonical instance resource with `--template plugin-actions` and `--action`
- **AND THEN** it explains the difference between retained role membership and current live applicability

### Requirement: Access Guidance Explains Managed-Self Registration

The access routine SHALL present `managed-self` registration, stable peer enrollment, and `agent-admin` qualification as separate sources of authority. It SHALL teach automatic signing with the verified generation's key in the owner-private SQLite credential store. Environment variables SHALL serve only as runtime locators. The routine SHALL preserve the empty-roster rule regardless of managed-self registration.

#### Scenario: Bob Registers While the Roster Is Empty

- **WHEN** Bob's owner provisions the public registration for his managed generation
- **THEN** the routine explains that the gateway remains open until an administrator key is added
- **AND THEN** it explains that later keyed self calls use the current runtime credential for supported own-agent non-admin effects and their ordinary eligibility checks

#### Scenario: Alice Needs Access to a Peer

- **WHEN** Alice presents a managed-self registration for her own runtime while seeking access to Bob
- **THEN** the routine keeps that registration scoped to Alice's own runtime and guides her toward Bob's default or a stable peer credential for an explicitly assigned effect
- **AND THEN** it explains that Bob's default requires no Bob-side enrollment
- **AND THEN** it keeps the self private key in Alice's owner-private SQLite credential store and omits it from command output

#### Scenario: A New Worker Continues in Bob's Current Generation

- **WHEN** Bob's next headless turn starts a new worker or Bob recovers a process within the same verified generation
- **THEN** the routine directs Bob to the same self commands, which load the currently registered key from the owner-private database automatically
- **AND THEN** it explains that gateway detach and reattach preserve this key and a new generation receives a fresh key

#### Scenario: Bob Rotates a Managed-Self Key

- **WHEN** Bob needs to replace the one registered key for his current generation
- **THEN** the routine explains how proof with the registered key or current admin authority can approve the replacement
- **AND THEN** if the registered key is missing, invalid, or revoked, it directs Bob to explicit admin recovery or an authorized relaunch for a new generation
