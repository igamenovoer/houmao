## Purpose
Define the packaged Houmao-owned `houmao-agent-definition` system skill for low-level project-local role and preset management.
## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-definition` system skill

The system SHALL package a Houmao-owned system skill named `houmao-agent-definition` under the maintained system-skill asset root.

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
- **WHEN** an agent opens the installed `houmao-agent-definition` skill
- **THEN** the skill directs the agent to use the supported `project agents roles ...` and `project agents presets ...` command surfaces for low-level definition work
- **AND THEN** it does not redirect the agent to ad hoc filesystem editing, stale command trees, or unrelated runtime-control surfaces

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-agent-definition` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `create`, `list`, `get`, `set`, and `remove`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than one flattened entry page

#### Scenario: Installed skill keeps easy, runtime, and auth-content workflows out of scope
- **WHEN** an agent reads the installed `houmao-agent-definition` skill
- **THEN** the skill marks easy-specialist CRUD, managed-agent lifecycle work, direct auth-bundle mutation, and filesystem editing as outside the packaged skill scope
- **AND THEN** it does not present those actions as part of low-level agent-definition guidance

### Requirement: `houmao-agent-definition` resolves the `houmao-mgr` launcher in the required precedence order

The packaged `houmao-agent-definition` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace using this default order unless the user explicitly requests a different launcher:

1. resolve `houmao-mgr` with `command -v houmao-mgr` and use the command found on `PATH`,
2. if that lookup fails, use the uv-managed fallback `uv tool run --from houmao houmao-mgr`,
3. if the PATH lookup and uv-managed fallback do not satisfy the turn, choose an appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`.

The skill SHALL treat the `command -v houmao-mgr` result as the ordinary first-choice launcher for the current turn.

The skill SHALL treat the uv-managed fallback as the ordinary non-PATH fallback because Houmao's documented installation path uses uv tools.

The skill SHALL only probe development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` after PATH resolution and uv fallback do not satisfy the turn, unless the user explicitly asks for a development launcher.

The skill SHALL honor an explicit user instruction to use a specific launcher family even when a higher-priority default launcher is available.

The resolved launcher SHALL be reused for any routed definition-management action selected through the packaged skill.

#### Scenario: PATH launcher is preferred before development probing
- **WHEN** `command -v houmao-mgr` succeeds in the current workspace
- **THEN** the skill tells the agent to use that PATH-resolved `houmao-mgr` command for the turn
- **AND THEN** it does not probe `.venv`, Pixi, or project-local uv launchers first

#### Scenario: uv fallback is used when PATH lookup fails
- **WHEN** `command -v houmao-mgr` fails in the current workspace
- **THEN** the skill tells the agent to try `uv tool run --from houmao houmao-mgr`
- **AND THEN** it treats that uv-managed launcher as the ordinary next fallback because Houmao is officially installed through uv tools

#### Scenario: Development launchers are later defaults, not first probes
- **WHEN** `command -v houmao-mgr` fails
- **AND WHEN** the uv-managed fallback does not satisfy the turn
- **AND WHEN** the current workspace provides development launchers such as Pixi, repo-local `.venv`, or project-local uv
- **THEN** the skill tells the agent to choose an appropriate development launcher for that workspace
- **AND THEN** it does not treat those development launchers as the default first search path

#### Scenario: Explicit user launcher choice overrides the default order
- **WHEN** the user explicitly asks to use `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, project-local `uv run houmao-mgr`, or another specific launcher
- **THEN** the skill tells the agent to honor that requested launcher
- **AND THEN** it does not replace the user-requested launcher with the default PATH-first or uv-fallback choice

### Requirement: `houmao-agent-definition` selects the correct current low-level command and asks before guessing

The packaged `houmao-agent-definition` skill SHALL tell the agent to recover omitted definition-management inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

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

When the user asks to change env vars or auth files inside an auth bundle, the skill SHALL report that the request belongs to `houmao-credential-mgr` rather than inventing direct file edits or routing that request through definition-management commands.

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
- **AND THEN** it does not claim that `houmao-agent-definition` covers that lower-level auth-bundle content mutation

#### Scenario: Missing target or mutation requires a user question
- **WHEN** the selected definition-management action still lacks a required target or explicit mutation after checking the current prompt and recent chat context
- **THEN** the skill tells the agent to ask the user for the missing input before proceeding
- **AND THEN** it does not guess a role, preset name, tool, or field change

### Requirement: `houmao-agent-definition` is the canonical pre-launch agent-definition skill
The packaged `houmao-agent-definition` skill SHALL be the canonical Houmao-owned skill for persisted pre-launch agent definition workflows.

That unified skill SHALL expose these skill-level subcommands:

- `roles` for low-level prompt-only roles;
- `recipes` for low-level recipes, with `presets` as a compatibility alias;
- `raw-profiles` for low-level recipe-backed launch profiles using the underlying `houmao-mgr project agents launch-profiles ...` CLI;
- `specialists` for project-easy specialist templates;
- `profiles` for specialist-backed easy profiles;
- `create-agent-fast-forward` for creating or selecting a specialist, creating or updating an easy profile, printing the launch command, and not launching a live agent;
- `launch-agent` for the limited easy launch entry point that hands off broader live lifecycle work to `houmao-agent-instance`;
- `stop-agent` for the limited easy stop entry point that hands off broader live lifecycle work to `houmao-agent-instance`.

The skill SHALL treat loosely stated `profile`, `agent profile`, `launch profile`, and `ready profile` wording as the `profiles` subcommand by default unless the user explicitly asks for `raw-profiles`, raw profile behavior, recipe-backed profile behavior, or the exact `project agents launch-profiles` CLI surface.

#### Scenario: Unified skill routes named subcommands
- **WHEN** an agent reads the packaged `houmao-agent-definition` skill
- **THEN** the top-level page lists the supported skill subcommands and their local subskill routes
- **AND THEN** the agent can route a user request that explicitly names `profiles`, `raw-profiles`, or `create-agent-fast-forward` without asking which branch was intended

#### Scenario: Ambiguous launch profile means easy profile
- **WHEN** a user asks to create or update an agent launch profile without saying raw, recipe-backed, or `project agents launch-profiles`
- **THEN** the skill routes the request to the `profiles` subcommand
- **AND THEN** it does not route the request to low-level recipe-backed launch profiles by default

### Requirement: `houmao-agent-definition` uses lane-specific subskills
The unified `houmao-agent-definition` skill SHALL keep its entry page concise and SHALL route detailed behavior into lane-specific local subskills or references.

At minimum, the skill SHALL distinguish `roles`, `recipes`, `raw-profiles`, `specialists`, `profiles`, `create-agent-fast-forward`, `launch-agent`, and `stop-agent`.

The skill SHALL include shared guidance for launcher resolution, missing-input handling, profile-lane terminology, and credential-routing boundaries.

The entry page SHALL either route existing generic `actions/*` pages through the new subcommand vocabulary or mark those pages as legacy low-level-only references so they do not conflict with the subcommand table.

#### Scenario: Entry page loads only the relevant lane
- **WHEN** the user asks to update one easy profile
- **THEN** `houmao-agent-definition` routes to the `profiles` subcommand and easy-profile subskill
- **AND THEN** it does not load or flatten unrelated low-level recipe, raw-profile, or easy-instance launch instructions into the entry page

#### Scenario: Raw profile route is explicit
- **WHEN** the user asks for `raw-profiles` or for the exact `project agents launch-profiles` surface
- **THEN** `houmao-agent-definition` routes to the low-level recipe-backed profile subskill
- **AND THEN** the subskill names the underlying `houmao-mgr project agents launch-profiles ...` commands

### Requirement: Unified skill keeps neighboring platform concerns out of scope
The unified `houmao-agent-definition` skill SHALL NOT become the owner for credential bundle CRUD, mailbox root/account administration, workspace creation, broad live managed-agent lifecycle, or direct filesystem edits under `.houmao/`.

It SHALL route those concerns to `houmao-credential-mgr`, `houmao-mailbox-mgr`, `houmao-utils-workspace-mgr`, `houmao-agent-instance`, or other maintained Houmao skills as appropriate.

#### Scenario: Credential content mutation is routed away
- **WHEN** a user asks to mutate auth files or environment variables inside a credential bundle while using `houmao-agent-definition`
- **THEN** the skill routes the request to `houmao-credential-mgr`
- **AND THEN** it does not treat credential-bundle content mutation as specialist, recipe, or profile authoring
