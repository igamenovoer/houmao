# Spec Delta

## ADDED Requirements

### Requirement: Peer File Commands Select Target and Source Independently

`agents single` SHALL expose `files` operations for the selected agent ID or name. It SHALL verify the attached endpoint through the shared client and support trusted remote coordinates when needed. It SHALL select the caller signer independently of the target or send an unsigned request under verified open mode.

#### Scenario: A source edits a target on another tmux server

- **WHEN** a caller selects an agent by ID or name and explicitly selects the enrolled logical peer's key
- **THEN** the CLI uses the selected signer and target's verified gateway independently of the source agent's runtime, gateway, or tmux placement
- **AND THEN** the file command does not require a tmux socket argument or a source runtime lookup when the signer is explicit

#### Scenario: Only a remote endpoint is available

- **WHEN** the caller selects a target and supplies trusted remote coordinates for its URL, owner context, generation, and gateway presence
- **THEN** the client verifies those coordinates and deployment trust before signing
- **AND THEN** a listener or generation mismatch prevents the command from sending protected input

#### Scenario: Peer routing or authority is unavailable

- **WHEN** the target has no verified attached gateway, a selected signer fails proof, or keyed mode requires a signer that the caller has not selected
- **THEN** the CLI reports that failure before file operations
- **AND THEN** it performs no unsigned retry, local-file or terminal fallback, gateway attachment, or target lifecycle action

#### Scenario: An unsigned caller addresses an open gateway

- **WHEN** the caller selects a verified live target in open mode without selecting a signer
- **THEN** the CLI uses the common unsigned request path and the gateway checks its current open authority and ordinary operation prerequisites
- **AND THEN** a failed explicit proof is refused even if unsigned access would have been allowed

#### Scenario: A scoped peer calls from an isolated OS account

- **WHEN** a keyed non-admin on a separate account selects its enrolled signer and a target mount
- **THEN** the gateway applies only its effective permissions for that mount, including denying an ungranted operation with the same valid proof
- **AND THEN** the CLI needs no target filesystem access, source runtime lookup, or shared execution context

### Requirement: Peer File Commands Expose Read-Only Inspection

`files` SHALL expose `mounts`, `list`, `read`, `diff`, `status`, and `history`. Inspection SHALL use explicit logical paths and applicable revision, draft, or operation references. Published content, candidates, and receipts require current `files.read`. Draft inspection requires the current draft lease and `files.edit`. Inspection SHALL initiate no edit, commit, push, or activation.

#### Scenario: A caller discovers and inspects an authorized mount

- **WHEN** a peer requests mount discovery, file listing, or file content
- **THEN** the CLI returns the authorized mount and its canonical resource ID, or the authorized entries for the selected revision or draft
- **AND THEN** owner-private paths and other callers' drafts remain undisclosed

#### Scenario: A target has no eligible skill projection

- **WHEN** a target lacks the owner-enabled and qualified DSH Web skill mount
- **THEN** discovery omits that mount or reports its availability limit
- **AND THEN** the CLI offers no upgrade, attach, or lifecycle fallback

### Requirement: Peer File Commands Expose Explicit Draft and Push Steps

`files` SHALL expose `lease open`, `lease renew`, `write`, `delete`, `mkdir`, `rename`, `commit`, `abort`, and `push`. Draft mutations SHALL name the applicable lease and logical paths. Anonymous drafts SHALL use the secret lease capability obtained at open. Commit SHALL save the selected draft. Push alone SHALL request publication using the immutable candidate, expected published base, and operation ID.

#### Scenario: A peer commits a draft while the target works

- **WHEN** a peer opens and renews an authorized lease, edits the draft, and commits it
- **THEN** the CLI reports the saved commit ID for later review or push
- **AND THEN** the target continues using its published revision

#### Scenario: The target is busy when the peer pushes

- **WHEN** the gateway refuses the push before publication because the target is busy
- **THEN** the CLI reports the candidate and operation ID with the busy outcome
- **AND THEN** a later explicit attempt of that candidate uses a new operation ID

#### Scenario: A named administrator publishes a retained anonymous candidate

- **WHEN** the authorized administrator selects an immutable candidate saved by an unsigned caller and supplies the exact expected published base
- **THEN** the CLI submits a new signed push and returns a receipt with the current publisher's identity
- **AND THEN** the saved commit retains its anonymous author and target committer

### Requirement: Peer File Writes Return Inspectable Receipts

File mutations SHALL return receipts with applicable references and actual caller attribution. Push results SHALL report publication, activation, and readiness separately. Plain output SHALL show inspection references, and root `--print-json` SHALL expose the typed result. The CLI SHALL give anonymous lease capabilities to the initiating caller and exclude them from ordinary status, history, and logs.

#### Scenario: A push response is lost

- **WHEN** the CLI cannot confirm the outcome after submitting a push
- **THEN** it reports an unconfirmed result with the original operation ID
- **AND THEN** a caller with current `files.read` can use `files status` on that ID without dispatching publication again

#### Scenario: A peer inspects an earlier commit

- **WHEN** the caller selects a saved commit from `files history` or a commit receipt
- **THEN** `files diff` can inspect its recorded changes without replaying the commit or push

### Requirement: File Grants Use Shared Access Administration

The CLI SHALL use `agents single access` for owner-local enrollment, grant, revoke, and inspection of mount permissions. Managed callers SHALL use the existing `agents self access public-key` command to export public signing identity for enrollment. File commands SHALL use the shared credential and policy contracts.

#### Scenario: An owner enrolls or revokes source access

- **WHEN** the verified local owner enrolls a public SSH key for a stable logical peer principal and grants selected `files.read`, `files.edit`, or `files.push` permissions for a mount
- **THEN** shared access inspection reports retained enrollments and grants subject to their current expiry and revocation
- **AND THEN** the scoped peer in keyed mode receives only its effective grants and roles independently of its runtime generation

#### Scenario: An owner inspects a retained grant while the target is detached

- **WHEN** the owner inspects the permission for a mount whose live availability cannot be verified
- **THEN** the CLI can show the retained assignment and reports live applicability as unresolved

#### Scenario: A peer attempts to administer grants

- **WHEN** a caller presents only a scoped file grant or gateway-admin proof to manage the target's general policy
- **THEN** the command refuses access without changing owner state

#### Scenario: A source prepares owner enrollment

- **WHEN** a managed caller requests its public signing identity through `agents self access public-key`
- **THEN** the CLI returns the logical agent's public key and fingerprint for trusted enrollment without exposing private key material or paths or requiring a source gateway
- **AND THEN** exporting the key creates no grant

#### Scenario: Source runtime authority is stale

- **WHEN** a caller cannot establish its managed self context for public-key export
- **THEN** self export fails without disclosing or substituting a signing identity

#### Scenario: An enrolled signer works without current self context

- **WHEN** a caller outside a verified self context uses an explicitly selected already-enrolled signer for a file request
- **THEN** the file command uses that signer directly and the target applies its retained credential and mount policy
