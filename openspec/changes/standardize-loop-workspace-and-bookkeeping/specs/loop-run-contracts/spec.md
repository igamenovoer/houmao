## ADDED Requirements

### Requirement: Loop-authored runs declare workspace and bookkeeping contracts separately
Every authored Houmao loop run SHALL declare a workspace contract and a bookkeeping contract as separate parts of the run contract.

Each contract SHALL declare whether it uses a `standard` posture or a `custom` posture.

When the workspace contract uses `standard`, it SHALL select one workspace-manager posture:

- `in-repo`
- `out-of-repo`

The standard workspace contract SHALL describe the selected visibility surface, source-mutation surface, shared writable surfaces when applicable, default read-only shared surfaces, and ad hoc worktree posture.

#### Scenario: Standard in-repo workspace contract is explicit
- **WHEN** an authored loop plan uses the standard in-repo workspace posture
- **THEN** the plan records that the run uses the `in-repo` standard workspace contract
- **AND THEN** it identifies the shared visibility surface, private source-mutation surface, and ad hoc worktree posture explicitly

#### Scenario: Custom contract remains allowed
- **WHEN** an authored loop plan needs a user-defined workspace or bookkeeping posture that does not fit the standard contract
- **THEN** the plan records a `custom` contract for that concern
- **AND THEN** the plan does not pretend the run uses the standard contract

### Requirement: Standard bookkeeping contracts define obligations and explicit locations without a fixed kb tree
When a loop plan uses the standard bookkeeping contract, that contract SHALL define:

- the expected bookkeeping categories,
- ownership and visibility rules,
- update expectations,
- one or more explicit plan-declared bookkeeping locations.

The standard bookkeeping contract SHALL NOT require or imply a fixed Houmao-owned subtree under per-agent `kb/`.

#### Scenario: Standard bookkeeping contract uses user-declared paths
- **WHEN** an authored loop plan uses the standard bookkeeping contract
- **THEN** the plan records explicit bookkeeping file or directory paths chosen for that run
- **AND THEN** it does not require those locations to follow a fixed `kb/loop-runs/<run_id>/...` tree

#### Scenario: Bookkeeping path can live outside kb
- **WHEN** a user-authored loop plan chooses a bookkeeping file in another writable path that fits the workspace contract
- **THEN** the standard bookkeeping contract may point at that explicit location
- **AND THEN** the contract remains valid without moving the bookkeeping into a Houmao-owned `kb/` subtree
