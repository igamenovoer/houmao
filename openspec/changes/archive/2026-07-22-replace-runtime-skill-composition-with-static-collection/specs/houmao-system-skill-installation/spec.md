## ADDED Requirements

### Requirement: Shared installer resolves packs to static standalone members
The shared system-skill installer SHALL resolve the `admin` and `agent` pack ids to deduplicated standalone skill records from the v4 manifest.

The admin pack SHALL resolve to `houmao-admin-welcome`, `houmao-admin-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite`. The agent pack SHALL resolve to `houmao-agent-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite`.

#### Scenario: Both packs are selected
- **WHEN** an operator explicitly selects both admin and agent packs
- **THEN** the installer resolves six unique standalone skills
- **AND THEN** shared routines and both loop skills occur once in first-occurrence order

### Requirement: Installation stages complete static directories
Copy installation SHALL stage an unmodified recursive copy of each selected public source directory. Symlink installation SHALL link each top-level destination directly to the corresponding complete public source directory.

The installer SHALL NOT call a Markdown composer, create nested mounts, render actor names, filter shared children, or create a hidden materialized skill tree. It SHALL validate the complete static union before committing any destination change.

#### Scenario: Static source contains an invalid child link
- **WHEN** validation finds a broken local link in one selected static skill
- **THEN** installation fails before committing any destination path
- **AND THEN** no partially installed pack or receipt is written

### Requirement: Receipt records shared ownership per standalone skill
The installation receipt SHALL record each projected standalone skill once, including its destination, projection mode, content digest, and non-empty set of owning pack ids.

Installing another pack SHALL add ownership to an existing byte-equivalent shared member. Uninstalling a pack SHALL remove its ownership and SHALL delete the projection only when no remaining installed pack owns it.

#### Scenario: Admin is removed from a home that also owns agent
- **WHEN** a receipt owns both packs and the operator uninstalls admin
- **THEN** admin welcome and admin entrypoint are removed
- **AND THEN** shared routines and both loop skills remain owned by agent
- **AND THEN** the agent entrypoint remains installed

#### Scenario: Last owner of a shared member is removed
- **WHEN** the agent pack is the only remaining owner and is uninstalled
- **THEN** the agent entrypoint, shared routines, pro loop, and lite loop are removed
- **AND THEN** unrelated user-authored skill directories are preserved

### Requirement: One installed collection uses one projection mode
A receipt-owned static collection SHALL use one projection mode for all of its owned members. A later operation requesting a different mode SHALL perform an explicit transactional replacement of the selected installed union or fail before mutation; it SHALL NOT assign conflicting copy and symlink claims to one shared path.

#### Scenario: Agent pack shares copied dependencies with admin
- **WHEN** admin is already installed in copy mode and agent is added in copy mode
- **THEN** the three shared paths remain copied once
- **AND THEN** their receipt owner sets include both packs

### Requirement: V3 composed installations upgrade transactionally to V4 static roots
Status SHALL classify a receipt-owned v3 composed installation as drifted. Upgrade SHALL stage and validate the selected v4 static union, replace only receipt-owned public paths, write the new receipt after successful projection commit, and then remove obsolete receipt-owned composition material.

Untracked or modified same-name paths SHALL remain conflicts and SHALL NOT be overwritten implicitly.

#### Scenario: Healthy V3 agent pack is upgraded
- **WHEN** upgrade finds a receipt-owned v3 agent entrypoint with its nested composed tree
- **THEN** it replaces that owned path with the static v4 agent entrypoint
- **AND THEN** it installs the shared and loop siblings as top-level roots
- **AND THEN** it records all four v4 members in the new receipt

#### Scenario: V3 public path contains unowned modifications
- **WHEN** upgrade cannot prove that a destination is safe receipt-owned content
- **THEN** it reports the exact conflict and preserves the path
- **AND THEN** it does not partially commit the static collection

### Requirement: Managed defaults install the complete static agent pack
Managed launch, rebuild, relaunch, and join SHALL install or synchronize the complete static agent pack in copy mode unless valid policy disables or replaces that selection.

The managed home SHALL contain the agent entrypoint, shared routines, pro loop, and lite loop as top-level siblings. Admin welcome and admin entrypoint SHALL remain absent by default.

#### Scenario: Managed launch uses omitted system-skill policy
- **WHEN** a new managed home is built with the default selection
- **THEN** all four static agent-pack members are copied into the tool-native root
- **AND THEN** no runtime composition directory or admin public skill is created
