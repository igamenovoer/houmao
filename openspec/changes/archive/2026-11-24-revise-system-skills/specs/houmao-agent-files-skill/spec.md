# Agent Files Skill Delta

## Purpose

Guide authorized operators and peers through inspecting and changing a managed agent's versioned logical files using the target gateway.

## ADDED Requirements

### Requirement: The Agent Files Routine Selects a Qualified Logical Mount
Houmao SHALL expose `agent-files` as a parent-scoped child for both actor entrypoints. Its read-only help and discovery workflow SHALL identify the explicit target gateway, supported live mount, verified caller lane, and exact resource and actions returned by `files mounts`.

#### Scenario: Reviewer Selects a Peer Skill Mount
- **WHEN** a managed reviewer selects a target with an owner-enabled qualified DSH Web `skills` provider
- **THEN** the routine guides the reviewer to discover the owner-selected mount using `agents single ... files`
- **AND THEN** it uses the returned mount ID and published commit rather than deriving them from the display name or a local filesystem path

#### Scenario: Target Has No Verified Mount
- **WHEN** the target gateway is missing or the live provider cannot verify the mount
- **THEN** the routine reports the missing prerequisite
- **AND THEN** it does not fall back to editing the target's files directly or attach a gateway implicitly

### Requirement: Read and Edit Workflows Preserve Draft Isolation
The routine SHALL distinguish published, revision-pinned, and draft reads, and explain bounded result pagination and base64 read content. It SHALL teach exact-base lease acquisition, renewal, logical changes, diff, abort, and commit while keeping anonymous lease capabilities private.

#### Scenario: Read-Only Peer Reviews a Saved Candidate
- **WHEN** a peer with `files.read` wants to review a saved candidate
- **THEN** the routine teaches `history --candidates` and `diff` with the selected commit
- **AND THEN** it does not open a draft lease or change the publication

#### Scenario: An Authorized Editor Saves an Update
- **WHEN** an editor with the required mount permissions changes logical skill files
- **THEN** the routine uses the discovered base, private draft ID, and the caller's authorized lease context
- **AND THEN** it reports the saved candidate and its attribution while treating the published tree as a separate revision

#### Scenario: An Unsigned Caller Edits in Open Mode
- **WHEN** an unsigned lease open supplies an anonymous capability
- **THEN** the routine keeps the capability in private local storage and uses it only on later operations on that draft

### Requirement: Publication and Reconciliation Use Exact Receipts
The routine SHALL teach publication as a separate operation requiring `files.push` on the selected mount, the saved candidate and its recorded base. It SHALL distinguish author and publisher, preserve the operation ID, and report publication, native activation, and readiness separately.

#### Scenario: The Caller Loses a Push Response
- **WHEN** push returns uncertain evidence or loses the response
- **THEN** the routine uses `files status` with the original operation ID and reports the strongest known outcome
- **AND THEN** it does not replay the push or invoke a separate refresh to force the outcome

#### Scenario: The Target Refuses a Stale Base
- **WHEN** the push conflicts with a newer publication
- **THEN** the routine directs the caller to inspect the current base and prepare a new draft for any intended change
- **AND THEN** it never treats a saved candidate as an applied update

#### Scenario: The Target Is Busy
- **WHEN** a push explicitly returns `busy`
- **THEN** the routine reports the candidate as saved and the attempt as refused
- **AND THEN** any later publication is an explicit new attempt after readiness with a fresh operation ID
