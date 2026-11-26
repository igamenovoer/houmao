# houmao-shared-routines-skill Specification

## Purpose
House reusable Houmao commands, reference material, and subskills in one bundle. Route them by actor posture so administrators and managed agents receive the operations and targets available to them.
## Requirements
### Requirement: Houmao packages one canonical protected routine bundle
Houmao SHALL package `houmao-shared-routines` as the standalone owner of reusable system-skill commands, references, and parent-scoped children. Both actor packs SHALL project the same static shared skill beside their actor entrypoints.

#### Scenario: Maintainer updates a shared routine
- **WHEN** a maintainer changes a routine eligible for both audiences
- **THEN** the canonical source changes under one shared root
- **AND THEN** both actor packs install that same complete source tree

### Requirement: Protected bundle declares an explicit audience matrix
The manifest SHALL declare the eligible actors for each shared child. The admin route SHALL include `houmao-project-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, and `houmao-operator-messaging` as admin-only children. The agent route SHALL include `houmao-process-emails-via-gateway` as an agent-only child.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Both actor routes SHALL include `houmao-agent-access`, `houmao-agent-files`, `houmao-agent-email-comms`, `houmao-adv-usage-pattern`, `houmao-utils-workspace-mgr`, `houmao-ext-graphing`, `houmao-mailbox-mgr`, `houmao-memory-mgr`, `houmao-agent-instance`, `houmao-agent-inspect`, `houmao-agent-messaging`, `houmao-agent-gateway`, and `houmao-interop-ag-ui`. Both actor routes SHALL delegate Pro and Lite workflows to their respective standalone siblings.

#### Scenario: Composer resolves both audience closures
- **WHEN** the manifest validator computes eligible admin and agent routine routes
- **THEN** each route set contains every common routine and its eligible actor-specific routines
- **AND THEN** the route set controls selection within the same complete installed tree

### Requirement: Shared routine layout distinguishes commands, references, and true subskills
The public shared `SKILL.md` SHALL route requests to owned commands and children. Executable procedures SHALL live under their owner's `commands/`, and supporting material under `references/`. Each direct child SHALL own `subskills/<name>/SKILL-MAIN.md` and its bundled resources.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The parent router SHALL list every direct child with a distinguishing “When to Route Here” sentence and its entrypoint path. The owner of a procedure-only page SHALL place it with commands or references according to its role.

#### Scenario: Procedure page owns no independent resources
- **WHEN** a page describes one executable operation over resources owned by its parent
- **THEN** the owner places it under `commands/`
- **AND THEN** the owner lists the command in its command map

#### Scenario: Nested capability owns private resources
- **WHEN** a capability owns commands, references, and a routing boundary
- **THEN** its entrypoint is a parent-scoped `SKILL-MAIN.md`
- **AND THEN** its parent provides a route summary

### Requirement: Common routines branch on the supplied actor frame
Every routine eligible for both audiences SHALL define the actor-sensitive target or command differences that apply to admin and agent callers, or SHALL explicitly state that its behavior is actor-invariant after validation.

The admin branch SHALL use explicit target scopes. The agent branch SHALL use verified self scope by default and SHALL require explicit targets for supported peer operations.

#### Scenario: Shared memory routine receives different actors
- **WHEN** the admin route opens the memory routine for another managed agent
- **THEN** it uses the explicit selected-agent path
- **AND WHEN** the agent route opens the same logical routine for itself
- **THEN** it uses the verified self path without changing actor kind

### Requirement: Protected invocation designators are entrypoint-qualified
The shared skill SHALL qualify its child designators with `houmao-shared-routines`. Subskill components SHALL use bare names and command components SHALL use parentheses. User-facing examples SHALL start at a public actor entrypoint or use advanced direct invocation of the shared skill.

#### Scenario: Inspect route has two qualified designators
- **WHEN** documentation renders the common inspect routine
- **THEN** it can show both `$houmao-admin-entrypoint agent-inspect` and `$houmao-agent-entrypoint agent-inspect`
- **AND THEN** its internal discovery route is `houmao-shared-routines->houmao-agent-inspect->discover()`

### Requirement: Removed public skills have direct protected replacements or retirement routes
The refactor SHALL preserve the maintained behavior of each current non-retired routine under its protected logical id and actor-eligible route.

`houmao-touring` SHALL be replaced by `houmao-admin-welcome`. `houmao-specialist-mgr` SHALL be removed, and its maintained specialist and profile behavior SHALL remain under `houmao-agent-definition`. No public compatibility directory SHALL be generated for either removed name.

#### Scenario: Old direct invocation is diagnosed
- **WHEN** migration guidance encounters a saved prompt that invokes a former flat routine directly
- **THEN** it provides the matching public entrypoint route when one exists
- **AND THEN** it does not reinstall the old public wrapper

### Requirement: Shared routines exposes one Agent Definition route
The public shared-routines skill SHALL list authoring and deployment as subcommands of the existing `houmao-agent-definition` child.

#### Scenario: Advanced admin invokes authoring directly
- **WHEN** an admin explicitly invokes `houmao-shared-routines->houmao-agent-definition`
- **THEN** the skill SHALL expose the maintained authoring and deployment command family

### Requirement: Agent posture cannot administer definitions
The `as-agent` qualifier SHALL reject Agent Definition authoring, materialization, deployment, update, and removal after identity verification.

#### Scenario: Managed agent requests deployment
- **WHEN** the shared routine resolves managed-agent actor posture
- **THEN** it SHALL reject the definition administration route

### Requirement: Shared routines exposes actor-scoped instance state
The public shared-routines skill SHALL expose runtime-variable and mindset operations through the existing `houmao-agent-instance` child.

#### Scenario: Admin invokes state mutation
- **WHEN** actor posture is admin and one target is explicit
- **THEN** the child SHALL expose inspection and mutation commands

#### Scenario: Managed agent invokes state access
- **WHEN** the `as-agent` qualifier verifies a current managed runtime
- **THEN** the child SHALL expose self read and snapshot commands only

### Requirement: Shared routines exposes actor-scoped private workspace operations
The public shared-routines skill SHALL expose private workspace operations through the existing `houmao-agent-instance` child.

#### Scenario: Admin invokes workspace management
- **WHEN** actor posture is admin and one target is explicit
- **THEN** the child SHALL expose inspection and maintained mutation commands

#### Scenario: Managed agent invokes workspace access
- **WHEN** `as-agent` verifies the current runtime
- **THEN** the child SHALL expose semantic path reads only

### Requirement: Custom private workspaces do not route to the team workspace manager
Routing SHALL keep instance-owned private workspace contracts separate from standard multi-agent workspace topology.

#### Scenario: Agent definition declares semantic directories
- **WHEN** the directories belong to one managed-agent instance
- **THEN** shared routines SHALL use `houmao-agent-instance`, not `houmao-utils-workspace-mgr`

### Requirement: Shared routines exposes plural deployment under admin posture
The public shared-routines skill SHALL expose batch deployment as a subcommand of `houmao-agent-definition` and SHALL reject it under `as-agent`.

#### Scenario: Advanced admin invokes batch deployment
- **WHEN** actor posture is admin
- **THEN** the route SHALL expose Batch Request, plan, and apply guidance

#### Scenario: Managed agent invokes batch deployment
- **WHEN** actor posture is managed agent
- **THEN** the route SHALL reject the operation

### Requirement: Published skill commands agree with their catalog
Each published command SHALL use the same canonical name in its owner route table, help, and manifest. A supported alias SHALL map to its canonical operation. The route table SHALL link the executable command page when one exists.

#### Scenario: Catalog reports the maintained command inventory
- **WHEN** an operator lists system skills
- **THEN** the catalog includes definition authoring, deployment, and batch commands under `agent-definition`
- **AND THEN** it includes runtime variables, mindsets, and private workspaces under `agent-instance`
- **AND THEN** the messaging catalog reports `mail` with `mail-handoff` as an alias

#### Scenario: Operator selects a project profile workflow
- **WHEN** an operator asks how to save a project launch profile
- **THEN** the skill routes to the owning profile workflow
- **AND THEN** a compatibility note does not appear as a second executable command
### Requirement: Shared routines help reports exact eighteen-child count and post-3.0.0 routes
`houmao-shared-routines/commands/help.md` SHALL replace the stale `"sixteen"` count with `"eighteen"` (`18`) parent-scoped children, and `SKILL.md` `When to Route Here` descriptions SHALL distinguish `request` vs `prompt`, `houmao-cccc`, `open-browser`, `mailbox online`, and usage inspection.

#### Scenario: Collection-wide help matches manifest eighteen-child inventory
- **WHEN** a caller runs `houmao-shared-routines->help()` for collection-wide help
- **THEN** `commands/help.md` states eighteen (`18`) parent-scoped children matching `manifest.toml` and the `SKILL.md` route table
- **AND THEN** route descriptions in `SKILL.md` reflect post-3.0.0 capabilities without copying child descriptions verbatim

### Requirement: Shared routines deduplicates actor-frame prose across entrypoint and reference
`houmao-shared-routines` SHALL remove duplicated actor-selection explanation between `SKILL.md` `## Actor Selection` and `references/actor-frame.md` so each detail lives in one authoritative place per `imsight-agent-skill-handling`.

#### Scenario: Actor frame definition lives in one canonical place
- **WHEN** a reviewer inspects `houmao-shared-routines/SKILL.md` and `references/actor-frame.md`
- **THEN** `SKILL.md` states concise actor-selection steps and links `references/actor-frame.md` for the six-field frame contract without repeating the full block

### Requirement: Shared routines preserves explicit activation, frame validation, and selective child loading
`houmao-shared-routines` SHALL preserve explicit-only activation, help before actor verification or child loading, immutable inherited six-field frame validation, `as-agent` fresh `agents self identity`, selective single-child `SKILL-MAIN.md` loading, and the `specialist-mgr` alias.

#### Scenario: Selective child loading never scans sibling directories
- **WHEN** `houmao-shared-routines` resolves a valid route for the verified actor frame
- **THEN** it loads only the selected `subskills/<logical-id>/SKILL-MAIN.md` and its internal resources
- **AND THEN** it keeps `| <route> |` and `"When to Route Here"` compliant with `system_skill_manifest.py`
