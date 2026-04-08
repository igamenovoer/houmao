## Purpose
Define the packaged Houmao-owned `houmao-credential-mgr` skill for project-local auth-bundle management guidance.

## Requirements

### Requirement: Houmao provides a packaged `houmao-credential-mgr` system skill
The system SHALL package a Houmao-owned system skill named `houmao-credential-mgr` under the maintained system-skill asset root.

That skill SHALL instruct agents to manage project-local auth bundles through these supported commands:

- `houmao-mgr project agents tools <tool> auth list`
- `houmao-mgr project agents tools <tool> auth get`
- `houmao-mgr project agents tools <tool> auth add`
- `houmao-mgr project agents tools <tool> auth set`
- `houmao-mgr project agents tools <tool> auth remove`

The packaged skill SHALL scope that guidance to the supported project-local tool families:

- `claude`
- `codex`
- `gemini`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `list`
- `get`
- `add`
- `set`
- `remove`

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `project easy specialist create|list|get|remove`
- `project easy instance launch|list|get|stop`
- `agents launch|join|list|stop|cleanup`
- `project agents tools <tool> setups ...`
- `project agents roles ...`
- `project mailbox ...`, `agents cleanup mailbox`, and `admin cleanup runtime ...`
- direct hand-editing of auth-bundle files under `.houmao/agents/tools/`

#### Scenario: Installed skill points the agent at project-local auth-bundle commands
- **WHEN** an agent opens the installed `houmao-credential-mgr` skill
- **THEN** the skill directs the agent to use the supported `project agents tools <tool> auth ...` command surface for auth-bundle work
- **AND THEN** it does not redirect the agent to ad hoc filesystem editing or unrelated runtime-control surfaces

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-credential-mgr` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `list`, `get`, `add`, `set`, and `remove`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than one flattened entry page

#### Scenario: Installed skill keeps non-auth project and runtime surfaces out of scope
- **WHEN** an agent reads the installed `houmao-credential-mgr` skill
- **THEN** the skill marks specialist CRUD, managed-agent lifecycle work, mailbox cleanup, and direct file editing as outside the packaged skill scope
- **AND THEN** it does not present those actions as part of project-local credential-management guidance

### Requirement: `houmao-credential-mgr` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-credential-mgr` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace using this default order unless the user explicitly requests a different launcher:

1. resolve `houmao-mgr` with `command -v houmao-mgr` and use the command found on `PATH`,
2. if that lookup fails, use the uv-managed fallback `uv tool run --from houmao houmao-mgr`,
3. if the PATH lookup and uv-managed fallback do not satisfy the turn, choose an appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`.

The skill SHALL treat the `command -v houmao-mgr` result as the ordinary first-choice launcher for the current turn.

The skill SHALL treat the uv-managed fallback as the ordinary non-PATH fallback because Houmao's documented installation path uses uv tools.

The skill SHALL only probe development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` after PATH resolution and uv fallback do not satisfy the turn, unless the user explicitly asks for a development launcher.

The skill SHALL honor an explicit user instruction to use a specific launcher family even when a higher-priority default launcher is available.

The resolved launcher SHALL be reused for any routed auth-bundle action selected through the packaged skill.

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

### Requirement: `houmao-credential-mgr` selects the correct auth-bundle action and asks before guessing
The packaged `houmao-credential-mgr` skill SHALL tell the agent to recover omitted auth-bundle inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess missing required inputs that are not explicit in current or recent conversation context.

The skill SHALL select commands by requested action:

- use `auth list` for listing bundle names for one supported tool,
- use `auth get --name <name>` for safe redacted inspection of one existing bundle,
- use `auth add --name <name>` for creating one new bundle,
- use `auth set --name <name>` for updating one existing bundle,
- use `auth remove --name <name>` for removing one existing bundle.

At minimum, the skill SHALL require the agent to obtain:

- for `list`: the tool family,
- for `get`: the tool family and bundle name,
- for `remove`: the tool family and bundle name,
- for `add`: the tool family, bundle name, and enough supported auth input for that selected tool,
- for `set`: the tool family, bundle name, and at least one supported change for that selected tool.

When the user asks to update credentials, the skill SHALL map that request to the `set` action rather than guessing another verb.

For mutating actions, the skill SHALL use only documented per-tool auth flags and SHALL NOT invent unsupported file flags, clear-style flags, or provider-neutral abstractions that the selected CLI surface does not actually support.

For `get`, the skill SHALL rely on the command's structured redacted output and SHALL NOT print secret env values or raw auth-file contents by bypassing that safe inspection surface.

Unless the user explicitly asks for a narrower path-based inspection as part of the current request, the skill SHALL NOT scan environment variables, home directories, repo-local tool homes, or unrelated filesystem locations to infer missing auth inputs for `add` or `set`.

#### Scenario: List action does not require a bundle name
- **WHEN** the current prompt asks the agent to list project-local credentials for one supported tool
- **THEN** the skill allows the agent to proceed without asking for a credential-bundle name
- **AND THEN** it does not invent a target bundle just because other actions require one

#### Scenario: Get or remove asks before guessing the target bundle
- **WHEN** the current prompt asks for auth-bundle inspection or removal
- **AND WHEN** the tool or bundle name is not explicit in current or recent conversation context
- **THEN** the skill tells the agent to ask the user for the missing tool or bundle name before proceeding
- **AND THEN** it does not guess which stored auth bundle the user intended

#### Scenario: Set requires an explicit supported change
- **WHEN** the current prompt asks the agent to update one existing auth bundle
- **AND WHEN** the prompt does not provide any explicit supported env value, auth file input, or clear-style change for the selected tool
- **THEN** the skill tells the agent to ask the user for the missing change before proceeding
- **AND THEN** it does not fabricate a default mutation or widen into ambient credential discovery

#### Scenario: Inspecting one bundle stays redacted
- **WHEN** the current prompt asks the agent to inspect one existing auth bundle
- **THEN** the skill uses the structured `auth get` output as the inspection contract
- **AND THEN** it reports presence and non-secret metadata without dumping raw secret values or raw auth-file contents

#### Scenario: Skill does not invent unsupported clear semantics
- **WHEN** the user asks the agent for a file-clear action that the selected tool's current `auth set` surface does not support
- **THEN** the skill reports that limitation explicitly
- **AND THEN** it does not invent an unsupported clear flag or silently reinterpret the request as another action
