## ADDED Requirements

### Requirement: Houmao provides a packaged `houmao-manage-agent-definition` system skill

The system SHALL package a Houmao-owned system skill named `houmao-manage-agent-definition` under the maintained system-skill asset root.

That skill SHALL instruct agents to manage low-level project-local agent definitions through these supported current commands:

- `houmao-mgr project agents roles list`
- `houmao-mgr project agents roles get`
- `houmao-mgr project agents roles init`
- `houmao-mgr project agents roles set`
- `houmao-mgr project agents roles remove`
- `houmao-mgr project agents presets list`
- `houmao-mgr project agents presets get`
- `houmao-mgr project agents presets add`
- `houmao-mgr project agents presets set`
- `houmao-mgr project agents presets remove`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `create`
- `list`
- `get`
- `set`
- `remove`

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `project easy specialist ...`
- `project easy instance ...`
- `agents launch|join|list|stop|cleanup`
- `project agents tools <tool> auth list|get|add|set|remove` when the user is asking to mutate auth-bundle contents rather than which bundle a preset references
- direct hand-editing under `.houmao/agents/roles/` or `.houmao/agents/presets/`

The packaged skill SHALL NOT instruct agents to use retired or unsupported low-level shapes such as:

- `houmao-mgr project agents roles scaffold`
- `houmao-mgr project agents roles presets ...`

#### Scenario: Installed skill points the agent at the current low-level role and preset commands

- **WHEN** an agent opens the installed `houmao-manage-agent-definition` skill
- **THEN** the skill directs the agent to use the supported `project agents roles ...` and `project agents presets ...` command surfaces for low-level definition work
- **AND THEN** it does not redirect the agent to ad hoc filesystem editing, stale command trees, or unrelated runtime-control surfaces

#### Scenario: Installed skill routes to action-specific local guidance

- **WHEN** an agent reads the installed `houmao-manage-agent-definition` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `create`, `list`, `get`, `set`, and `remove`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than one flattened entry page

#### Scenario: Installed skill keeps easy, runtime, and auth-content workflows out of scope

- **WHEN** an agent reads the installed `houmao-manage-agent-definition` skill
- **THEN** the skill marks easy-specialist CRUD, managed-agent lifecycle work, direct auth-bundle mutation, and filesystem editing as outside the packaged skill scope
- **AND THEN** it does not present those actions as part of low-level agent-definition guidance

### Requirement: `houmao-manage-agent-definition` resolves the `houmao-mgr` launcher in the required precedence order

The packaged `houmao-manage-agent-definition` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace in this order:

1. repo-local `.venv` executable,
2. Pixi-managed project invocation,
3. project-local `uv run`,
4. globally installed `houmao-mgr` from uv tools.

The skill SHALL treat global uv-tools installation as the default end-user case when no development-project hints justify a repo-local launcher.

The skill SHALL tell the agent to look for development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` before choosing a repo-local launcher.

The resolved launcher SHALL be reused for any routed definition-management action selected through the packaged skill.

#### Scenario: Repo-local `.venv` takes precedence over other launchers

- **WHEN** the current workspace provides `.venv/bin/houmao-mgr`
- **THEN** the skill tells the agent to use that repo-local executable first
- **AND THEN** it does not prefer Pixi, project-local `uv run`, or the global uv-tools install for that workspace

#### Scenario: Pixi-managed project takes precedence when no `.venv` launcher exists

- **WHEN** the current workspace has no repo-local `.venv` launcher
- **AND WHEN** the current workspace has Pixi development-project hints
- **THEN** the skill tells the agent to use `pixi run houmao-mgr`
- **AND THEN** it does not skip directly to project-local `uv run` or the global uv-tools install

#### Scenario: Project-local uv run is used when Pixi is absent

- **WHEN** the current workspace has no repo-local `.venv` launcher
- **AND WHEN** no Pixi-managed project hints are present
- **AND WHEN** the current workspace has project-local uv hints such as `uv.lock`
- **THEN** the skill tells the agent to use `uv run houmao-mgr`
- **AND THEN** it does not skip directly to the global uv-tools install

#### Scenario: Global uv-tools install remains the end-user default

- **WHEN** the current workspace does not provide repo-local `.venv`, Pixi, or project-local uv hints
- **THEN** the skill tells the agent to use the globally installed `houmao-mgr` command from uv tools
- **AND THEN** it treats that path as the ordinary end-user launcher

### Requirement: `houmao-manage-agent-definition` selects the correct current low-level command and asks before guessing

The packaged `houmao-manage-agent-definition` skill SHALL tell the agent to recover omitted definition-management inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess missing required inputs that are not explicit in current or recent conversation context.

The skill SHALL select commands by target and action:

- use `roles init` for creating one new minimal role root
- use `presets add` for creating one named preset
- use `roles list` for listing roles
- use `presets list` for listing named presets
- use `roles get` for inspecting one role, adding `--include-prompt` when the user explicitly asks to inspect prompt text or the full low-level definition
- use `presets get` for inspecting one named preset
- use `roles set` for changing the canonical role prompt
- use `presets set` for changing one named preset's role, tool, setup, auth reference, skill membership, or prompt mode
- use `roles remove` for removing one role
- use `presets remove` for removing one named preset

At minimum, the skill SHALL require the agent to obtain:

- for `roles list`: no role name
- for `presets list`: no preset name, plus any optional filters only when the user explicitly asked for them
- for `roles get`: the role name
- for `presets get`: the preset name
- for `roles init`: the role name, plus an optional initial prompt only when the user asked for it explicitly
- for `roles set`: the role name and at least one explicit prompt mutation
- for `presets add`: the preset name, role name, tool, and any optional preset fields the user explicitly wants to author
- for `presets set`: the preset name and at least one explicit preset mutation
- for removal: the concrete role or preset target to delete

When the user asks to change which credential bundle one preset or low-level definition uses, the skill SHALL treat that as a preset-auth-reference change on `presets set` rather than as direct auth-bundle mutation.

When the user asks to change env vars or auth files inside an auth bundle, the skill SHALL report that the request belongs to `houmao-manage-credentials` rather than inventing direct file edits or routing that request through definition-management commands.

#### Scenario: Full role inspection uses explicit prompt inclusion

- **WHEN** the user asks the agent to inspect one role's full low-level definition including its prompt text
- **THEN** the skill directs the agent to use `houmao-mgr project agents roles get --include-prompt`
- **AND THEN** it does not require direct reads from `.houmao/agents/roles/<role>/system-prompt.md`

#### Scenario: Preset credential change stays within definition structure

- **WHEN** the user asks the agent to change which credential bundle one preset references
- **THEN** the skill directs the agent to use `houmao-mgr project agents presets set --auth ...` or `--clear-auth`
- **AND THEN** it treats that change as part of preset structure rather than as direct auth-bundle mutation

#### Scenario: Auth-bundle content mutation stays on the credential skill

- **WHEN** the user asks the agent to add, remove, or change env vars or auth files inside an auth bundle
- **THEN** the skill reports that the request belongs to the credential-management workflow
- **AND THEN** it does not claim that `houmao-manage-agent-definition` covers that lower-level auth-bundle content mutation

#### Scenario: Missing target or mutation requires a user question

- **WHEN** the selected definition-management action still lacks a required target or explicit mutation after checking the current prompt and recent chat context
- **THEN** the skill tells the agent to ask the user for the missing input before proceeding
- **AND THEN** it does not guess a role, preset name, tool, or field change
