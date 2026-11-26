# Spec Delta

## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-credential-mgr` system skill

The system SHALL package a Houmao-owned system skill named `houmao-credential-mgr` under the maintained system-skill asset root.

#### Scenario: Packaged credential guidance routes operators to supported commands

- **GIVEN** an agent consults `houmao-credential-mgr` to manage provider credentials
- **THEN** the packaged guidance identifies the supported operations, tool families, and command surfaces

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
- `dsh`
- `kimi`

That skill SHALL instruct agents to use credential login helpers only for tool families with maintained login-helper support:

- `houmao-mgr project credentials <login-tool> login`
- `houmao-mgr internals native-agent credentials <login-tool> login --native-agent-root <path> --name <name>`

The packaged skill SHALL scope credential login-helper guidance to:

- `claude`
- `codex`

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
- `agents global|single|self|external ...`
- `internals native-agent tools <tool> setups ...`
- `internals native-agent roles ...`
- `project mailbox ...`, `mailbox cleanup ...`, `agents single ... cleanup ...`, and `admin cleanup runtime ...`
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

### Requirement: Credential manager covers DSH credential CRUD and Kimi native config updates
`houmao-credential-mgr` SHALL add `dsh` (`DeepSeek Harness`) across `SKILL-MAIN.md` and `commands/{list,get,add,set,rename,remove}.md`, bundle `references/dsh-credential-kinds.md` (`--adapter [deepseek|pi-ai]`, `--api-key`, `--base-url`, `--api-key-env`, `--base-url-env`), and update `references/kimi-credential-kinds.md` for Kimi `config.toml` and `support_efforts`.

#### Scenario: Operator configures DSH credentials or Kimi support efforts
- **WHEN** an admin adds or inspects a `dsh` credential or configures a Kimi model with `support_efforts`
- **THEN** `houmao-credential-mgr` routes `dsh` CRUD to `project credentials dsh` or `internals native-agent credentials dsh` using `references/dsh-credential-kinds.md`
- **AND THEN** `references/kimi-credential-kinds.md` documents native `config.toml` and `support_efforts` behavior without inventing a `kimi login` CLI helper

### Requirement: Credential manager fixes workflow step numbering and streamlines SKILL-MAIN.md
`houmao-credential-mgr/SKILL-MAIN.md` SHALL fix the step `8 -> 10` numbering gap so `## Workflow` steps are sequential, convert the `## Subcommands` bullet list into a clean table linking `commands/*.md`, and remove duplicated launcher, Missing-Input, `houmao-cli`, and Scope/Routing boilerplate (~95 lines).

#### Scenario: Entrypoint workflow numbering and subcommand table conform to style rules
- **WHEN** a reviewer inspects `houmao-credential-mgr/SKILL-MAIN.md`
- **THEN** `## Workflow` numbers every step sequentially (`1..N`) with no skipped step
- **AND THEN** `## Subcommands` uses a plain `| Subcommand | Use For | Detail |` table without cross-skill boilerplate

### Requirement: Credential manager preserves dual lanes, secret redaction, and rename semantics
`houmao-credential-mgr` SHALL preserve admin-only `## Actor Frame Gate`, dual lanes (`project credentials` vs `internals native-agent credentials`), maintained `login` scope (`claude`, `codex`), non-disclosure of secret values or raw files, and lane-specific rename semantics.

#### Scenario: Credential inspection and rename preserve security and lane contracts
- **WHEN** an admin runs `get` or `rename` on a credential
- **THEN** `get` reports presence and redacted metadata without printing raw secret env values or auth file contents
- **AND THEN** project-backed `rename` updates display metadata while direct-dir `rename` updates `presets/*.yaml` and `launch-profiles/*.yaml`, keeping `--auth` profile overrides in `houmao-agent-definition`
