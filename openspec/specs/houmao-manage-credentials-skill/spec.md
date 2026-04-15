# houmao-manage-credentials-skill Specification

## Purpose
Define the packaged Houmao-owned `houmao-credential-mgr` skill for credential-management guidance across project overlays and plain agent-definition directories.

## Requirements

### Requirement: Houmao provides a packaged `houmao-credential-mgr` system skill
The system SHALL package a Houmao-owned system skill named `houmao-credential-mgr` under the maintained system-skill asset root.

That skill SHALL instruct agents to manage credentials through these supported commands:

- `houmao-mgr project credentials <tool> list`
- `houmao-mgr project credentials <tool> get`
- `houmao-mgr project credentials <tool> add`
- `houmao-mgr project credentials <tool> set`
- `houmao-mgr project credentials <tool> rename`
- `houmao-mgr project credentials <tool> remove`
- `houmao-mgr credentials <tool> list --agent-def-dir <path>`
- `houmao-mgr credentials <tool> get --agent-def-dir <path> --name <name>`
- `houmao-mgr credentials <tool> add --agent-def-dir <path> --name <name>`
- `houmao-mgr credentials <tool> set --agent-def-dir <path> --name <name>`
- `houmao-mgr credentials <tool> rename --agent-def-dir <path> --name <name> --to <new-name>`
- `houmao-mgr credentials <tool> remove --agent-def-dir <path> --name <name>`

The packaged skill SHALL scope that guidance to the supported tool families:

- `claude`
- `codex`
- `gemini`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `list`
- `get`
- `add`
- `set`
- `rename`
- `remove`

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `project easy specialist create|list|get|remove`
- `project easy instance launch|list|get|stop`
- `agents launch|join|list|stop|cleanup`
- `project agents tools <tool> setups ...`
- `project agents roles ...`
- `project mailbox ...`, `agents cleanup mailbox`, and `admin cleanup runtime ...`
- direct hand-editing of credential files under `.houmao/agents/tools/` or plain agent-definition directories

#### Scenario: Installed skill points the agent at the supported credential commands
- **WHEN** an agent opens the installed `houmao-credential-mgr` skill
- **THEN** the skill directs the agent to use the supported `project credentials ...` or `credentials ... --agent-def-dir <path>` command surfaces for credential work
- **AND THEN** it does not redirect the agent to ad hoc filesystem editing or unrelated runtime-control surfaces

#### Scenario: Installed skill routes to action-specific local guidance including rename
- **WHEN** an agent reads the installed `houmao-credential-mgr` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `list`, `get`, `add`, `set`, `rename`, and `remove`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than one flattened entry page

#### Scenario: Installed skill keeps non-credential project and runtime surfaces out of scope
- **WHEN** an agent reads the installed `houmao-credential-mgr` skill
- **THEN** the skill marks specialist CRUD, managed-agent lifecycle work, mailbox cleanup, and direct file editing as outside the packaged skill scope
- **AND THEN** it does not present those actions as part of the supported credential-management guidance

### Requirement: `houmao-credential-mgr` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-credential-mgr` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace using this default order unless the user explicitly requests a different launcher:

1. resolve `houmao-mgr` with `command -v houmao-mgr` and use the command found on `PATH`,
2. if that lookup fails, use the uv-managed fallback `uv tool run --from houmao houmao-mgr`,
3. if the PATH lookup and uv-managed fallback do not satisfy the turn, choose an appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`.

The skill SHALL treat the `command -v houmao-mgr` result as the ordinary first-choice launcher for the current turn.

The skill SHALL treat the uv-managed fallback as the ordinary non-PATH fallback because Houmao's documented installation path uses uv tools.

The skill SHALL only probe development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` after PATH resolution and uv fallback do not satisfy the turn, unless the user explicitly asks for a development launcher.

The skill SHALL honor an explicit user instruction to use a specific launcher family even when a higher-priority default launcher is available.

The resolved launcher SHALL be reused for any routed credential action selected through the packaged skill.

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

### Requirement: `houmao-credential-mgr` selects the correct credential action and target before acting
The packaged `houmao-credential-mgr` skill SHALL tell the agent to recover omitted credential inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess missing required inputs that are not explicit in current or recent conversation context.

The skill SHALL resolve both action and target:

- use `project credentials <tool> list|get|add|set|rename|remove` when the request is clearly project-local or the active project overlay is the intended target,
- use `credentials <tool> list|get|add|set|rename|remove --agent-def-dir <path>` when the user explicitly targets a plain agent-definition directory,
- ask the user before proceeding when the action or target remains ambiguous.

The skill SHALL select commands by requested action:

- use `list` for listing credential names for one supported tool,
- use `get --name <name>` for safe redacted inspection of one existing credential,
- use `add --name <name>` for creating one new credential,
- use `set --name <name>` for updating one existing credential,
- use `rename --name <name> --to <new-name>` for renaming one existing credential,
- use `remove --name <name>` for removing one existing credential.

At minimum, the skill SHALL require the agent to obtain:

- for `list`: the tool family and a resolvable target,
- for `get`: the tool family, target, and credential name,
- for `remove`: the tool family, target, and credential name,
- for `add`: the tool family, target, credential name, and enough supported credential input for that selected tool,
- for `set`: the tool family, target, credential name, and at least one supported change for that selected tool,
- for `rename`: the tool family, target, current credential name, and target credential name.

For mutating actions, the skill SHALL use only documented per-tool credential flags and SHALL NOT invent unsupported file flags, clear-style flags, or provider-neutral abstractions that the selected CLI surface does not actually support.

For `get`, the skill SHALL rely on the command's structured redacted output and SHALL NOT print secret env values or raw credential-file contents by bypassing that safe inspection surface.

Unless the user explicitly asks for a narrower path-based inspection as part of the current request, the skill SHALL NOT scan environment variables, home directories, repo-local tool homes, or unrelated filesystem locations to infer missing credential inputs for `add` or `set`.

#### Scenario: Project-local credential work uses the project wrapper
- **WHEN** the current prompt asks the agent to manage one credential in the current project workspace
- **AND WHEN** no explicit plain agent-definition directory target is provided
- **THEN** the skill routes that work through `houmao-mgr project credentials <tool> ...`
- **AND THEN** it does not route the request through the removed `project agents tools <tool> auth ...` surface

#### Scenario: Explicit agent-definition-directory work uses the dedicated direct-dir form
- **WHEN** the current prompt asks the agent to manage credentials under `tests/fixtures/plain-agent-def`
- **THEN** the skill routes that work through `houmao-mgr credentials <tool> ... --agent-def-dir tests/fixtures/plain-agent-def`
- **AND THEN** it does not reinterpret that request as project-local credential management

#### Scenario: Rename requires both the current and target names
- **WHEN** the current prompt asks the agent to rename one credential
- **AND WHEN** the tool, target, current credential name, or target credential name is not explicit in current or recent conversation context
- **THEN** the skill tells the agent to ask the user for the missing rename input before proceeding
- **AND THEN** it does not guess either side of the rename

#### Scenario: Inspecting one credential stays redacted
- **WHEN** the current prompt asks the agent to inspect one existing credential
- **THEN** the skill uses the structured `get` output as the inspection contract
- **AND THEN** it reports presence and non-secret metadata without dumping raw secret values or raw credential-file contents

### Requirement: `houmao-credential-mgr` routes credential login helper workflows
The packaged `houmao-credential-mgr` skill SHALL route requests to obtain fresh provider auth files through the supported credential `login` helper when the user asks to log in with a new Codex, Claude, or Gemini account and import the resulting credential into Houmao storage.

The top-level `SKILL.md` for that packaged skill SHALL include `login` in its action router alongside `list`, `get`, `add`, `set`, `rename`, and `remove`.

The skill SHALL instruct agents to use:

- `houmao-mgr project credentials <tool> login --name <name>` when the active project overlay is the intended target,
- `houmao-mgr credentials <tool> login --agent-def-dir <path> --name <name>` when the user explicitly targets a plain agent-definition directory,
- the explicit update option only when the user intends to replace an existing credential.

The skill SHALL explain that the command creates an isolated temporary provider home, invokes the installed provider CLI with inherited stdio, imports the expected auth artifact into Houmao storage, and deletes the temporary provider home after a successful import by default.

The skill SHALL tell agents not to hand-roll this workflow by manually creating provider home directories, running provider login commands, copying auth files into credential storage, or deleting temp directories outside the supported `houmao-mgr credentials ... login` surface unless the user explicitly asks for a lower-level recovery workflow after a failed login attempt.

#### Scenario: Login request routes to the project credential helper
- **WHEN** the current prompt asks the agent to log in to Codex with another account and import it into the current project as `work`
- **AND WHEN** no explicit plain agent-definition directory target is provided
- **THEN** the skill routes the work through `houmao-mgr project credentials codex login --name work`
- **AND THEN** it does not tell the agent to manually copy `auth.json` into Houmao storage

#### Scenario: Explicit direct-dir login request includes the target directory
- **WHEN** the current prompt asks the agent to obtain a new Gemini OAuth credential under `tests/fixtures/plain-agent-def` as `personal`
- **THEN** the skill routes the work through `houmao-mgr credentials gemini login --agent-def-dir tests/fixtures/plain-agent-def --name personal`
- **AND THEN** it does not reinterpret that request as project-local credential management

#### Scenario: Existing credential replacement requires user intent
- **WHEN** the current prompt asks the agent to log in and import a credential name that may already exist
- **AND WHEN** the user has not explicitly said to replace or update the existing credential
- **THEN** the skill tells the agent to use the default create-only login behavior
- **AND THEN** it does not add the explicit update option on the user's behalf

#### Scenario: Skill explains temp cleanup ownership
- **WHEN** an agent reads the login workflow guidance
- **THEN** the skill states that `houmao-mgr credentials ... login` owns the temporary provider home lifecycle
- **AND THEN** it states that successful imports delete the temp home by default while failed attempts preserve and report it for recovery

### Requirement: `houmao-credential-mgr` ships per-tool credential kinds references and cites them when asking the user for missing auth inputs

The packaged `houmao-credential-mgr` skill SHALL ship a `references/` directory with three per-tool credential kinds reference pages:

- `claude-credential-kinds.md`
- `codex-credential-kinds.md`
- `gemini-credential-kinds.md`

Each kinds reference page SHALL enumerate the user-facing credential kinds the selected tool accepts through `project credentials <tool> add` and `credentials <tool> add --agent-def-dir <path>`, including at minimum:

- Claude: API key, auth token, OAuth token, and a vendor-login config-directory kind that carries `.credentials.json` plus companion `.claude.json` when present.
- Codex: API key, and a cached login state kind that carries an `auth.json` file.
- Gemini: API key, a Vertex AI kind that pairs a Google API key with the Vertex AI selector, and an OAuth creds kind that carries an `.gemini/oauth_creds.json` file.

Each kinds reference page SHALL for every enumerated kind state a plain-language name, a description of what the user provides, the `project credentials <tool> add` flag it maps to, and a short guidance line on when to pick that kind.

Each kinds reference page SHALL use flag spellings that match the `houmao-credential-mgr` command surface (for example `--oauth-token`, `--auth-json`, `--oauth-creds`, `--config-dir`) rather than `houmao-specialist-mgr` create-command spellings.

Each kinds reference page SHALL state that the credential-mgr add command does not run discovery-mode credential creation, and SHALL point the user at `houmao-specialist-mgr` when the user wants auto credentials, env lookup, or directory scan during credential creation.

The add action within the packaged skill SHALL cite the kinds reference for the currently selected tool when the skill presents auth-input options to the user.

The `SKILL.md` top-level file SHALL list the three credential kinds references as the credential kinds menu surface.

#### Scenario: Selected tool loads only its own kinds reference when asking the user
- **WHEN** the add action needs to present auth-input options to the user for one selected tool
- **THEN** the skill loads the kinds reference for that tool and presents the enumerated kinds as a menu
- **AND THEN** it does not load the kinds references for the other two tools in the same turn

#### Scenario: Kinds reference uses credential-mgr flag spellings
- **WHEN** an agent reads a `houmao-credential-mgr` credential kinds reference
- **THEN** each enumerated kind maps to a `project credentials <tool> add` flag such as `--api-key`, `--auth-token`, `--oauth-token`, `--auth-json`, `--oauth-creds`, `--config-dir`, or `--google-api-key` plus `--use-vertex-ai`
- **AND THEN** it does not use the `houmao-specialist-mgr` create-command spellings

#### Scenario: Kinds reference notes the credential-mgr discovery gap
- **WHEN** an agent reads a `houmao-credential-mgr` credential kinds reference
- **THEN** the page states that the add command does not run discovery-mode credential creation
- **AND THEN** the page points the user at `houmao-specialist-mgr` when the user wants discovery-mode import
