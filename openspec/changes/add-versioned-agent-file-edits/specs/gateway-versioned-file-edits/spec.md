# Spec Delta

## Purpose

Let authorized callers edit logical agent files in private drafts, record attributed Git history, and push complete revisions through the target gateway at a safe native boundary.

## ADDED Requirements

### Requirement: The Gateway Exposes Owner-Defined Logical Mounts

The target gateway SHALL expose logical mounts owned by its bound agent over HTTP. A mount SHALL declare supported paths, operations, validation, and activation. The gateway SHALL apply shared authorization for the caller, target owner domain, and exact mount using `files.read`, `files.edit`, and `files.push`. Path resolution SHALL stay within that mount and use owner-side storage.

#### Scenario: A peer browses the published revision

- **WHEN** a peer with read authority lists a mount or reads an exposed file
- **THEN** the gateway returns only that mount's authorized logical entries and published revision
- **AND THEN** it excludes native home paths, credentials, and unpublished drafts of other callers

#### Scenario: An edit crosses a mount boundary

- **WHEN** a file request attempts traversal, link following outside its mount, or renames a file into another mount
- **THEN** the gateway rejects that operation before changing any draft or active files

#### Scenario: No target gateway is reachable

- **WHEN** a peer can resolve the agent but has no verified live gateway endpoint
- **THEN** the edit operation reports unavailable without attaching a gateway, writing through the filesystem, or using terminal control

#### Scenario: Read, draft, and publication permissions apply to their effects

- **WHEN** a keyed non-admin requests file operations under a grant for the selected mount
- **THEN** `files.read` permits mount, published-tree, candidate, history, and receipt inspection, `files.edit` permits lease and draft operations including draft reads and commit, and `files.push` permits requesting publication
- **AND THEN** private draft access checks and the other preconditions for each operation still apply

#### Scenario: Enrolled and open administrators have the same file permissions

- **WHEN** a verified administrator in keyed mode or a caller under a valid empty administrator roster requests a supported file action for the selected target domain
- **THEN** each has permission for every supported file action, including inspection, lease and draft operations, and push
- **AND THEN** each request still must satisfy target, proof, lease, draft, single-mount, validation, and runtime prerequisites

#### Scenario: A peer signs from a separate account without a live source execution

- **WHEN** a non-admin on a separate OS account proves a current owner-enrolled SSH key for a stable logical peer agent principal
- **THEN** the target applies that principal's current grants for the exact mount and action without requiring a live source runtime, gateway, or matching execution context
- **AND THEN** the caller cannot read an ungranted mount or use an ungranted action on the granted mount

#### Scenario: Another approved principal receives a scoped grant

- **WHEN** the owner enrolls a credential for another approved principal and grants a file action on a specific mount in keyed mode
- **THEN** the signer can use the granted operation with the same mount and runtime checks as a managed peer

#### Scenario: The owner revokes a source key or mount permission

- **WHEN** an enrolled source key or a required grant is revoked before a requested effect
- **THEN** proof from the revoked key or the earlier authorization cannot authorize that effect
- **AND THEN** a replacement enrolled key for the same logical principal uses the principal's current permissions

### Requirement: A Draft Lease Isolates File Edits

Opening a draft SHALL bind its admitted origin, target generation, mount, and base commit to an expiring exclusive editing lease. An anonymous draft SHALL use an unguessable lease capability bound to the target and open epoch. Draft operations SHALL recheck the lease and current authorization at completion. Changes SHALL remain outside native discovery while the published tree stays readable.

#### Scenario: A peer edits a multi-file skill during a turn

- **WHEN** a peer uses the current lease to create, replace, rename, or delete logical draft entries
- **THEN** the peer can read and diff its draft changes
- **AND THEN** the target's work continues using the published revision

#### Scenario: A replacement lease fences a late upload

- **WHEN** an upload finishes after the peer's lease expires or is replaced
- **THEN** the old upload cannot change the draft or publish data

#### Scenario: An edit session ends without a commit

- **WHEN** the peer aborts or lets a draft lease expire
- **THEN** the gateway releases the lease and discards the unpublished edits
- **AND THEN** it performs no publication or activation

#### Scenario: Another anonymous caller attempts to edit the open draft

- **WHEN** an unsigned caller has open administrator permissions and knows the draft ID but lacks its lease capability
- **THEN** the gateway refuses access to that draft without exposing the capability or draft contents
- **AND THEN** history, ordinary status, and logs omit the secret capability

#### Scenario: The admin roster changes during an open lease

- **WHEN** an in-flight operation relies on an earlier open epoch and the roster authority changes before the write or commit
- **THEN** the gateway refuses the operation without changing the draft or active files
- **AND THEN** reopening the roster cannot restore the earlier capability

### Requirement: Commit Records Immutable Git History

Commit SHALL validate and save the exact draft tree as a Git commit with its base parent, author, committer, and message. It SHALL release the draft lease and return the commit ID. Scoped history and diff SHALL be readable over HTTP. The gateway SHALL support this workflow without a host Git executable.

#### Scenario: A caller commits and reviews a draft

- **WHEN** the peer commits a validated draft and requests its diff
- **THEN** the gateway returns the candidate's recorded changes relative to its base
- **AND THEN** the candidate stays available for push without becoming visible to the running agent

#### Scenario: A draft fails mount validation

- **WHEN** a draft contains an invalid resource or exceeds the configured limits
- **THEN** commit rejects it and returns safe validation evidence without saving a publishable revision

#### Scenario: A draft contains an empty directory

- **WHEN** a peer commits a draft with an empty directory
- **THEN** the committed logical tree represents directories through their files
- **AND THEN** the empty draft directory contributes no persisted entry

#### Scenario: A peer restores earlier contents

- **WHEN** a peer creates a draft from the current publication and restores the logical tree from an authorized earlier revision
- **THEN** committing and pushing that draft adds a new descendant that restores those contents in published history

### Requirement: File History and Receipts Attribute the Actual Callers

The gateway SHALL derive Git author from the authenticated draft origin or explicit anonymous origin and Git committer from the target gateway or its represented target. Managed authors SHALL use a safe synthetic identity based on the verified logical agent ID and label. The gateway SHALL reject caller-supplied attribution and retain the target's OS identity. Receipts and journals SHALL record the actual admitted actor for each effect.

#### Scenario: A cross-account peer saves a commit

- **WHEN** a non-admin on an isolated account commits a draft using its enrolled logical peer agent key
- **THEN** Git history records that peer as author and the target gateway or its represented target as committer
- **AND THEN** the commit receipt identifies the actual authenticated actor

#### Scenario: An anonymous caller saves a commit

- **WHEN** an unsigned caller saves a valid draft using a current anonymous lease capability
- **THEN** Git history and the commit receipt show an explicit anonymous origin
- **AND THEN** the gateway releases the lease and retains the immutable candidate

#### Scenario: A caller supplies an author override

- **WHEN** a request proposes a different Git author, committer, or execution identity
- **THEN** the gateway rejects the override and preserves its owner-side execution identity

### Requirement: Push Compares the Published Base Before Effects

Push SHALL name an immutable candidate, expected published commit, and operation ID. Under target admission it SHALL recheck the current publisher's authorization, candidate, mount, target generation, expected base, and managed projection. An in-flight push using open authority SHALL remain bound to its open epoch. Push SHALL publish only a candidate based on that exact publication.

#### Scenario: Two peers prepared from the same revision

- **WHEN** one peer pushes a candidate and a second peer pushes from the earlier base
- **THEN** the second push returns a revision conflict with the current authorized base
- **AND THEN** it leaves the candidate available for an explicit new draft and dispatches no activation

#### Scenario: A queued browser input claims the target first

- **WHEN** the native maintenance boundary cannot be acquired because affected work is active, pending, or uncertain
- **THEN** push returns busy before publication and retains the immutable candidate for a later explicit attempt

#### Scenario: The target or managed projection changed

- **WHEN** a relaunch replaces the target generation or the gateway observes foreign changes to managed projection authority
- **THEN** push returns a stale-target or projection conflict before effects
- **AND THEN** it does not apply the earlier request to a replacement runtime

#### Scenario: Open authority changes before a push takes effect

- **WHEN** an admitted push relying on open authority reaches its effect after the roster epoch has changed
- **THEN** the gateway refuses that request before publication or activation, including if the roster has become empty again

#### Scenario: A current administrator publishes a retained candidate

- **WHEN** a verified current administrator reviews a retained candidate authored by an anonymous or scoped caller and submits a new push with its exact candidate and expected base
- **THEN** the gateway applies current publisher authorization and ordinary target, base, and runtime preconditions
- **AND THEN** the receipt identifies the administrator as publisher and the commit retains its original author and committer

#### Scenario: An authenticated scoped peer lacks permission at publication

- **WHEN** a peer on an isolated account can read the candidate but its push grant for that mount is absent or revoked at the protected effect
- **THEN** the gateway refuses publication and leaves the active revision unchanged

### Requirement: Push Shows Publication and Activation Separately

The gateway SHALL expose the published commit and native effective commit or evidence separately. An adapter SHALL make a complete projection visible at its qualified publication boundary and report activation at its supported native boundary. Native readiness and partial or unknown effects SHALL remain explicit.

#### Scenario: A prepared revision takes effect

- **WHEN** a supported push publishes a complete revision and verifies its native effect
- **THEN** the receipt reports the new published commit and confirmed effective revision and boundary
- **AND THEN** authorized reads resolve one complete revision

#### Scenario: Only a broader refresh could apply the files

- **WHEN** the mount can activate only through a native operation outside the caller's grant or protected execution scope
- **THEN** the push leaves the candidate staged and reports the limitation before publishing it

#### Scenario: Native activation cannot be confirmed

- **WHEN** the files have been published and native activation reports partial effects or loses attributable confirmation
- **THEN** the receipt retains the published revision and reports the partial or unknown activation outcome
- **AND THEN** it does not claim rollback, provider completion, or whole-agent freshness

### Requirement: Push Receipts Survive Gateway Interruption

The owner SHALL persist the operation identity, actual publisher, and publication intent before effects. An authorized read by operation ID SHALL return the best known result. Repeating the same operation ID and intent SHALL preserve the same receipt without replaying native work after a possible handoff.

#### Scenario: A response is lost after switching the files

- **WHEN** the gateway restarts after a complete projection switch and before returning the receipt
- **THEN** recovery uses the recorded intent and publication evidence to resolve the published revision
- **AND THEN** activation remains unknown until the owner can attribute native evidence

#### Scenario: An operation ID is reused with different inputs

- **WHEN** a caller supplies a different candidate, expected base, or target for an already recorded operation
- **THEN** the gateway returns a conflict without changing the existing receipt or dispatching work

#### Scenario: A fresh attempt follows a confirmed busy result

- **WHEN** an earlier push ended before publication because the owner was busy
- **THEN** the caller can explicitly submit the same candidate and base with a new operation ID

### Requirement: Qualified DSH Web Hosts Expose Private Managed Skills

The first live mount SHALL expose an owner-enabled skill tree through a dedicated provider for the bound DSH Web agent. It SHALL qualify target-scoped discovery and revision-specific reads before advertising live push. Skill names and assets SHALL remain within that provider's owned projection.

#### Scenario: One peer adds, edits, or removes a managed skill

- **WHEN** a qualified push alters a managed skill's metadata, body, or accompanying files
- **THEN** subsequent qualified skill listing and loading reflect the published revision
- **AND THEN** the same native process and conversation remain active without a model turn caused by the push

#### Scenario: A draft shadows a skill from another source

- **WHEN** a candidate would collide with a protected, reserved, or unrelated provider's skill name
- **THEN** the gateway rejects the candidate before publication

#### Scenario: The target has other native configuration edits

- **WHEN** a peer pushes a skill revision while an unrelated MCP or native configuration edit is pending
- **THEN** the operation applies only the managed skill provider's revision
- **AND THEN** it performs no broad native configuration reconciliation or MCP restart

### Requirement: Managed History Follows the Owned Home

Published commits and receipts SHALL survive gateway restart and reattach. An ordinary relaunch of the same verified owned home SHALL reconcile the retained published revision before enabling the mount. Target-generation-bound drafts and pending requests SHALL expire on replacement. A fresh home SHALL begin an independent history.

#### Scenario: The owner relaunches the same home

- **WHEN** a relaunch creates a new generation of the same authorized home
- **THEN** the published skill tree remains available and history can be read with a current grant
- **AND THEN** earlier leases and unexecuted pushes cannot control the new generation
