# houmao-parent-scoped-skill-entrypoints Specification

## Purpose
TBD - created by archiving change adopt-protected-skill-main-entrypoints. Update Purpose after archive.
## Requirements
### Requirement: System-skill entrypoint filenames reflect discovery scope
Houmao SHALL package every standalone or host-discoverable public system-skill root with `SKILL.md` and every protected parent-scoped router or routine below `subskills/<name>/` with `SKILL-MAIN.md`.

A parent-scoped directory SHALL NOT contain `SKILL.md`, and no directory SHALL contain both `SKILL.md` and `SKILL-MAIN.md`. Houmao SHALL NOT create compatibility copies for the obsolete nested filename.

#### Scenario: Agent pack is composed for a managed home
- **WHEN** Houmao composes the managed-agent system-skill pack
- **THEN** `houmao-agent-entrypoint/SKILL.md` exists as the public root
- **AND THEN** `houmao-agent-entrypoint/subskills/houmao-shared-routines/SKILL-MAIN.md` exists
- **AND THEN** each included protected routine owns `SKILL-MAIN.md` and no nested protected directory owns `SKILL.md`

#### Scenario: Admin welcome is composed
- **WHEN** Houmao composes the admin system-skill pack
- **THEN** `houmao-admin-welcome/SKILL.md` remains a standalone public entrypoint
- **AND THEN** the welcome directory contains no protected subskill mount

### Requirement: Parents explicitly and selectively load protected children
Each executable public entrypoint SHALL establish its actor frame before explicitly loading `subskills/houmao-shared-routines/SKILL-MAIN.md`.

Each protected audience router SHALL list every eligible direct routine with its exact child `SKILL-MAIN.md` load path and a distinguishing `When to Route Here` sentence. After route selection, the router SHALL load only the selected child's entrypoint and resources needed for the selected operation.

#### Scenario: Agent enters the mailbox routine
- **WHEN** a verified managed agent invokes `$houmao-agent-entrypoint agent-email-comms list`
- **THEN** the public entrypoint establishes the agent actor frame and loads the protected router's `SKILL-MAIN.md`
- **AND THEN** the router loads only the selected `houmao-agent-email-comms/SKILL-MAIN.md` entrypoint and required local resources

#### Scenario: Protected child is encountered without its parent
- **WHEN** a protected routine is read without a valid actor-qualified frame from its public parent
- **THEN** the routine refuses standalone execution and directs the caller through the eligible public entrypoint

### Requirement: Composition validation rejects discovery-unsafe layouts
Houmao SHALL validate public and parent-scoped roots with role-specific filenames before target mutation. It SHALL reject a missing role-canonical entrypoint, a nested `SKILL.md`, both entrypoint candidates in one directory, files placed directly under `subskills/`, unresolved actor placeholders, and protected routes lacking actor-frame gates or route summaries.

For each composed public system skill, recursive exact-`SKILL.md` discovery SHALL return only that public root's entrypoint.

#### Scenario: Protected routine retains legacy nested filename
- **WHEN** a protected source or composed routine owns `SKILL.md` instead of `SKILL-MAIN.md`
- **THEN** manifest or composition validation fails before installation changes the target home

#### Scenario: Composed entrypoint passes scanner-safety validation
- **WHEN** a valid actor pack is staged
- **THEN** the only exact `SKILL.md` below each public skill directory is the public root entrypoint
- **AND THEN** every direct nested capability has exactly one `SKILL-MAIN.md`

### Requirement: Object-style designators declare their notation
Every packaged Markdown instruction page that uses object-style skill, subskill, or subcommand designators SHALL declare `skill_invocation_notation` in YAML frontmatter using the maintained standard value.

The notation SHALL define top-level `SKILL.md`, explicitly parent-loaded `SKILL-MAIN.md`, bare skill and subskill path components, parenthesized command components, and invalid skill-entrypoint parentheses.

#### Scenario: Protected instruction page contains an arrow designator
- **WHEN** validation reads a packaged instruction page containing a designator such as `houmao-agent-entrypoint->houmao-shared-routines->agent-inspect`
- **THEN** the page contains the standard `skill_invocation_notation` declaration

#### Scenario: Instruction page omits required notation metadata
- **WHEN** a packaged instruction page uses object-style designators without the standard declaration
- **THEN** validation fails before the pack is installed

### Requirement: Generated prompts invoke only public skill entrypoints
Automatically generated mailbox-operation and mail-notifier prompts SHALL invoke the eligible public entrypoint through the current tool's native skill syntax. They SHALL describe protected routines as parent-controlled routes and SHALL NOT instruct the agent to discover, open, or invoke a protected entrypoint independently.

Internal object-style route traces MAY appear for diagnostics, but SHALL NOT replace the public `$houmao-agent-entrypoint <route> ...`, `/houmao-agent-entrypoint <route> ...`, or equivalent plain invocation.

#### Scenario: Codex receives a notifier prompt
- **WHEN** the managed agent pack is installed and the gateway generates a Codex mail-notifier prompt
- **THEN** the prompt invokes `$houmao-agent-entrypoint process-emails-via-gateway <gateway-url>`
- **AND THEN** the prompt states that the public entrypoint controls protected traversal
- **AND THEN** the prompt does not present a protected file or logical id as a standalone native skill trigger

#### Scenario: Agent pack is unavailable
- **WHEN** the gateway cannot find the public managed-agent entrypoint
- **THEN** the generated prompt uses the supported mailbox API fallback
- **AND THEN** it does not claim that protected mailbox routines are installed

### Requirement: Old protected compositions are safely upgradeable
The system-skill manifest schema SHALL identify the parent-scoped entrypoint contract. Pack status SHALL compare the installed receipt's manifest schema version with the current manifest version and classify receipt-owned packs from an older contract as drifted.

Pack upgrade SHALL replace the complete receipt-owned public projection transactionally and SHALL preserve unowned paths and existing collision safeguards.

#### Scenario: Version-two receipt owns an otherwise unchanged agent pack
- **WHEN** the current manifest uses the parent-scoped entrypoint schema and the installed receipt records `houmao-system-skills.v2`
- **THEN** system-skill status reports the receipt-owned agent pack as drifted

#### Scenario: Operator upgrades an old receipt-owned pack
- **WHEN** the operator runs the supported upgrade workflow for the drifted pack
- **THEN** Houmao replaces the old nested-`SKILL.md` composition with the canonical `SKILL-MAIN.md` composition atomically
- **AND THEN** the new receipt records the current manifest schema version

### Requirement: Unrelated top-level skill contracts remain unchanged
Houmao SHALL retain `SKILL.md` for public system skills, the managed auto system-prompt skill, project and private skills, generated top-level skills, and read-only legacy migration assets.

The protected-entrypoint migration SHALL apply only to parent-scoped system-skill routers and routines.

#### Scenario: Project skill is validated after the migration
- **WHEN** a project or private skill is selected for a managed agent
- **THEN** its source directory continues to require a top-level `SKILL.md`
- **AND THEN** it is not rewritten to `SKILL-MAIN.md`

