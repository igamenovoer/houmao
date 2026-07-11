# houmao-manage-credentials-skill Specification

## Purpose
Define the packaged Houmao-owned `houmao-credential-mgr` skill for credential-management guidance across project overlays and retained internal native-agent credential roots.
## Requirements
### Requirement: Houmao provides a packaged `houmao-credential-mgr` system skill

The system SHALL package a Houmao-owned system skill named `houmao-credential-mgr` under the maintained system-skill asset root.

That skill SHALL instruct agents to manage credential CRUD through these supported commands for supported credential-CRUD tool families:

- `houmao-mgr project credentials <tool> list`
- `houmao-mgr project credentials <tool> get`
- `houmao-mgr project credentials <tool> add`
- `houmao-mgr project credentials <tool> set`
- `houmao-mgr project credentials <tool> rename`
- `houmao-mgr project credentials <tool> remove`
- `houmao-mgr internals native-agent credentials <tool> list --native-agent-root <path>`
- `houmao-mgr internals native-agent credentials <tool> get --native-agent-root <path> --name <name>`
- `houmao-mgr internals native-agent credentials <tool> add --native-agent-root <path> --name <name>`
- `houmao-mgr internals native-agent credentials <tool> set --native-agent-root <path> --name <name>`
- `houmao-mgr internals native-agent credentials <tool> rename --native-agent-root <path> --name <name> --to <new-name>`
- `houmao-mgr internals native-agent credentials <tool> remove --native-agent-root <path> --name <name>`

The packaged skill SHALL scope credential CRUD guidance to the supported tool families:

- `claude`
- `codex`
- `gemini`
- `kimi`

That skill SHALL instruct agents to use credential login helpers only for tool families with maintained login-helper support:

- `houmao-mgr project credentials <login-tool> login`
- `houmao-mgr internals native-agent credentials <login-tool> login --native-agent-root <path> --name <name>`

The packaged skill SHALL scope credential login-helper guidance to:

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
- `login`

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `project specialist create|list|get|remove`
- `project agents launch|list|get|stop`
- `agents launch|join|list|stop|cleanup`
- `internals native-agent tools <tool> setups ...`
- `internals native-agent roles ...`
- `project mailbox ...`, `agents cleanup mailbox`, and `admin cleanup runtime ...`
- direct hand-editing of credential files under `.houmao/agents/tools/` or retained native-agent credential roots

#### Scenario: Installed skill points the agent at the supported credential commands

- **WHEN** an agent opens the installed `houmao-credential-mgr` skill
- **THEN** the skill directs the agent to use the supported `project [--project-dir <dir>] credentials ...` or `internals native-agent credentials ... --native-agent-root <path>` command surfaces for credential work
- **AND THEN** it does not redirect the agent to ad hoc filesystem editing or unrelated runtime-control surfaces

#### Scenario: Installed skill routes to action-specific local guidance including rename

- **WHEN** an agent reads the installed `houmao-credential-mgr` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `list`, `get`, `add`, `set`, `rename`, and `remove`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than one flattened entry page

#### Scenario: Installed skill keeps non-credential project and runtime surfaces out of scope

- **WHEN** an agent reads the installed `houmao-credential-mgr` skill
- **THEN** the skill marks specialist CRUD, managed-agent lifecycle work, mailbox cleanup, and direct file editing as outside the packaged skill scope
- **AND THEN** it does not present those actions as part of the supported credential-management guidance

#### Scenario: Kimi credential work is CRUD-only

- **WHEN** an agent reads `houmao-credential-mgr` guidance for tool `kimi`
- **THEN** the skill presents `list`, `get`, `add`, `set`, `rename`, and `remove` as supported credential actions
- **AND THEN** it does not present a Kimi credential `login` helper unless a maintained Kimi login helper is added in a later change

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

### Requirement: Credential-management skill uses consolidated project targeting
The packaged credential-management skill SHALL route ordinary project credential requests to:

```text
houmao-mgr project [--project-dir <dir>] credentials <tool> <verb>
```

When the user names a project directory explicitly, the skill SHALL use the group-level `--project-dir` option instead of selecting a top-level credential target.

The skill SHALL NOT present `houmao-mgr credentials --project ...` as the maintained project credential workflow.

#### Scenario: Skill routes explicit project credential request
- **WHEN** a user asks the agent to list Codex credentials for project `/repo`
- **THEN** the skill guidance routes to `houmao-mgr project --project-dir /repo credentials codex list`
- **AND THEN** it does not route to `houmao-mgr credentials --project codex list`

### Requirement: Credential-management skill routes direct native credentials to internals
The packaged credential-management skill SHALL treat direct native-agent credential roots as internal provider-aligned material.

When the user explicitly asks for direct native-agent credential CRUD outside a Houmao project, the skill SHALL route to:

```text
houmao-mgr internals native-agent credentials <tool> <verb> --native-agent-root <dir>
```

The skill SHALL ask for a native-agent root when the user requests direct native credential work but no root can be inferred.

#### Scenario: Skill routes direct native credential request
- **WHEN** a user asks the agent to update a Codex credential under native-agent root `/tmp/native`
- **THEN** the skill guidance routes to `houmao-mgr internals native-agent credentials codex set --native-agent-root /tmp/native`
- **AND THEN** it does not route to a top-level `credentials --agent-def-dir` command

### Requirement: `houmao-credential-mgr` selects the correct credential action and target before acting
The packaged `houmao-credential-mgr` skill SHALL tell the agent to recover omitted credential inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess missing required inputs that are not explicit in current or recent conversation context.

The skill SHALL resolve both action and target:

- use `project [--project-dir <dir>] credentials <tool> list|get|add|set|rename|remove|login` when the request is clearly project-local, names a project directory, or the active project overlay is the intended target,
- use `internals native-agent credentials <tool> list|get|add|set|rename|remove|login --native-agent-root <path>` when the user explicitly targets a direct native-agent credential root,
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
- **AND WHEN** no explicit direct native-agent root target is provided
- **THEN** the skill routes that work through `houmao-mgr project credentials <tool> ...`
- **AND THEN** it does not route the request through the removed `internals native-agent tools <tool> auth ...` surface

#### Scenario: Explicit project credential work uses the project directory selector
- **WHEN** the current prompt asks the agent to list Codex credentials for project `/repo`
- **THEN** the skill routes that work through `houmao-mgr project --project-dir /repo credentials codex list`
- **AND THEN** it does not route the request through a top-level credential target selector

#### Scenario: Explicit native-agent credential work uses internals
- **WHEN** the current prompt asks the agent to manage credentials under `tests/fixtures/plain-agent-def`
- **THEN** the skill routes that work through `houmao-mgr internals native-agent credentials <tool> ... --native-agent-root tests/fixtures/plain-agent-def`
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

- `houmao-mgr project [--project-dir <dir>] credentials <tool> login --name <name>` when the selected project overlay is the intended target,
- `houmao-mgr internals native-agent credentials <tool> login --native-agent-root <path> --name <name>` when the user explicitly targets a direct native-agent credential root,
- the explicit update option only when the user intends to replace an existing credential.

The skill SHALL explain that the command creates an isolated temporary provider home, invokes the installed provider CLI with inherited stdio, imports the expected auth artifact into Houmao storage, and deletes the temporary provider home after a successful import by default.

The skill SHALL tell agents not to hand-roll this workflow by manually creating provider home directories, running provider login commands, copying auth files into credential storage, or deleting temp directories outside the supported project or internal native-agent credential login surfaces unless the user explicitly asks for a lower-level recovery workflow after a failed login attempt.

#### Scenario: Login request routes to the project credential helper
- **WHEN** the current prompt asks the agent to log in to Codex with another account and import it into the current project as `work`
- **AND WHEN** no explicit plain agent-definition directory target is provided
- **THEN** the skill routes the work through `houmao-mgr project credentials codex login --name work`
- **AND THEN** it does not tell the agent to manually copy `auth.json` into Houmao storage

#### Scenario: Explicit native-agent login request includes the target root
- **WHEN** the current prompt asks the agent to obtain a new Gemini OAuth credential under native-agent root `tests/fixtures/plain-agent-def` as `personal`
- **THEN** the skill routes the work through `houmao-mgr internals native-agent credentials gemini login --native-agent-root tests/fixtures/plain-agent-def --name personal`
- **AND THEN** it does not reinterpret that request as project-local credential management

#### Scenario: Existing credential replacement requires user intent
- **WHEN** the current prompt asks the agent to log in and import a credential name that may already exist
- **AND WHEN** the user has not explicitly said to replace or update the existing credential
- **THEN** the skill tells the agent to use the default create-only login behavior
- **AND THEN** it does not add the explicit update option on the user's behalf

#### Scenario: Skill explains temp cleanup ownership
- **WHEN** an agent reads the login workflow guidance
- **THEN** the skill states that the supported credential login command owns the temporary provider home lifecycle
- **AND THEN** it states that successful imports delete the temp home by default while failed attempts preserve and report it for recovery

### Requirement: `houmao-credential-mgr` ships per-tool credential kinds references and cites them when asking the user for missing auth inputs

The packaged `houmao-credential-mgr` skill SHALL ship a `references/` directory under `src/houmao/agents/assets/system_skills/houmao-credential-mgr/` and four per-tool credential kinds reference pages inside that directory:

- `claude-credential-kinds.md`
- `codex-credential-kinds.md`
- `gemini-credential-kinds.md`
- `kimi-credential-kinds.md`

Each kinds reference page SHALL enumerate the user-facing credential kinds the selected tool accepts through `houmao-mgr project credentials <tool> add` and `houmao-mgr internals native-agent credentials <tool> add --native-agent-root <path>`, including at minimum the following kinds per tool:

- Claude: API key, auth token, OAuth token, and a vendor-login config-directory kind that carries `.credentials.json` plus companion `.claude.json` when present.
- Codex: API key, and a cached login state kind that carries an `auth.json` file.
- Gemini: API key, a Vertex AI kind that pairs a Google API key with the Vertex AI selector, and an OAuth creds kind that carries an `.gemini/oauth_creds.json` file.
- Kimi: API key or provider-routing material that may include model name, base URL, provider type, Kimi Code base URL, Kimi Code OAuth host, OAuth host, telemetry disablement, `config.toml`, or credential JSON inputs according to the maintained Kimi credential CLI.

Each kinds reference page SHALL for every enumerated kind state:

- a plain-language name for the kind that a first-time user can recognize,
- a description of what the user would provide for that kind,
- the `project credentials <tool> add` flag that the kind maps to in the `houmao-credential-mgr` command surface,
- a short guidance line on when the user would pick that kind.

Each kinds reference page SHALL state that `houmao-credential-mgr/actions/add.md` does not run discovery-mode credential creation, and SHALL point the user at `houmao-specialist-mgr` when the user wants auto credentials, env lookup, or directory scan during credential creation.

The `houmao-credential-mgr/actions/add.md` step that asks the user for missing auth inputs SHALL cite the kinds reference for the currently selected tool when the skill presents auth-input options to the user.

The `houmao-credential-mgr/SKILL.md` top-level file SHALL list the four kinds references as the credential kinds menu surface.

The kinds reference pages SHALL use flag spellings that match the `houmao-credential-mgr` command surface rather than the `houmao-specialist-mgr` create-command spellings.

#### Scenario: Selected tool loads only its own kinds reference when asking the user

- **WHEN** the add action needs to present auth-input options to the user for one selected tool
- **THEN** the skill loads the kinds reference for that tool from the `houmao-credential-mgr` references directory and presents the enumerated kinds as a menu
- **AND THEN** it does not load the kinds references for other tools in the same turn

#### Scenario: Kinds reference uses credential-mgr flag spellings

- **WHEN** an agent reads a `houmao-credential-mgr` credential kinds reference
- **THEN** each enumerated kind maps to a `project credentials <tool> add` flag such as `--api-key`, `--auth-token`, `--oauth-token`, `--auth-json`, `--oauth-creds`, `--config-dir`, `--google-api-key`, `--use-vertex-ai`, `--base-url`, `--provider-type`, `--config-toml`, or `--credential-json`
- **AND THEN** it does not use the corresponding `houmao-specialist-mgr` create-command flag spellings

#### Scenario: Kinds reference notes the credential-mgr discovery gap

- **WHEN** an agent reads a `houmao-credential-mgr` credential kinds reference
- **THEN** the page states that `houmao-credential-mgr/actions/add.md` does not run discovery-mode credential creation
- **AND THEN** the page points the user at `houmao-specialist-mgr` when the user wants auto credentials, env lookup, or directory scan during credential creation

#### Scenario: Kimi kinds reference covers Kimi credential inputs

- **WHEN** the Kimi kinds reference for `houmao-credential-mgr` is presented to the user
- **THEN** it describes the Kimi credential inputs accepted by the maintained credential add/set surfaces
- **AND THEN** it maps those inputs to credential-manager flag spellings such as `--api-key`, `--model-name`, `--base-url`, `--provider-type`, `--code-base-url`, `--code-oauth-host`, `--oauth-host`, `--disable-telemetry`, `--config-toml`, or `--credential-json`

### Requirement: `houmao-credential-mgr` uses direct command snippets for credential workflows
The packaged `houmao-credential-mgr` skill SHALL document supported credential commands as fenced `bash` snippets.

At minimum, covered credential verbs SHALL include:

- `add`
- `set`
- `login`
- `list`
- `get`
- `rename`
- `remove`

The skill SHALL document project-vs-native-agent lane selection directly and SHALL include tool-specific option shapes for Claude, Codex, and Gemini where a workflow needs credential material flags.

The skill SHALL NOT reference `houmao-mgr internals command-templates show`, `houmao-mgr internals command-templates render`, command-template ids, or template blockers.

#### Scenario: Codex credential add uses direct project command
- **WHEN** a user asks the skill to add project Codex credential `main`
- **THEN** the skill guidance shows a direct `houmao-mgr project credentials codex add --name main ...` command
- **AND THEN** Codex-specific credential material flags are documented in skill guidance rather than loaded from a command-template schema

#### Scenario: Claude login update uses direct login command
- **WHEN** a user asks the skill to update an existing Claude login credential
- **THEN** the skill guidance shows the direct Claude credential login or add command with the explicit update flag when supported
- **AND THEN** omitted login options remain absent from the command snippet

#### Scenario: Native agent-definition lane stays explicit
- **WHEN** a user targets a plain native-agent directory instead of the active project
- **THEN** the skill guidance uses a direct `houmao-mgr internals native-agent credentials <tool> ... --native-agent-root <dir>` command
- **AND THEN** it does not silently switch to `project credentials`

### Requirement: `houmao-credential-mgr` action guidance includes Kimi credential CRUD

The packaged `houmao-credential-mgr` action pages for `list`, `get`, `add`, `set`, `rename`, and `remove` SHALL include Kimi as a supported tool family wherever those pages enumerate supported tools or show tool-specific credential examples.

Kimi `add` and `set` guidance SHALL describe only documented Kimi credential flags and SHALL NOT invent provider-neutral flags that the CLI does not support.

Kimi `login` guidance SHALL state that Kimi does not have a maintained Houmao credential login helper in this change.

#### Scenario: Add guidance offers Kimi credential inputs

- **WHEN** a user asks the installed skill to add a Kimi credential
- **THEN** the `add` action can route to `houmao-mgr project credentials kimi add --name <name>` or `houmao-mgr internals native-agent credentials kimi add --native-agent-root <path> --name <name>`
- **AND THEN** the guidance offers Kimi-specific supported credential inputs rather than Claude, Codex, or Gemini-only options

#### Scenario: Set guidance offers Kimi credential updates

- **WHEN** a user asks the installed skill to update a Kimi credential
- **THEN** the `set` action can route to the Kimi credential set command for the selected target
- **AND THEN** the guidance presents Kimi-specific update flags from the maintained CLI surface

#### Scenario: Login guidance excludes Kimi helper workflow

- **WHEN** a user asks the installed skill to log in to Kimi through Houmao credential helpers
- **THEN** the skill explains that no maintained Kimi credential login helper is available in this change
- **AND THEN** it does not direct the agent to run a Claude, Codex, or Gemini login helper for Kimi

### Requirement: Credential management skill excludes Gemini
The credential management skill SHALL expose actions, kinds, examples, and references only for maintained credential providers and SHALL delete Gemini-only reference pages.

#### Scenario: Credential skill routing has no Gemini target
- **WHEN** an agent reads credential kind or action routing
- **THEN** it can route Claude, Codex, or Kimi credential work
- **AND THEN** no Gemini credential reference is discoverable from the skill
