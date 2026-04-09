## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-credential-mgr` system skill
The system SHALL package a Houmao-owned system skill named `houmao-credential-mgr` under the maintained system-skill asset root.

That skill SHALL instruct agents to manage project-local auth profiles through these supported commands:

- `houmao-mgr project agents tools <tool> auth list`
- `houmao-mgr project agents tools <tool> auth get`
- `houmao-mgr project agents tools <tool> auth add`
- `houmao-mgr project agents tools <tool> auth set`
- `houmao-mgr project agents tools <tool> auth rename`
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
- `rename`
- `remove`

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `project easy specialist create|list|get|remove`
- `project easy instance launch|list|get|stop`
- `agents launch|join|list|stop|cleanup`
- `project agents tools <tool> setups ...`
- `project agents roles ...`
- `project mailbox ...`, `agents cleanup mailbox`, and `admin cleanup runtime ...`
- direct hand-editing of auth-bundle files under `.houmao/agents/tools/`

#### Scenario: Installed skill points the agent at project-local auth-profile commands
- **WHEN** an agent opens the installed `houmao-credential-mgr` skill
- **THEN** the skill directs the agent to use the supported `project agents tools <tool> auth ...` command surface for auth-profile work
- **AND THEN** it does not redirect the agent to ad hoc filesystem editing or unrelated runtime-control surfaces

#### Scenario: Installed skill routes to action-specific local guidance including rename
- **WHEN** an agent reads the installed `houmao-credential-mgr` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `list`, `get`, `add`, `set`, `rename`, and `remove`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than one flattened entry page

### Requirement: `houmao-credential-mgr` selects the correct auth-bundle action and asks before guessing
The packaged `houmao-credential-mgr` skill SHALL tell the agent to recover omitted auth-profile inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess missing required inputs that are not explicit in current or recent conversation context.

The skill SHALL select commands by requested action:

- use `auth list` for listing auth display names for one supported tool,
- use `auth get --name <name>` for safe redacted inspection of one existing auth profile,
- use `auth add --name <name>` for creating one new auth profile,
- use `auth set --name <name>` for updating one existing auth profile,
- use `auth rename --name <name> --to <new-name>` for renaming one existing auth profile,
- use `auth remove --name <name>` for removing one existing auth profile.

At minimum, the skill SHALL require the agent to obtain:

- for `list`: the tool family,
- for `get`: the tool family and auth display name,
- for `remove`: the tool family and auth display name,
- for `add`: the tool family, auth display name, and enough supported auth input for that selected tool,
- for `set`: the tool family, auth display name, and at least one supported change for that selected tool,
- for `rename`: the tool family, current auth display name, and target display name.

When the user asks to update credentials, the skill SHALL map that request to the `set` action rather than guessing another verb.

For mutating actions, the skill SHALL use only documented per-tool auth flags and SHALL NOT invent unsupported file flags, clear-style flags, or provider-neutral abstractions that the selected CLI surface does not actually support.

For `get`, the skill SHALL rely on the command's structured redacted output and SHALL NOT print secret env values or raw auth-file contents by bypassing that safe inspection surface.

Unless the user explicitly asks for a narrower path-based inspection as part of the current request, the skill SHALL NOT scan environment variables, home directories, repo-local tool homes, or unrelated filesystem locations to infer missing auth inputs for `add` or `set`.

#### Scenario: List action does not require an auth display name
- **WHEN** the current prompt asks the agent to list project-local credentials for one supported tool
- **THEN** the skill allows the agent to proceed without asking for an auth display name
- **AND THEN** it does not invent a target auth profile just because other actions require one

#### Scenario: Get or remove asks before guessing the target auth profile
- **WHEN** the current prompt asks for auth-profile inspection or removal
- **AND WHEN** the tool or auth display name is not explicit in current or recent conversation context
- **THEN** the skill tells the agent to ask the user for the missing tool or auth display name before proceeding
- **AND THEN** it does not guess which stored auth profile the user intended

#### Scenario: Rename requires both the current and target names
- **WHEN** the current prompt asks the agent to rename one auth profile
- **AND WHEN** the tool, current auth display name, or target display name is not explicit in current or recent conversation context
- **THEN** the skill tells the agent to ask the user for the missing rename input before proceeding
- **AND THEN** it does not guess either side of the rename

#### Scenario: Inspecting one auth profile stays redacted
- **WHEN** the current prompt asks the agent to inspect one existing auth profile
- **THEN** the skill uses the structured `auth get` output as the inspection contract
- **AND THEN** it reports presence and non-secret metadata without dumping raw secret values or raw auth-file contents
