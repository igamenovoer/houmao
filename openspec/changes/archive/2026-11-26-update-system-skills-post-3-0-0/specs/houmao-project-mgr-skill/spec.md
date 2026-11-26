# Spec Delta

## MODIFIED Requirements

### Requirement: Packaged `houmao-project-mgr` skill explains project-aware side effects and renamed-skill routing boundaries
The `houmao-project-mgr` skill SHALL explain what changes for other Houmao commands when a project overlay exists. At minimum, that project-aware guidance SHALL cover:

- `houmao-mgr project agents launch` (building brain homes internally)
- `houmao-mgr agents self join`
- `houmao-mgr agents global list`
- `houmao-mgr agents single ... state`
- `houmao-mgr mailbox ...`
- `houmao-passive-server serve`
- `houmao-mgr admin cleanup runtime ...`

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

That guidance SHALL explain that those command families resolve project-local defaults such as the active agent-definition tree, runtime root, jobs root, mailbox root, or selected overlay when project context is present.

The skill SHALL use the current packaged skill names when routing neighboring concerns. At minimum, it SHALL hand off:

- specialist and project profile authoring plus easy `launch|stop` to `houmao-agent-definition`
- project-local auth bundle CRUD to `houmao-credential-mgr`
- low-level roles and recipes to `houmao-agent-definition`
- generic managed-agent lifecycle after project-scoped routing to `houmao-agent-instance`
- project or global mailbox administration to `houmao-mailbox-mgr`

#### Scenario: Reader asks what other subcommands do differently inside a project
- **WHEN** a reader uses `houmao-project-mgr` to understand project context effects
- **THEN** the skill explains which other command families become project-aware
- **AND THEN** it explains which project-local roots or defaults those families now resolve from the active overlay

#### Scenario: Reader asks which renamed packaged skill owns a neighboring workflow
- **WHEN** a reader asks `houmao-project-mgr` about specialist CRUD, auth-bundle editing, low-level role or recipe editing, mailbox administration, or generic live-agent lifecycle
- **THEN** the skill routes the request to `houmao-agent-definition`, `houmao-credential-mgr`, `houmao-mailbox-mgr`, or `houmao-agent-instance` as appropriate
- **AND THEN** the skill does not keep obsolete `houmao-manage-*` or `houmao-specialist-mgr` identifiers as the current routing targets

## ADDED Requirements

### Requirement: Project manager covers project skills, project migrate, manual, and system-skills boundaries
`houmao-project-mgr` SHALL cover `houmao-mgr project skills {add|get|list|remove|set}` (`.houmao/content/skills/`) and `houmao-mgr project migrate [--apply]` in `SKILL-MAIN.md` and `references/project-layout.md`, plus clear discovery routing for `houmao-mgr manual` and `houmao-mgr system-skills` boundaries.

#### Scenario: Operator manages project-local skills or migrates an overlay
- **WHEN** an admin asks to register project-local skills or migrate an existing `.houmao/` overlay
- **THEN** `houmao-project-mgr` routes project skill registration to `houmao-mgr project skills ...` and overlay migration to `houmao-mgr project migrate [--apply]`
- **AND THEN** `references/project-layout.md` explains `.houmao/content/skills/` alongside `.houmao/catalog.sqlite`, `.houmao/content/`, and `.houmao/agents/`

### Requirement: Project manager removes orphan redirect and redundant boilerplate
`houmao-project-mgr` SHALL remove the orphaned `commands/launch-profiles.md` file, replace obsolete `houmao-specialist-mgr` routing mentions with `houmao-agent-definition`, strip duplicated launcher, Missing-Input, `houmao-cli`/Pixi, and Scope/Routing prose from `SKILL-MAIN.md`, and keep `SKILL-MAIN.md` concise (~85 lines).

#### Scenario: Orphan command file and cross-skill boilerplate are cleaned up
- **WHEN** a reviewer checks `houmao-project-mgr` against `imsight-agent-skill-handling` and `manifest.toml`
- **THEN** `commands/launch-profiles.md` is removed and all routing references to specialists and profiles point to `houmao-agent-definition`
- **AND THEN** `SKILL-MAIN.md` uses a concise `## Workflow`, `## Subcommands` table, and skill-specific `DO NOT ...` guardrails

### Requirement: Project manager preserves admin gate and non-creating overlay invariants
`houmao-project-mgr` SHALL preserve its admin-only `## Actor Frame Gate`, `project init|status` and `project agents list|get|stop` coverage, non-creating overlay resolution (`would_bootstrap_overlay` on `project status` vs existing-overlay requirement for `project agents`), and handoffs to `agent-definition`, `credential-mgr`, `mailbox-mgr`, and `agent-instance`.

#### Scenario: Non-creating overlay queries avoid unexpected bootstrap
- **WHEN** an admin invokes `houmao-project-mgr->status()` on a workspace without an initialized overlay
- **THEN** `project status` uses non-creating resolution and reports `would_bootstrap_overlay` without creating `.houmao/`
- **AND THEN** requests in `agent` actor posture are rejected at `## Actor Frame Gate`
