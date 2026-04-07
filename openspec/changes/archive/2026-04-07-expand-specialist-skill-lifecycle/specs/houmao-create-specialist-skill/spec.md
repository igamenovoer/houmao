## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-create-specialist` system skill
The system SHALL package a Houmao-owned system skill named `houmao-manage-specialist` under the maintained system-skill asset root.

That skill SHALL instruct agents to manage reusable specialists through `houmao-mgr project easy specialist create|list|get|remove` and specialist-scoped runtime actions through `houmao-mgr project easy instance launch|stop` rather than through deprecated or lower-level authoring surfaces.

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `create`,
- `list`,
- `get`,
- `remove`,
- `launch`,
- `stop`.

That packaged skill SHALL treat generic managed-agent lifecycle actions outside specialist-scoped launch and stop as out of scope and SHALL direct users to `houmao-manage-agent-instance` for further agent management after a specialist-backed launch or stop flow.

The create action within that packaged skill SHALL describe the documented project-easy defaults that matter for authoring behavior, including:

- `--credential` defaults to `<specialist-name>-creds`,
- `--system-prompt` and `--system-prompt-file` are optional and mutually exclusive,
- `--no-unattended` opts out of the easy unattended default.

#### Scenario: Installed skill points the agent at specialist management and specialist-scoped lifecycle commands
- **WHEN** an agent opens the installed specialist-management skill
- **THEN** the skill directs the agent to use `houmao-mgr project easy specialist create|list|get|remove` and `houmao-mgr project easy instance launch|stop`
- **AND THEN** it does not redirect the agent to deprecated entrypoints or ad hoc filesystem editing

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-manage-specialist` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `create`, `list`, `get`, `remove`, `launch`, and `stop`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than being flattened into one long entry page

#### Scenario: Installed skill preserves the documented easy-specialist create defaults
- **WHEN** an agent follows the create path inside the installed `houmao-manage-specialist` skill
- **THEN** the skill states that `--credential` defaults to `<specialist-name>-creds`
- **AND THEN** it states that system-prompt input is optional and that `--no-unattended` is the explicit opt-out from the easy unattended default

#### Scenario: Installed skill hands off follow-up lifecycle work after specialist launch or stop
- **WHEN** an agent completes a specialist-backed `launch` or `stop` action through `houmao-manage-specialist`
- **THEN** the skill tells the user that further agent management should go through `houmao-manage-agent-instance`
- **AND THEN** it does not imply that `houmao-manage-specialist` is the canonical surface for generic live managed-agent lifecycle

### Requirement: `houmao-create-specialist` recovers explicit inputs from conversation context and asks before guessing
The packaged `houmao-manage-specialist` skill SHALL tell the agent to recover omitted specialist-management inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess missing required inputs that are not explicit in current or recent conversation context.

At minimum, the skill SHALL require the agent to obtain:

- no specialist name for `list`,
- specialist name for `get`,
- specialist name for `remove`,
- specialist name, tool lane, and enough auth information for `create` unless an existing credential bundle for the intended credential name has already been confirmed,
- specialist name and instance name for `launch`,
- easy-instance name for specialist-scoped `stop`.

When the user omits `--credential` on the create path, the skill MAY rely on the documented CLI default `<specialist-name>-creds` without treating that default as a guess.

When required inputs remain unresolved after checking prompt and recent conversation context, the skill SHALL instruct the agent to ask the user for the missing inputs before proceeding.

When the user explicitly requests `auto credentials`, the skill SHALL treat that as a create-action opt-in auth-discovery mode rather than as a literal CLI flag or replacement credential-bundle name.

The skill SHALL NOT apply credential discovery rules to `list`, `get`, `remove`, `launch`, or `stop`.

#### Scenario: List action does not require a specialist name
- **WHEN** the current prompt asks the agent to list specialists
- **THEN** the skill allows the agent to proceed without asking for a specialist name
- **AND THEN** it does not invent a target specialist just because other actions require one

#### Scenario: Get or remove asks before guessing the target specialist
- **WHEN** the current prompt asks for specialist inspection or removal
- **AND WHEN** the specialist name is not explicit in current or recent conversation context
- **THEN** the skill tells the agent to ask the user for the missing specialist name before proceeding
- **AND THEN** it does not guess which persisted specialist the user intended

#### Scenario: Existing credential bundle makes create auth re-entry unnecessary
- **WHEN** the current prompt or recent conversation establishes the create-action specialist name and tool
- **AND WHEN** the skill confirms that the intended credential bundle already exists for that tool
- **THEN** the skill allows the agent to proceed without asking the user to restate API-key or auth inputs
- **AND THEN** it treats the confirmed credential bundle as satisfying the auth requirement for specialist creation

#### Scenario: Specialist launch asks before guessing the launch target
- **WHEN** the current prompt asks to launch from a specialist
- **AND WHEN** the specialist name or instance name is not explicit in current or recent conversation context
- **THEN** the skill tells the agent to ask the user for the missing launch input before proceeding
- **AND THEN** it does not guess which specialist or instance name to use

#### Scenario: Specialist stop asks before guessing the easy-instance target
- **WHEN** the current prompt asks to stop a specialist-backed instance
- **AND WHEN** the easy-instance name is not explicit in current or recent conversation context
- **THEN** the skill tells the agent to ask the user for the missing easy-instance name before proceeding
- **AND THEN** it does not guess which running instance the user intended

#### Scenario: Non-create lifecycle actions do not trigger auth discovery
- **WHEN** the user asks for `list`, `get`, `remove`, `launch`, or `stop`
- **THEN** the skill does not enter credential discovery or auth-bundle creation flow
- **AND THEN** it keeps create-only auth logic scoped to the create action
