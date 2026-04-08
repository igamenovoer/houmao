## Purpose
Define the packaged Houmao-owned `houmao-project-mgr` skill for project overlay lifecycle, project layout explanation, and project-scoped management routing.

## Requirements

### Requirement: Packaged `houmao-project-mgr` skill covers project overlay lifecycle and project-scoped management surfaces
The packaged current Houmao-owned system-skill inventory SHALL include `houmao-project-mgr` as the Houmao-owned project-management skill.

That packaged skill SHALL use `houmao-project-mgr` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `houmao-project-mgr` skill SHALL act as an index/router for these supported project command families:

- `houmao-mgr project init`
- `houmao-mgr project status`
- `houmao-mgr project agents launch-profiles list|get|add|set|remove`
- `houmao-mgr project easy instance list|get|stop`

The packaged skill SHALL treat `project agents launch-profiles ...` as the explicit reusable recipe-backed birth-time profile surface and SHALL treat `project easy instance list|get|stop` as the selected-project overlay inspection and stop surface for already-launched easy instances.

#### Scenario: Agent needs project overlay lifecycle guidance
- **WHEN** an agent is asked to create or inspect the active Houmao project overlay
- **THEN** `houmao-project-mgr` routes that task through `houmao-mgr project init` or `houmao-mgr project status`
- **AND THEN** the skill treats those commands as the canonical project-overlay lifecycle entrypoints

#### Scenario: Agent needs project-local launch-profile or easy-instance inspection guidance
- **WHEN** an agent is asked to manage explicit project launch profiles or inspect or stop one easy instance through the selected project overlay
- **THEN** `houmao-project-mgr` routes that task through `project agents launch-profiles ...` or `project easy instance list|get|stop`
- **AND THEN** the skill does not redirect those tasks to unrelated generic lifecycle or mailbox command families

### Requirement: Packaged `houmao-project-mgr` skill explains overlay resolution, `.houmao` layout, and bootstrap semantics
The `houmao-project-mgr` skill SHALL document the current project-overlay resolution inputs and precedence, including:

- `HOUMAO_PROJECT_OVERLAY_DIR`
- `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`
- `HOUMAO_AGENT_DEF_DIR`
- ambient `ancestor` versus `cwd_only` discovery behavior

The skill SHALL explain the managed `.houmao/` layout and SHALL distinguish the canonical semantic store from the compatibility projection. At minimum, that layout guidance SHALL cover:

- `houmao-config.toml`
- `catalog.sqlite`
- `content/`
- `agents/` as the compatibility projection materialized from the catalog and managed content
- `runtime/`
- `jobs/`
- `mailbox/`
- `easy/`

The skill SHALL explain the current bootstrap distinction between creating and non-creating flows:

- `project status` uses non-creating resolution and reports `would_bootstrap_overlay` when the selected overlay does not exist yet
- stateful project-aware flows that ensure local roots may bootstrap the selected overlay
- `project easy instance list|get|stop` use non-creating selected-overlay resolution and SHALL be described as requiring an already-existing overlay

#### Scenario: Reader checks how overlay selection works
- **WHEN** a reader opens the overlay-resolution material referenced by `houmao-project-mgr`
- **THEN** they see the precedence and semantics for `HOUMAO_PROJECT_OVERLAY_DIR`, `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`, and `HOUMAO_AGENT_DEF_DIR`
- **AND THEN** they see the distinction between `ancestor` and `cwd_only` ambient discovery

#### Scenario: Reader checks project layout and bootstrap behavior
- **WHEN** a reader opens the layout or lifecycle material referenced by `houmao-project-mgr`
- **THEN** they see `.houmao/catalog.sqlite` and `.houmao/content/` described as the canonical semantic store and managed payload roots
- **AND THEN** they see `.houmao/agents/` described as the compatibility projection rather than the sole canonical source
- **AND THEN** they see that `project status` reports bootstrap intent while `project easy instance list|get|stop` require an existing selected overlay

### Requirement: Packaged `houmao-project-mgr` skill explains project-aware side effects and renamed-skill routing boundaries
The `houmao-project-mgr` skill SHALL explain what changes for other Houmao commands when a project overlay exists. At minimum, that project-aware guidance SHALL cover:

- `houmao-mgr brains build`
- `houmao-mgr agents launch`
- `houmao-mgr agents join`
- `houmao-mgr agents list`
- `houmao-mgr agents state`
- `houmao-mgr mailbox ...`
- `houmao-mgr server start`
- `houmao-mgr admin cleanup runtime ...`

That guidance SHALL explain that those command families resolve project-local defaults such as the active agent-definition tree, runtime root, jobs root, mailbox root, or selected overlay when project context is present.

The skill SHALL use the current renamed packaged skill names when routing neighboring concerns. At minimum, it SHALL hand off:

- easy specialist and easy profile authoring plus easy `launch|stop` to `houmao-specialist-mgr`
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
- **THEN** the skill routes the request to `houmao-specialist-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, `houmao-mailbox-mgr`, or `houmao-agent-instance` as appropriate
- **AND THEN** the skill does not keep obsolete `houmao-manage-*` identifiers as the current routing targets
