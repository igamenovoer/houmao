# Gateway Versioned File Edits Delta

## ADDED Requirements

### Requirement: Skill Role Templates Bind One Exact Mount

The system SHALL provide skill role templates for one exact `files:<mount-id>` resource. `skill-reviewer` SHALL grant `files.read`. `skill-editor` SHALL grant `files.read` and `files.edit`. `skill-publisher` SHALL grant `files.read` and `files.push`. `skill-maintainer` SHALL grant all three actions. File permissions SHALL remain independent of other mounts and other gateway roles.

#### Scenario: Alice drafts a change and Bob delegates publication separately

- **WHEN** Alice has the editor role on Bob's skills mount and another caller has the publisher role on that mount
- **THEN** Alice can edit and commit her draft, and the publisher can review and push the saved candidate
- **AND THEN** the running agent uses the published revision until push, and history attributes the author and publisher separately

#### Scenario: A reviewer inspects a saved candidate

- **WHEN** Alice holds the reviewer role on Bob's mount and inspects a published revision or saved candidate
- **THEN** the gateway permits the authorized inspection
- **AND THEN** draft mutation and publication still require their respective effects

#### Scenario: A mount or a target changes

- **WHEN** Alice attempts to reuse Bob's skill assignment on another target or another mount with the same display name
- **THEN** the gateway applies only the policy and resource ID verified for the requested effect
- **AND THEN** Alice's original assignment supplies no permission for the other resource

### Requirement: Agent Maintainers Update Qualified Common Plugin Mounts

`agent-maintainer` and its inherited authority in `agent-operator` SHALL supply supported `files.read`, `files.edit`, and `files.push` effects on each exact owner-exposed, qualified common skill or MCP mount on the assigned target. The gateway SHALL resolve qualification and current authority before admitting operations and recheck both before publication.

#### Scenario: Alice updates Bob's qualified common plugins

- **WHEN** Alice holds `builtin:agent-maintainer` on keyed Bob and selects one of his qualified common skill or MCP mounts by exact ID
- **THEN** Alice can inspect, draft, commit, and request publication under the usual prerequisites for that resource
- **AND THEN** Bob's native extension packages, gateway integration configuration, and mounts outside the common scope remain subject to their own authority

#### Scenario: A common mount is unavailable or permission changes

- **WHEN** the requested common plugin has no qualified owner-exposed mount, or Alice loses publication authority before handoff
- **THEN** the gateway refuses the corresponding operation before changing the running plugin
- **AND THEN** it preserves any existing saved candidate according to the normal lease and publication contract

### Requirement: MCP Mounts Validate Provider-Qualified Changes

A qualified MCP mount SHALL expose only the provider's typed common declarations and owner-approved references. The provider SHALL validate the complete candidate within the assigned scope before publication. MCP edits SHALL convey no arbitrary launch, credential, or native harness mutation authority. A target that cannot enforce the declared boundary SHALL report the operation as unsupported.

#### Scenario: A qualified provider updates an MCP declaration

- **WHEN** Alice publishes a candidate with a supported MCP declaration and owner-approved references against Bob's current base revision
- **THEN** the gateway applies the provider-specific validation, exact mount policy, and native handoff checks
- **AND THEN** the receipt distinguishes publication from native activation

#### Scenario: An MCP candidate crosses the update boundary

- **WHEN** a candidate attempts to introduce an unchecked program launch, change a credential definition, or edit native harness configuration outside the mount
- **THEN** the gateway rejects publication before changing the active plugin or crossing the declared boundary

### Requirement: Managed Self Uses Its Own Non-Admin Mount Effects

In keyed mode a current `managed-self` credential SHALL receive the supported non-admin file actions on its own exact owner-exposed mounts. The gateway SHALL verify current qualification and normal file admission prerequisites. Open-roster authorization SHALL continue to follow open `agent-admin` policy.

#### Scenario: Bob edits his own exposed skills or MCP mount

- **WHEN** Bob signs as `managed-self` on his current keyed gateway and selects his qualified skills or MCP mount
- **THEN** Bob can inspect, draft, commit, and request publication for supported non-admin file actions subject to the usual prerequisites
- **AND THEN** Git metadata and receipts attribute each effect to the verified actor

#### Scenario: Bob selects an unexposed or foreign mount

- **WHEN** Bob selects a mount that his gateway has no qualified provider for, or presents his `managed-self` proof for another target's mount
- **THEN** the request fails at the target or resource check before performing a file action

#### Scenario: Bob requests publication during his own active turn

- **WHEN** Bob drafts and commits on a qualified mount during an active turn and immediately pushes that candidate
- **THEN** draft and commit can succeed, and push returns busy before publication when native maintenance cannot be acquired
- **AND THEN** the candidate remains saved for a later explicit attempt with a fresh operation ID

#### Scenario: Bob resumes a signed draft after the first admin enrolls

- **WHEN** Bob opens a signed draft under an empty roster and makes a fresh managed-self request after the roster becomes keyed
- **THEN** the gateway can admit the fresh request against the same current lease when Bob still proves its actor and the mount remains qualified for that effect
- **AND THEN** an earlier in-flight effect admitted under open authority remains subject to the open epoch fence

### Requirement: Managed Self Can Schedule Publication at Idle

The attached gateway SHALL let verified `managed-self` schedule one handoff of a saved candidate with `files.push` on its exact qualified mount. The intent SHALL record its operation ID, publisher, admitted authority, self registration revision, target generation, listener, candidate, expected base, and timing mode. Handoff SHALL acquire the existing maintenance boundary and recheck that intent against current authority and state before publication.

#### Scenario: Bob schedules a saved update during his turn

- **WHEN** Bob signs a publish-at-idle request for a saved skill or MCP candidate during his active turn
- **THEN** the gateway retains the exact intent and provides a receipt by operation ID
- **AND THEN** active, pending, or uncertain native work can keep the intent pending before handoff
- **AND THEN** the gateway performs the authorized publication at a qualified idle boundary and reports publication and activation separately

#### Scenario: A scheduled request loses its original authority or base

- **WHEN** Bob's registered key rotates or is revoked, the runtime generation or listener changes, the admitted authority no longer applies, or the published base moves before handoff
- **THEN** the gateway settles the intent without publishing and preserves the saved candidate for a fresh authorized request

#### Scenario: A caller attempts to schedule without managed-self proof

- **WHEN** a caller invokes publish-at-idle with peer, unsigned, or default-group admission alone
- **THEN** the gateway refuses scheduling before retaining an intent

#### Scenario: Bob checks or repeats a scheduled publication

- **WHEN** Bob reads the receipt with current read authority or repeats the exact admitted intent under its original operation ID
- **THEN** the gateway returns the strongest known state without dispatching a second handoff
- **AND THEN** a different intent or timing mode with the same ID produces a conflict
- **AND THEN** recovery after a committed or uncertain handoff uses retained evidence and never replays the publication

## MODIFIED Requirements

### Requirement: A Draft Lease Isolates File Edits

Opening a draft SHALL bind its admitted origin, target generation, mount, and base commit to an expiring exclusive editing lease. Signed drafts SHALL bind the verified actor kind and principal. Anonymous drafts SHALL require an unguessable lease capability tied to the original open epoch or default setting revision. Before a draft effect, the gateway SHALL recheck the lease and exact admitted authority. Draft changes SHALL stay outside native discovery.

#### Scenario: A peer edits a multi-file skill during a turn

- **WHEN** a peer uses the current lease to create, replace, rename, or delete logical draft entries
- **THEN** the peer can read and diff its draft changes
- **AND THEN** the target's work continues using the published revision

#### Scenario: A replacement lease fences a late upload

- **WHEN** an upload finishes after the peer's lease expires or is replaced
- **THEN** the old upload cannot change the draft or publish data

#### Scenario: The owner replaces a signed draft's enrollment

- **WHEN** the owner revokes the earlier signing key and enrolls a replacement for the same principal
- **THEN** an in-flight effect admitted with the revoked enrollment is refused
- **AND THEN** a fresh request from the replacement key can use the still-current lease if it proves the same principal and has current draft permission

#### Scenario: An edit session ends without a commit

- **WHEN** the peer aborts or lets a draft lease expire
- **THEN** the gateway releases the lease and discards the unpublished edits
- **AND THEN** it performs no publication or activation

#### Scenario: Another anonymous caller attempts to edit the open draft

- **WHEN** an unsigned caller has open administrator permissions and knows the draft ID but lacks its lease capability
- **THEN** the gateway refuses access to that draft without exposing the capability or draft contents
- **AND THEN** history, ordinary status, and logs omit the secret capability

#### Scenario: The admin roster changes during an open lease

- **WHEN** a signed or unsigned operation relies on an earlier open epoch and the roster changes before the write or commit
- **THEN** the gateway refuses the operation without changing the draft or active files
- **AND THEN** reopening the roster cannot restore the earlier admission or an anonymous lease capability bound to its epoch

#### Scenario: The default changes during an anonymous lease

- **WHEN** an unsigned caller opens a draft under an editing default and the default is replaced
- **THEN** the original anonymous lease capability cannot authorize further changes under the replaced decision
- **AND THEN** selecting the original group again does not revive the lease
