## MODIFIED Requirements

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

The top-level `SKILL.md` SHALL also route explicit Kimi Code login/import requests to local Kimi Code login-handling guidance without adding Kimi to the maintained credential login-helper tool list.

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

#### Scenario: Kimi credential work uses CRUD plus Kimi Code login handling

- **WHEN** an agent reads `houmao-credential-mgr` guidance for tool `kimi`
- **THEN** the skill presents `list`, `get`, `add`, `set`, `rename`, and `remove` as supported credential actions
- **AND THEN** it may route an explicit Kimi Code login/import request to Kimi-specific login-handling guidance that ends in an existing `add` or `set --code-home` import command
- **AND THEN** it does not present a `houmao-mgr project credentials kimi login` or `houmao-mgr internals native-agent credentials kimi login` helper unless a maintained Kimi login helper is added in a later change

## ADDED Requirements

### Requirement: `houmao-credential-mgr` provides Kimi Code login-handling guidance
The packaged `houmao-credential-mgr` skill SHALL include local Kimi Code login-handling guidance for requests to obtain a fresh default Kimi Code OAuth login and import it into Houmao Kimi credential storage.

The guidance SHALL explain that `kimi login` is the Kimi Code CLI OAuth device-code login command and SHALL distinguish it from the Kimi TUI `/login` flow, which can also collect Kimi Platform API keys.

The guidance SHALL tell agents to run `kimi login` in a dedicated tmux session by default, with an isolated temporary `KIMI_CODE_HOME`, when the user asks for a new Kimi Code OAuth credential and the required Houmao credential name and target are known.

The guidance SHALL instruct agents to preserve the current shell's proxy environment in the tmux session by passing set proxy variables explicitly with tmux environment arguments. At minimum, when set in the current environment, the guidance SHALL carry these variables into the tmux session:

- `HTTP_PROXY`
- `HTTPS_PROXY`
- `ALL_PROXY`
- `NO_PROXY`
- `http_proxy`
- `https_proxy`
- `all_proxy`
- `no_proxy`

The guidance SHALL use the existing Kimi credential import surfaces after successful default OAuth login:

- `houmao-mgr project [--project-dir <dir>] credentials kimi add --name <name> --code-home <temp-kimi-home>` for create-only project import,
- `houmao-mgr project [--project-dir <dir>] credentials kimi set --name <name> --code-home <temp-kimi-home>` when the user explicitly intends to update an existing project credential,
- `houmao-mgr internals native-agent credentials kimi add --native-agent-root <path> --name <name> --code-home <temp-kimi-home>` for create-only direct native-agent import,
- `houmao-mgr internals native-agent credentials kimi set --native-agent-root <path> --name <name> --code-home <temp-kimi-home>` when the user explicitly intends to update an existing direct native-agent credential.

The guidance SHALL verify that `<temp-kimi-home>/credentials/kimi-code.json` exists before importing with `--code-home`.

The guidance SHALL preserve and report the temp Kimi Code home path when `kimi login` fails, is cancelled, or does not create the expected default credential file.

The guidance SHALL constrain automatic import guidance to the default Kimi Code OAuth token file shape that Houmao already imports as `credentials/kimi-code.json`. When the user explicitly needs `KIMI_CODE_OAUTH_HOST`, `KIMI_OAUTH_HOST`, or `KIMI_CODE_BASE_URL` for a non-default Kimi Code environment, the guidance SHALL warn that current Houmao `--code-home` import does not preserve arbitrary scoped OAuth token filenames and SHALL ask before proceeding with any lower-level recovery path.

The guidance SHALL NOT print proxy values, raw token JSON, raw API keys, or raw credential-file contents.

The guidance SHALL NOT tell agents to use `--inherit-auth-env` for Kimi proxy preservation.

#### Scenario: Default project Kimi Code OAuth login imports through code-home
- **WHEN** the user asks the installed skill to log in to Kimi Code OAuth for the current project as credential `kimi-coding`
- **AND WHEN** the user has not asked to update an existing credential
- **AND WHEN** tmux is available
- **THEN** the skill directs the agent to run `KIMI_CODE_HOME=<temp-kimi-home> kimi login` in a dedicated tmux session with set proxy variables forwarded
- **AND THEN** after successful login it imports through `houmao-mgr project credentials kimi add --name kimi-coding --code-home <temp-kimi-home>`
- **AND THEN** it does not call or invent `houmao-mgr project credentials kimi login`

#### Scenario: Explicit native Kimi Code OAuth update uses set
- **WHEN** the user asks to replace a Kimi credential under native-agent root `tests/fixtures/plain-agent-def` with a fresh Kimi Code OAuth login
- **THEN** the skill directs the agent to complete `kimi login` with an isolated temporary `KIMI_CODE_HOME`
- **AND THEN** it imports through `houmao-mgr internals native-agent credentials kimi set --native-agent-root tests/fixtures/plain-agent-def --name <name> --code-home <temp-kimi-home>`
- **AND THEN** it does not use create-only `add` for the explicit replacement

#### Scenario: Kimi login temp home is preserved on missing credential file
- **WHEN** `kimi login` exits unsuccessfully or the temp home does not contain `credentials/kimi-code.json`
- **THEN** the skill reports the preserved temporary `KIMI_CODE_HOME` path as recovery context
- **AND THEN** it does not import an incomplete Kimi credential into Houmao storage

#### Scenario: Non-default Kimi Code OAuth endpoints are not overpromised
- **WHEN** the user asks to log in to Kimi Code with explicit `KIMI_CODE_OAUTH_HOST`, `KIMI_OAUTH_HOST`, or `KIMI_CODE_BASE_URL`
- **THEN** the skill warns that Kimi may create a scoped OAuth token filename that current Houmao Kimi `--code-home` import does not preserve
- **AND THEN** it does not promise that the imported credential will work for that scoped environment unless supported import behavior is added by a later change

### Requirement: Kimi credential-kind guidance references Kimi Code login handling
The Kimi credential kinds reference SHALL continue to enumerate the maintained Kimi CRUD input kinds accepted by `credentials kimi add` and `credentials kimi set`.

The Kimi credential kinds reference SHALL describe default Kimi Code OAuth login as a workflow that creates a Kimi Code home and then imports it with `--code-home`, not as a direct credential value pasted into `add`.

The Kimi credential kinds reference SHALL link or point to the Kimi Code login-handling guidance when the user wants a fresh default Kimi Code OAuth login.

The Kimi credential kinds reference SHALL keep Kimi Platform API key handling separate from `kimi login` and SHALL map API-key material to the existing `--api-key` and related model/provider flags.

#### Scenario: Kimi reference points fresh OAuth login to login handling
- **WHEN** an agent reads the Kimi credential kinds reference for a user who wants a fresh Kimi Code OAuth login
- **THEN** the reference directs the agent to the Kimi Code login-handling guidance and the `--code-home` import path
- **AND THEN** it does not claim that `credentials kimi add` can itself perform the device-code login

#### Scenario: Kimi API key remains a CRUD input
- **WHEN** a user provides a Kimi Platform or compatible provider API key
- **THEN** the Kimi credential kinds reference maps that material to `--api-key` and optional Kimi model/provider modifiers
- **AND THEN** it does not route API-key storage through `kimi login`
