# houmao-agent-files-skill Specification

## Purpose

Guide authorized operators and peers through inspecting and changing a managed agent's versioned logical files using the target gateway.

## Requirements

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

### Requirement: The Agent Files Routine Teaches Scheduled Self-Publication

The routine SHALL teach `agents self files push --when-idle` for a saved candidate on a qualified own mount. It SHALL distinguish accepted pending work from publication and native activation. It SHALL use `files status` with the original operation ID for reconciliation.

#### Scenario: Bob Finishes a Self-Update Without Another Publisher

- **WHEN** Bob saves a common-plugin candidate during his own active turn
- **THEN** the routine guides him to schedule the exact candidate and its expected base using current managed-self proof
- **AND THEN** it reports the operation ID and uses the retained receipt to establish the eventual result

#### Scenario: An Immediate Push Reports Busy

- **WHEN** Bob's immediate push returns a confirmed `busy` result
- **THEN** the routine reports the candidate as saved
- **AND THEN** a later explicit publish-at-idle request uses a fresh operation ID
### Requirement: Agent files aligns existing skills and mcp mounts and --when-idle with role templates and signer hints
`houmao-agent-files` (`references/mount-scope.md` and `commands/publish.md`) SHALL preserve and align its existing `skills` (`managed_web_skills`) and `mcp` (`managed_web_mcp`/`mcp_servers`) logical mount coverage and self-only `agents self files push --when-idle` recovery guidance with the built-in `agent-maintainer` group, exact-resource role templates (`skill-reviewer`, `skill-editor`, `skill-publisher`, `skill-maintainer`), and mode-aware (`open` vs `keyed`) signer hints.

#### Scenario: File edits align mounts and busy-push recovery with role templates and signer hints
- **WHEN** a caller inspects mounts or pushes committed edits while a DSH Web target is busy
- **THEN** `references/mount-scope.md` preserves `skills` (`managed_web_skills`) and `mcp` (`managed_web_mcp` with `mcp_servers`) mount coverage and explains built-in `agent-maintainer` vs `skill-reviewer`, `skill-editor`, `skill-publisher`, and `skill-maintainer` templates plus `open` vs `keyed` signer selection
- **AND THEN** `commands/publish.md` preserves self-only `agents self files push --when-idle` recovery for busy targets alongside mode-aware signer hints without dropping `--expected-base` or `--operation-id`

### Requirement: Agent files adds explicit Helper Subcommands line and normalizes table parentheses
`houmao-agent-files/SKILL-MAIN.md` SHALL add an explicit `### Helper Subcommands` subsection stating `No helper subcommands are currently exposed.` per `imsight-agent-skill-handling` and remove `()` from the `Subcommand` column in `## Subcommands` tables (`discover`, `inspect`, `edit-draft`, `publish`, `reconcile`, `help`).

#### Scenario: Complex-procedure three-split and table format are strictly compliant
- **WHEN** a reviewer checks `houmao-agent-files/SKILL-MAIN.md` against `imsight-agent-skill-handling`
- **THEN** `## Subcommands` contains `### Procedural Subcommands`, `### Helper Subcommands` (`No helper subcommands are currently exposed.`), and `### Misc Subcommands` with bare command names in table columns

### Requirement: Agent files preserves mount exclusivity, lease capability security, lifecycle separation, and reconcile
`houmao-agent-files` SHALL preserve `## Actor Frame Gate`, no direct target-filesystem fallback, lease exclusivity, 2 MiB decoded write limit, `umask 077` `lease_capability` file handling, draft!=commit!=publish!=refresh separation, `reconcile` by original `operation_id` on uncertain push, and `references/{mount-scope,receipts}.md`.

#### Scenario: Uncertain push reconciles without replay and anonymous lease keeps capability private
- **WHEN** a push status is uncertain or an anonymous lease is opened
- **THEN** `houmao-agent-files` stores `lease_capability` in an owner-private `umask 077` file for `--lease-capability-file` and reconciles uncertain pushes by `operation_id` without replaying
