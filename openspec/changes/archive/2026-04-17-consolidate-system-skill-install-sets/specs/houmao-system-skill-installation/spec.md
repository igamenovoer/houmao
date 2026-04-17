## MODIFIED Requirements

### Requirement: Current Houmao-owned system skills are packaged as maintained runtime assets
The system SHALL package the current Houmao-owned `houmao-*` skills under one maintained Houmao-owned runtime asset root that is separate from project starter assets.

The packaged current-skill catalog SHALL live as one authoritative packaged catalog file under that maintained runtime asset root.

That packaged catalog SHALL identify:

- an explicit `schema_version`,
- the full inventory of current installable Houmao-owned skills,
- the packaged asset subpath for each current skill,
- exactly two installable named skill sets, `core` and `all`, whose members are explicit current skill names,
- fixed auto-install set lists used by Houmao-managed homes and CLI default installation.

The `core` set SHALL contain the closed automation and operator-control system-skill surface. The `all` set SHALL contain every `core` skill plus packaged utility skills.

This change SHALL NOT require conditional rules, profile expansion, nested set expansion, aliases for removed set names, or other dynamic catalog evaluation beyond those fixed named sets and auto-install set lists.

The packaged current-skill catalog SHALL have one matching JSON Schema document, and loading SHALL validate the normalized catalog payload against that JSON Schema before any set expansion or install resolution proceeds.

For the current maintained skill set, each packaged skill `asset_subpath` SHALL equal the skill's own directory name under the maintained asset root and SHALL NOT include a family namespace segment such as `mailbox/` or `project/`.

Logical grouping of current skills MAY be expressed through documentation and set descriptions, but the installable named-set surface SHALL remain `core` and `all`.

#### Scenario: Maintainer inspects the packaged current-skill catalog
- **WHEN** a maintainer inspects the Houmao-owned packaged system-skill assets
- **THEN** the current `houmao-*` skills are available from one maintained runtime asset root
- **AND THEN** project starter assets remain in their own separate asset tree
- **AND THEN** one authoritative packaged catalog file identifies the current installable skill inventory, fixed auto-install set lists, explicit `schema_version`, and exactly the `core` and `all` named sets
- **AND THEN** each current packaged skill directory lives directly under that asset root using its skill name as the relative `asset_subpath`

#### Scenario: Catalog exposes closed core and all sets
- **WHEN** a maintainer inspects the packaged current-skill catalog
- **THEN** the `core` set resolves the closed automation and operator-control skill surface
- **AND THEN** the `all` set resolves every `core` skill plus packaged utility skills
- **AND THEN** removed granular set names such as `user-control`, `mailbox-full`, `mailbox-core`, `agent-memory`, `agent-instance`, `agent-messaging`, `agent-gateway`, `touring`, `agent-inspect`, and `utils` are not current installable named sets

#### Scenario: Loader rejects a schema-invalid packaged catalog
- **WHEN** Houmao loads the packaged current-skill catalog
- **AND WHEN** the normalized catalog payload violates the packaged JSON Schema
- **THEN** catalog loading fails explicitly before set expansion or install resolution begins
- **AND THEN** Houmao does not proceed to filesystem mutation from that invalid packaged catalog

### Requirement: Shared installer supports named set selection and explicit current-skill selection
The shared installer SHALL support two selection modes for the current Houmao-owned skill set:

- one or more current named skill sets,
- one or more explicitly selected current skill names.

The current installable named skill sets SHALL be `core` and `all`.

Whenever Houmao automatically installs its own current skills into a managed home, it SHALL use the packaged catalog's fixed auto-install set lists.

The packaged catalog SHALL set:

- `managed_launch_sets = ["core"]`
- `managed_join_sets = ["core"]`
- `cli_default_sets = ["all"]`

When installation input includes multiple named sets plus explicit skill names, the resolved install list SHALL preserve first occurrence order and SHALL contain each selected skill at most once.

That automatic or explicit selection SHALL NOT depend on conditional rule evaluation in this change.

#### Scenario: Managed brain construction uses the managed-launch auto-install set list
- **WHEN** Houmao constructs a managed home that performs default Houmao-owned skill installation
- **THEN** it installs the skill list resolved from the packaged current-skill catalog's `managed_launch_sets`
- **AND THEN** that fixed list is `["core"]`
- **AND THEN** that automatic selection does not depend on a second mailbox-only default list or any removed granular set

#### Scenario: Explicit installation resolves multiple named sets and explicit skills
- **WHEN** an operator explicitly selects `core` or `all` plus one current Houmao-owned skill for installation
- **THEN** the installer resolves the final install list by expanding the selected sets in order, appending the explicit skill, and deduplicating by first occurrence
- **AND THEN** it does not silently replace that explicit selection with an internal auto-install set list

#### Scenario: Unknown set fails explicit installation
- **WHEN** an operator explicitly selects one named set for installation
- **AND WHEN** that set name is not `core` or `all`
- **THEN** the installation fails explicitly
- **AND THEN** the installer does not guess another set or proceed with partial resolution

#### Scenario: Loader rejects a set that references an unknown skill
- **WHEN** Houmao loads the packaged current-skill catalog
- **AND WHEN** one named set references a skill name not present in the packaged skill inventory
- **THEN** catalog loading fails explicitly before installation begins
- **AND THEN** Houmao does not proceed with partial set expansion

## ADDED Requirements

### Requirement: Installable system-skill sets are closed over internal skill routing
Each installable named set in the packaged current-system-skill catalog SHALL be closed over internal system-skill routing references.

If a packaged skill included in a named set references another packaged catalog skill as a routing target from its Markdown skill instructions or subskill pages, that referenced skill SHALL also be included in the same set.

This closure requirement SHALL apply to every installable named set, including `core` and `all`.

#### Scenario: Catalog test catches an omitted internal routing target
- **WHEN** a packaged skill in `core` references another catalog skill from its Markdown instructions
- **AND WHEN** the referenced skill is omitted from `core`
- **THEN** catalog validation or regression coverage fails
- **AND THEN** maintainers must either add the referenced skill to `core` or remove the routing reference

### Requirement: Packaged utility skills are available through all
The packaged current-system-skill catalog SHALL include `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr` as current installable utility skills.

The `all` set SHALL include both utility skills.

The `core` set SHALL exclude utility skills unless a future change explicitly promotes a utility into the managed core surface.

The packaged catalog's fixed `cli_default_sets` selection SHALL include `all`, so omitted-selection explicit CLI installs include utility skills by default.

The packaged catalog's fixed `managed_launch_sets` and `managed_join_sets` selections SHALL include `core`, so managed launch and join do not install utility skills by default.

#### Scenario: CLI default includes utility skills
- **WHEN** an operator installs system skills into an external tool home without selecting `--skill-set` or `--skill`
- **THEN** the installer resolves `cli_default_sets = ["all"]`
- **AND THEN** the resolved skill list includes `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr`

#### Scenario: Managed auto-install excludes utility skills
- **WHEN** Houmao installs system skills into a managed launch or join home
- **THEN** the installer resolves `core`
- **AND THEN** the resolved skill list excludes `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr`

## REMOVED Requirements

### Requirement: Packaged system-skill catalog includes low-level agent-definition guidance in the user-control set
**Reason**: The packaged catalog no longer exposes `user-control` as an installable set. `houmao-agent-definition` remains packaged and is included through `core` and `all`.

**Migration**: Use `--skill-set core`, `--skill-set all`, or explicit `--skill houmao-agent-definition`.

#### Scenario: Agent-definition remains available without user-control
- **WHEN** an operator lists or installs current system skills
- **THEN** `houmao-agent-definition` remains a current installable skill
- **AND THEN** `user-control` is not required as a named set to install it

### Requirement: Packaged system-skill catalog includes agent-instance lifecycle guidance and adds it to CLI-default installs
**Reason**: Dedicated lifecycle, messaging, and gateway sets have been replaced by the closed `core` and `all` sets. The skills remain packaged and are included through those current sets.

**Migration**: Use `--skill-set core`, `--skill-set all`, or explicit `--skill` names for narrow installs.

#### Scenario: Lifecycle skills remain available through current sets
- **WHEN** an operator installs `core` or `all`
- **THEN** the resolved selection includes the current lifecycle, messaging, and gateway skills without requiring dedicated granular sets

### Requirement: Packaged system-skill catalog includes mailbox-administration guidance and expands `mailbox-full`
**Reason**: The catalog no longer exposes `mailbox-core` or `mailbox-full` as installable set names. The current mailbox skills remain packaged and are included through `core` and `all`.

**Migration**: Use `--skill-set core`, `--skill-set all`, or explicit mailbox skill names.

#### Scenario: Mailbox skills remain available without mailbox sets
- **WHEN** an operator installs `core` or `all`
- **THEN** the resolved selection includes the current mailbox operation and mailbox-administration skills

### Requirement: Packaged system-skill catalog includes explicit LLM Wiki utility guidance
**Reason**: Utility guidance is no longer modeled as an explicit-only `utils` set. `houmao-utils-llm-wiki` remains packaged and is included through `all`.

**Migration**: Use `--skill-set all` or explicit `--skill houmao-utils-llm-wiki`.

#### Scenario: LLM Wiki utility installs through all
- **WHEN** an operator requests the `all` set
- **THEN** the resolved selection includes `houmao-utils-llm-wiki`
- **AND THEN** the removed `utils` set is not required
