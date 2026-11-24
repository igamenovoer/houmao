# Shared Routines Skill Delta

## MODIFIED Requirements

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

### Requirement: Protected invocation designators are entrypoint-qualified
The shared skill SHALL qualify its child designators with `houmao-shared-routines`. Subskill components SHALL use bare names and command components SHALL use parentheses. User-facing examples SHALL start at a public actor entrypoint or use advanced direct invocation of the shared skill.

#### Scenario: Inspect route has two qualified designators
- **WHEN** documentation renders the common inspect routine
- **THEN** it can show both `$houmao-admin-entrypoint agent-inspect` and `$houmao-agent-entrypoint agent-inspect`
- **AND THEN** its internal discovery route is `houmao-shared-routines->houmao-agent-inspect->discover()`

## ADDED Requirements

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
