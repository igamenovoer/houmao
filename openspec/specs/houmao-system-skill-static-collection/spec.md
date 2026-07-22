# houmao-system-skill-static-collection Specification

## Purpose
TBD - created by archiving change replace-runtime-skill-composition-with-static-collection. Update Purpose after archive.
## Requirements
### Requirement: System skills are distributed as six static standalone roots
Houmao SHALL package exactly these current host-discoverable system-skill roots beneath `src/houmao/agents/assets/system_skills/public/`: `houmao-admin-welcome`, `houmao-admin-entrypoint`, `houmao-agent-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite`.

Each root SHALL contain `SKILL.md` and all locally owned runtime resources. The checked-in directory SHALL be the same instruction tree installed into a tool home, apart from the projection mechanism itself.

#### Scenario: Maintainer inspects the static source collection
- **WHEN** a maintainer enumerates standalone entrypoints beneath the public source root
- **THEN** exactly six `SKILL.md` roots are found
- **AND THEN** each root can be validated without running a composer

### Requirement: Shared routines own sixteen parent-scoped children
`houmao-shared-routines` SHALL own exactly sixteen parent-scoped routine directories beneath `subskills/`, for advanced usage, agent definition, agent email communication, agent gateway, agent inspection, agent instances, agent messaging, credentials, graphing, AG-UI interop, mailbox administration, memory, operator messaging, gateway email rounds, project management, and workspace management.

Each direct child SHALL contain `SKILL-MAIN.md` and SHALL NOT contain a sibling `SKILL.md`. Pro and lite loop skills SHALL NOT appear as shared children.

#### Scenario: Exact entrypoint scanner traverses shared routines
- **WHEN** a recursive scanner registers only exact `SKILL.md` filenames
- **THEN** it registers `houmao-shared-routines` as one standalone skill
- **AND THEN** it does not register any of the sixteen `SKILL-MAIN.md` children independently
- **AND THEN** it does not find nested copies of either loop skill

### Requirement: Runtime installation does not compose skill content
The system SHALL NOT generate Markdown, render source placeholders, select an audience-specific route file, filter child routines, mount one skill below another, or otherwise synthesize a skill directory during installation.

Static staging SHALL copy complete source directories byte for byte or create direct symlinks to complete source directories. Validation MAY inspect staged content but SHALL NOT rewrite it.

#### Scenario: Admin pack is staged in copy mode
- **WHEN** the installer stages the admin pack
- **THEN** each selected destination tree is byte-identical to its corresponding public source directory
- **AND THEN** no local subskill tree is generated beneath `houmao-admin-entrypoint`

#### Scenario: Agent pack is staged in symlink mode
- **WHEN** the installer stages the agent pack using explicit symlink mode
- **THEN** each selected top-level destination links directly to its complete public source directory
- **AND THEN** no materialized composition directory is created

### Requirement: Static roots declare sibling dependencies without pretending to own them
Actor entrypoints SHALL declare `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite` as sibling routes where applicable. They SHALL NOT link to those skills through paths relative to their own directory.

Every local Markdown link in a standalone skill SHALL resolve within that skill. Every cross-skill dependency SHALL use an explicit skill invocation or documented sibling name.

#### Scenario: Admin entrypoint source is validated by itself
- **WHEN** validation checks local files referenced by `houmao-admin-entrypoint/SKILL.md`
- **THEN** every local file exists beneath `houmao-admin-entrypoint`
- **AND THEN** shared and loop delegation appears as sibling skill invocation rather than a nonexistent local `subskills/` path

### Requirement: Static public collection supports Skills CLI discovery
The public source root SHALL be usable as a standard Agent Skills collection. Exact-`SKILL.md` discovery SHALL expose exactly the six standalone skill names, and the repository documentation SHALL provide explicit all, admin, and agent selection examples.

The documentation SHALL NOT claim that Skills CLI resolves Houmao pack dependencies automatically. Explicit admin selection SHALL include five roots, and explicit agent selection SHALL include four roots.

#### Scenario: User lists the public collection with Skills CLI
- **WHEN** a user asks Skills CLI to list or select skills from the public source root
- **THEN** the result contains exactly the six standalone Houmao skill names
- **AND THEN** no shared child logical id is offered as an independent skill

#### Scenario: User installs the admin surface explicitly
- **WHEN** a user follows the documented Skills CLI admin installation
- **THEN** the selection names admin welcome, admin entrypoint, shared routines, pro loop, and lite loop
- **AND THEN** the installed entrypoint has every required sibling available

