# houmao-shared-routines-skill Specification

## Purpose
TBD - created by archiving change refactor-system-skills-by-actor. Update Purpose after archive.
## Requirements
### Requirement: Houmao packages one canonical protected routine bundle
Houmao SHALL package one protected bundle with logical id `houmao-shared-routines` as the canonical owner of reusable system-skill commands, references, audience routers, and maintained nested routine skills.

The bundle SHALL NOT be independently installable or publicly discoverable as a top-level Houmao system skill.

#### Scenario: Maintainer updates a shared routine
- **WHEN** a maintainer changes a routine eligible for both audiences
- **THEN** the canonical source changes in one protected bundle
- **AND THEN** both audience compositions derive from that source during installation

### Requirement: Protected bundle declares an explicit audience matrix
The admin route SHALL include `houmao-project-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, and `houmao-operator-messaging`; the agent route SHALL omit those admin-only routines.

The agent route SHALL include `houmao-process-emails-via-gateway`; the admin route SHALL omit that notifier-round-only routine.

Both routes SHALL include `houmao-agent-email-comms`, `houmao-adv-usage-pattern`, `houmao-utils-workspace-mgr`, `houmao-ext-graphing`, `houmao-mailbox-mgr`, `houmao-memory-mgr`, `houmao-agent-loop-pro`, `houmao-agent-loop-lite`, `houmao-agent-instance`, `houmao-agent-inspect`, `houmao-agent-messaging`, `houmao-agent-gateway`, and `houmao-interop-ag-ui`.

#### Scenario: Composer resolves both audience closures
- **WHEN** the manifest validator computes admin and agent routine closures
- **THEN** each closure contains every common routine
- **AND THEN** each closure contains only its eligible actor-specific routines

### Requirement: Shared routine layout distinguishes commands, references, and true subskills
The protected parent `SKILL.md` installed for each audience SHALL remain a lean router.

Parent-owned executable procedures SHALL live under `commands/`; supporting facts, examples, schemas, and policy SHALL live under `references/`; and each direct subskill SHALL live under `subskills/<name>/` with its own `SKILL.md` and privately owned resources.

Each parent router SHALL list every direct subskill with a “When to Route Here” summary. Existing procedure-only `actions/*.md` or `subskills/*.md` pages SHALL be reclassified according to resource ownership.

#### Scenario: Procedure page owns no independent resources
- **WHEN** a migrated page describes one operation over resources owned by its parent
- **THEN** the refactor places it under `commands/` rather than creating a nominal subskill
- **AND THEN** the parent router lists the command in its command map

#### Scenario: Nested capability owns private resources
- **WHEN** a migrated capability has its own workflow, commands, references, and routing boundary
- **THEN** it becomes a nested subskill with its own `SKILL.md`
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
The manifest SHALL derive an invocation designator for each eligible entrypoint rather than assigning one global public name to a protected routine.

Skill and subskill segments SHALL use bare arrow notation, while command segments SHALL use parentheses. User-facing examples SHALL start from `$houmao-admin-entrypoint` or `$houmao-agent-entrypoint` and SHALL NOT present a protected logical id as a top-level invocation.

#### Scenario: Inspect route has two qualified designators
- **WHEN** documentation renders the common inspect routine
- **THEN** it can show `houmao-admin-entrypoint->houmao-shared-routines->agent-inspect` and `houmao-agent-entrypoint->houmao-shared-routines->agent-inspect`
- **AND THEN** an inspect command is rendered with a final command segment such as `status()`

### Requirement: Removed public skills have direct protected replacements or retirement routes
The refactor SHALL preserve the maintained behavior of each current non-retired routine under its protected logical id and actor-eligible route.

`houmao-touring` SHALL be replaced by `houmao-admin-welcome`. `houmao-specialist-mgr` SHALL be removed, and its maintained specialist and profile behavior SHALL remain under `houmao-agent-definition`. No public compatibility directory SHALL be generated for either removed name.

#### Scenario: Old direct invocation is diagnosed
- **WHEN** migration guidance encounters a saved prompt that invokes a former flat routine directly
- **THEN** it provides the matching public entrypoint route when one exists
- **AND THEN** it does not reinstall the old public wrapper

