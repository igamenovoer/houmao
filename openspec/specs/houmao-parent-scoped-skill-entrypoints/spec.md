# houmao-parent-scoped-skill-entrypoints Specification

## Purpose
Public roots and protected children use distinct entrypoint filenames so hosts discover only public skills. Parents explicitly load eligible children, and validation enforces the discovery rules for packaged layouts and generated prompts.
## Requirements
### Requirement: System-skill entrypoint filenames reflect discovery scope
Each standalone public system skill SHALL use `SKILL.md`. Each shared child under `houmao-shared-routines/subskills/<name>/` SHALL use `SKILL-MAIN.md`. Every runtime directory SHALL contain at most one role-canonical entrypoint. Nested `SKILL.md` compatibility copies SHALL be rejected.

#### Scenario: Agent pack is composed for a managed home
- **WHEN** Houmao stages the managed-agent system-skill pack
- **THEN** `houmao-agent-entrypoint/SKILL.md` and `houmao-shared-routines/SKILL.md` exist as sibling public entrypoints
- **AND THEN** each shared child owns `SKILL-MAIN.md` beneath the shared root

#### Scenario: Admin welcome is composed
- **WHEN** Houmao stages the admin system-skill pack
- **THEN** `houmao-admin-welcome/SKILL.md` remains a standalone public entrypoint
- **AND THEN** all parent-scoped shared children remain under the shared sibling

### Requirement: Parents explicitly and selectively load protected children
Each actor entrypoint SHALL establish its actor frame before delegating a shared route to the public `houmao-shared-routines` sibling. The shared router SHALL list each child entrypoint path and a distinguishing “When to Route Here” sentence. It SHALL select an eligible child and load only that child's `SKILL-MAIN.md` and the resources needed for the operation.

#### Scenario: Agent enters the mailbox routine
- **WHEN** a verified managed agent invokes `$houmao-agent-entrypoint agent-email-comms list`
- **THEN** the actor entrypoint passes the verified agent frame to the shared sibling
- **AND THEN** the shared sibling loads only `subskills/houmao-agent-email-comms/SKILL-MAIN.md` and required child resources

#### Scenario: Protected child is encountered without its parent
- **WHEN** an instruction loads a shared child without a valid actor-qualified frame from the shared root
- **THEN** the child directs the caller through an eligible public route and refuses standalone execution

### Requirement: Composition validation rejects discovery-unsafe layouts
Before target mutation, static source validation SHALL enforce role-canonical filenames and reject nested `SKILL.md`, ambiguous entrypoints, files placed directly in `subskills/`, unresolved actor placeholders, and shared routes missing actor gates or route summaries.

#### Scenario: Protected routine retains legacy nested filename
- **WHEN** a packaged shared routine owns `SKILL.md` in place of `SKILL-MAIN.md`
- **THEN** source validation fails before the installer changes the target home

#### Scenario: Composed entrypoint passes scanner-safety validation
- **WHEN** a valid static actor pack is staged
- **THEN** the only exact `SKILL.md` below each public directory is that directory's public entrypoint
- **AND THEN** every direct child has exactly one `SKILL-MAIN.md`

### Requirement: Object-style designators declare their notation
Every current standalone and parent-scoped entrypoint SHALL declare the maintained standard value at `metadata.skill_invocation_notation` in YAML frontmatter. Every other active instruction page using object-style designators SHALL declare it at the same location.

#### Scenario: Protected instruction page contains an arrow designator
- **WHEN** validation reads an instruction page containing `houmao-shared-routines->houmao-agent-inspect->discover()`
- **THEN** the page declares the standard nested notation
- **AND THEN** the declaration defines standalone and parent-scoped filenames, bare skill and subskill paths, and parenthesized command components

#### Scenario: Instruction page omits required notation metadata
- **WHEN** a current entrypoint or designator-bearing instruction page omits the nested key or uses the former top-level location
- **THEN** source validation fails before the pack is installed

### Requirement: Generated prompts invoke only public skill entrypoints
Automatically generated mailbox-operation and mail-notifier prompts SHALL invoke the eligible public entrypoint through the current tool's native skill syntax. They SHALL describe protected routines as parent-controlled routes and SHALL NOT instruct the agent to discover, open, or invoke a protected entrypoint independently.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

### Requirement: Unrelated top-level skill contracts remain unchanged
Houmao SHALL retain `SKILL.md` for public system skills, the managed auto system-prompt skill, project and private skills, generated top-level skills, and read-only legacy migration assets.

The protected-entrypoint migration SHALL apply only to parent-scoped system-skill routers and routines.

#### Scenario: Project skill is validated after the migration
- **WHEN** a project or private skill is selected for a managed agent
- **THEN** its source directory continues to require a top-level `SKILL.md`
- **AND THEN** it is not rewritten to `SKILL-MAIN.md`

