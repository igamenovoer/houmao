# houmao-admin-welcome-skill Specification

## Purpose
Help human operators explore Houmao and choose a workflow through read-only guidance. Hand off executable requests to the admin entrypoint with the selected target and confirmed inputs.
## Requirements
### Requirement: Houmao provides a public admin welcome skill
Houmao SHALL provide a public skill named `houmao-admin-welcome` as the welcome-role member of the admin pack.

The welcome SHALL be installed and managed atomically with `houmao-admin-entrypoint`, but SHALL remain a standalone sibling rather than a subskill of the entrypoint.

#### Scenario: Admin pack exposes the welcome sibling
- **WHEN** an operator installs the admin pack
- **THEN** the tool-native skill root contains both `houmao-admin-welcome` and `houmao-admin-entrypoint`
- **AND THEN** removing or upgrading the pack manages both public siblings together

### Requirement: Admin welcome is self-contained and read-only
The welcome SHALL own its teaching text, concepts, examples, and route map within its public asset directory.

It MAY perform narrowly scoped read-only inspection to orient the user, but SHALL NOT mutate files, credentials, mailboxes, gateways, agent lifecycle, or runtime state. It SHALL NOT contain or mount `houmao-shared-routines` or instruct the user to invoke a protected routine directly.

#### Scenario: First-time user requests orientation
- **WHEN** a user asks what Houmao can do or how to begin
- **THEN** the welcome may inspect supported read-only posture and explain available paths
- **AND THEN** it performs no operational mutation

### Requirement: Admin welcome exposes a compact guided command surface
The welcome SHALL expose `help`, `show-options`, `choose-path`, `show-command-map`, `next-step`, and `start-guided-tour` as read-only commands.

Its curated paths SHALL include Single Agent Full Run, Operator-Controlled Agent Team, Pro Agent Loop, Subsystem Exploration, and Existing Project Reorientation. Each path SHALL explain the goal, required prerequisites, optional choices, and the public admin-entrypoint handoff.

#### Scenario: User asks for guided path options
- **WHEN** the user invokes `show-options` or `choose-path`
- **THEN** the welcome presents the curated paths with concrete outcomes
- **AND THEN** it does not load every protected routine or execute the selected path

### Requirement: Welcome hands executable work to the admin entrypoint with context
When the user asks to perform a selected path, the welcome SHALL produce or invoke an exact `$houmao-admin-entrypoint ...` route and SHALL preserve the chosen path, explicit targets, constraints, and confirmed required or optional inputs.

The welcome SHALL NOT restate or execute the protected routine's command sequence.

#### Scenario: User chooses Single Agent Full Run and asks to proceed
- **WHEN** the welcome has collected the project and agent choices needed for that path
- **THEN** it hands those choices to `houmao-admin-entrypoint` in one context-preserving route
- **AND THEN** the entrypoint, not the welcome, owns execution

### Requirement: Implicit welcome activation is limited to orientation intent
The welcome MAY activate implicitly for first-use orientation, capability comparison, discovery, guided choice, and how-to intent.

It SHALL NOT intercept a concrete operational request that already identifies an executable Houmao action and sufficient target context; that request SHALL route to `houmao-admin-entrypoint`.

#### Scenario: Concrete stop request bypasses welcome
- **WHEN** a human asks to stop one explicitly identified managed agent
- **THEN** the request routes to the admin entrypoint
- **AND THEN** the welcome does not replace the request with a guided tour

### Requirement: Admin welcome skill covers post-3.0.0 runtime concepts and tool surfaces
`houmao-admin-welcome` (`references/concepts.md` and `references/guided-paths.md`) SHALL cover DeepSeek Harness (`dsh`) adapter checks, run modes (`headless`, `service`, `tui`, `web`), `--executor` contexts, `houmao-mgr manual`, gateway dashboard and open-roster access, durable usage records, `houmao-cccc`, `project skills`, and `agents external`.

#### Scenario: Guided tour checks include DSH and post-3.0.0 concepts
- **WHEN** an operator runs onboarding or subsystem exploration through `houmao-admin-welcome`
- **THEN** `references/guided-paths.md` includes `dsh` alongside `claude`, `codex`, and `kimi`, plus gateway access policy, versioned files, external agents, and system-skill packs
- **AND THEN** `references/concepts.md` accurately introduces `dsh`, `service`/`web` modes, `--executor`, `houmao-mgr manual`, open-roster dashboard, usage records, and `houmao-cccc`

### Requirement: Admin welcome skill tightens reference overlap for concise guidance
`houmao-admin-welcome` SHALL remove duplicated presentation and handoff prose between `SKILL.md` and `references/orientation.md` / `references/admin-handoff.md` and tighten `references/question-style.md` and `references/guided-paths.md` using compact comparison tables per `imsight-agent-skill-handling`.

#### Scenario: Entrypoint and references stay non-redundant
- **WHEN** a reviewer inspects `houmao-admin-welcome` against `imsight-agent-skill-handling`
- **THEN** `SKILL.md` keeps concise numbered `## Workflow` steps, native-planning fallback, `## Subcommands` table, and `DO NOT ...` guardrails without duplicating reference prose

### Requirement: Admin welcome skill preserves explicit activation and read-only onboarding invariants
`houmao-admin-welcome` SHALL preserve explicit-only activation (`allow_implicit_invocation: false`), its strictly read-only boundary, the exact three blank-workspace choices, state-aware reorientation without restarting from `init`, and context-preserving handoff to `$houmao-admin-entrypoint`.

#### Scenario: Blank workspace onboarding preserves three read-only choices
- **WHEN** an operator invokes `houmao-admin-welcome` in a blank workspace
- **THEN** it presents only `Create Houmao Project`, `Subsystem Exploration`, and `Inspect` without mutating files, credentials, or agents
- **AND THEN** it recommends `$houmao-admin-entrypoint` rather than invoking execution siblings directly
