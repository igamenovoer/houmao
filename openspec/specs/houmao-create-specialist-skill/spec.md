## Purpose
Define the packaged specialist-management system skill contract for routed specialist actions, launcher selection, and explicit input recovery.
## Requirements
### Requirement: Houmao provides a packaged `houmao-create-specialist` system skill
The system SHALL package a Houmao-owned system skill named `houmao-specialist-mgr` under the maintained system-skill asset root.

That skill SHALL instruct agents to manage reusable specialists through `houmao-mgr project easy specialist create|list|get|remove` and specialist-scoped runtime actions through `houmao-mgr project easy instance launch|stop` rather than through deprecated or lower-level authoring surfaces.

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `create`,
- `list`,
- `get`,
- `remove`,
- `launch`,
- `stop`.

That packaged skill SHALL treat generic managed-agent lifecycle actions outside specialist-scoped launch and stop as out of scope and SHALL direct users to `houmao-agent-instance` for further agent management after a specialist-backed launch or stop flow.

The create action within that packaged skill SHALL describe the documented project-easy defaults that matter for authoring behavior, including:

- `--credential` defaults to `<specialist-name>-creds`,
- `--system-prompt` and `--system-prompt-file` are optional and mutually exclusive,
- `--no-unattended` opts out of the easy unattended default.

#### Scenario: Installed skill points the agent at specialist management and specialist-scoped lifecycle commands
- **WHEN** an agent opens the installed specialist-management skill
- **THEN** the skill directs the agent to use `houmao-mgr project easy specialist create|list|get|remove` and `houmao-mgr project easy instance launch|stop`
- **AND THEN** it does not redirect the agent to deprecated entrypoints or ad hoc filesystem editing

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-specialist-mgr` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `create`, `list`, `get`, `remove`, `launch`, and `stop`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than being flattened into one long entry page

#### Scenario: Installed skill preserves the documented easy-specialist create defaults
- **WHEN** an agent follows the create path inside the installed `houmao-specialist-mgr` skill
- **THEN** the skill states that `--credential` defaults to `<specialist-name>-creds`
- **AND THEN** it states that system-prompt input is optional and that `--no-unattended` is the explicit opt-out from the easy unattended default

#### Scenario: Installed skill hands off follow-up lifecycle work after specialist launch or stop
- **WHEN** an agent completes a specialist-backed `launch` or `stop` action through `houmao-specialist-mgr`
- **THEN** the skill tells the user that further agent management should go through `houmao-agent-instance`
- **AND THEN** it does not imply that `houmao-specialist-mgr` is the canonical surface for generic live managed-agent lifecycle

### Requirement: `houmao-create-specialist` treats credential defaults as display-name defaults only
The create action within the packaged `houmao-specialist-mgr` skill SHALL treat `--credential` as the operator-facing auth display name used for selection or creation rather than as an implied storage-path key.

When the user omits `--credential`, the skill MAY continue using `<specialist-name>-creds` as the documented display-name default without implying that the resulting auth profile must use the same basename for managed content or compatibility projection storage.

The create guidance SHALL NOT describe auth rename, auth storage paths, or auth directory basenames as something the operator must coordinate manually for specialist creation.

#### Scenario: Installed skill presents the default credential as a display-name default
- **WHEN** an agent follows the create path inside the installed `houmao-specialist-mgr` skill
- **THEN** the skill states that `--credential` defaults to `<specialist-name>-creds`
- **AND THEN** it does not imply that the auth profile's storage path basename must equal that display name

#### Scenario: Existing auth profile display name still satisfies specialist create
- **WHEN** the current prompt or recent conversation establishes specialist name and tool
- **AND WHEN** the skill confirms that an auth profile with the intended display name already exists for that tool
- **THEN** the skill allows specialist creation to proceed without re-entering auth inputs
- **AND THEN** it does not require the agent to inspect or reason about the auth profile's opaque storage path

### Requirement: `houmao-create-specialist` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-specialist-mgr` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace using this default order unless the user explicitly requests a different launcher:

1. resolve `houmao-mgr` with `command -v houmao-mgr` and use the command found on `PATH`,
2. if that lookup fails, use the uv-managed fallback `uv tool run --from houmao houmao-mgr`,
3. if the PATH lookup and uv-managed fallback do not satisfy the turn, choose an appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`.

The skill SHALL treat the `command -v houmao-mgr` result as the ordinary first-choice launcher for the current turn.

The skill SHALL treat the uv-managed fallback as the ordinary non-PATH fallback because Houmao's documented installation path uses uv tools.

The skill SHALL only probe development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` after PATH resolution and uv fallback do not satisfy the turn, unless the user explicitly asks for a development launcher.

The skill SHALL honor an explicit user instruction to use a specific launcher family even when a higher-priority default launcher is available.

The resolved launcher SHALL be reused for any routed `project easy specialist` action selected through the packaged skill.

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

### Requirement: `houmao-create-specialist` recovers explicit inputs from conversation context and asks before guessing
The packaged `houmao-specialist-mgr` skill SHALL tell the agent to recover omitted specialist-management inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

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

The skill SHALL NOT apply credential discovery rules to `list`, `get`, or `remove`.

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

### Requirement: `houmao-create-specialist` describes Claude credential lanes separately from optional state templates
The create action within the packaged `houmao-specialist-mgr` skill SHALL describe Claude credential-providing methods separately from optional Claude runtime-state template inputs.

When the create action lists Claude-specific create inputs or discovery outcomes, it SHALL treat:

- supported Claude credential or login-state lanes as Claude auth methods,
- `claude_state.template.json` only as optional reusable bootstrap state for runtime preparation.

The create action SHALL NOT present `claude_state.template.json` as one of the ways to provide Claude credentials.

#### Scenario: Installed skill does not present the Claude state template as credentials
- **WHEN** an agent reads the create guidance inside the installed `houmao-specialist-mgr` skill
- **THEN** the skill distinguishes Claude credential-providing methods from the optional Claude state-template input
- **AND THEN** it does not describe `claude_state.template.json` as a Claude credential lane

### Requirement: `houmao-create-specialist` explains filesystem mailbox behavior on specialist-backed easy launch
When the packaged `houmao-specialist-mgr` skill describes `project easy instance launch` with filesystem mailbox support, the launch guidance SHALL distinguish launch-time mailbox flags from profile-create declarative mailbox fields.

At minimum, that launch guidance SHALL state that `project easy instance launch` does not accept profile-create declarative mailbox fields such as `--mail-address`, `--mail-principal-id`, `--mail-base-url`, `--mail-jmap-url`, or `--mail-management-url`.

The launch guidance SHALL state that the supported launch-time filesystem mailbox inputs are `--mail-transport filesystem`, `--mail-root`, and optional `--mail-account-dir`.

The launch guidance SHALL state that the managed-agent instance name seeds the ordinary filesystem mailbox identity for launch-owned mailbox bootstrap when mailbox support is enabled and no explicit private mailbox directory override changes the storage path.

The launch guidance SHALL explain that `--mail-account-dir` is a private filesystem mailbox directory that is symlinked into the shared mailbox root and therefore MUST live outside that shared root.

The launch guidance SHALL warn that manual preregistration of the same address under the same mailbox root can collide with the launch's safe mailbox bootstrap for that instance.

#### Scenario: Specialist launch guidance excludes profile-only mailbox fields
- **WHEN** an agent reads the specialist-manager launch action for mailbox-enabled `project easy instance launch`
- **THEN** the skill states that launch-time filesystem mailbox support uses only the documented launch flags
- **AND THEN** it does not present `--mail-address` or `--mail-principal-id` as supported `project easy instance launch` flags

#### Scenario: Specialist launch guidance explains private mailbox directory placement
- **WHEN** an agent reads the specialist-manager launch action for `--mail-account-dir`
- **THEN** the skill explains that the path is a private mailbox directory symlinked into the shared root
- **AND THEN** it states that the private mailbox directory must live outside the shared mailbox root

#### Scenario: Specialist launch guidance warns about preregistering the same address
- **WHEN** an agent reads the specialist-manager launch action for launch-owned filesystem mailbox binding
- **AND WHEN** the intended mailbox address follows the ordinary managed-agent identity pattern for the same mailbox root
- **THEN** the skill warns that preregistering that same address can make safe launch bootstrap fail
- **AND THEN** it tells the reader to let launch own that address unless they are intentionally using a different manual-registration or late-binding lane

### Requirement: `houmao-specialist-mgr` routes easy-profile editing commands
The packaged `houmao-specialist-mgr` skill SHALL treat specialist-backed easy-profile editing as part of its easy-profile authoring responsibility.

When a user asks to update one existing easy profile's stored launch defaults, the skill SHALL route to `houmao-mgr project easy profile set --name <profile> ...`.

When a user asks to replace one existing easy profile definition, the skill SHALL route to `houmao-mgr project easy profile create --name <profile> --specialist <specialist> ... --yes` after identifying the replacement intent.

The skill SHALL NOT route ordinary easy-profile stored-default edits through manual remove/recreate.

#### Scenario: Skill routes easy-profile patch request to set
- **WHEN** a user asks an agent using `houmao-specialist-mgr` to change the workdir on easy profile `alice`
- **THEN** the skill guidance routes that request through `project easy profile set --name alice --workdir <path>`
- **AND THEN** it does not instruct the agent to remove and recreate `alice`

#### Scenario: Skill distinguishes replacement from patch
- **WHEN** a user asks an agent using `houmao-specialist-mgr` to rebuild easy profile `alice` over a different specialist
- **THEN** the skill guidance treats that as replacement
- **AND THEN** it routes through `project easy profile create --name alice --specialist <specialist> --yes`

### Requirement: `houmao-specialist-mgr` routes specialist update requests
The packaged `houmao-specialist-mgr` skill SHALL instruct agents to route existing-specialist update requests through `houmao-mgr project easy specialist set --name <specialist> ...`.

The top-level skill router SHALL include specialist update as an easy-workflow action and SHALL distinguish it from specialist creation, same-name specialist replacement, easy-profile update, and easy-instance runtime work.

The specialist update guidance SHALL require the specialist name and at least one explicit update or clear option before running the command.

The specialist update guidance SHALL tell agents that omitted fields are preserved and that already-running managed agents are not mutated in place.

#### Scenario: Installed skill routes specialist skill edits to set
- **WHEN** a user asks an agent to add or remove a skill on an existing specialist
- **THEN** the installed `houmao-specialist-mgr` skill routes the agent to `project easy specialist set`
- **AND THEN** it does not instruct the agent to remove and recreate the specialist for that ordinary edit

#### Scenario: Installed skill asks before running an empty specialist update
- **WHEN** a user asks to update specialist `researcher` but does not state any concrete update field
- **THEN** the installed `houmao-specialist-mgr` skill tells the agent to ask for the missing update details
- **AND THEN** it does not run `project easy specialist set --name researcher` without an update or clear flag

#### Scenario: Installed skill distinguishes profile update from specialist update
- **WHEN** a user asks to update a reusable launch default on an easy profile
- **THEN** the installed `houmao-specialist-mgr` skill routes the agent to `project easy profile set`
- **AND THEN** it does not use `project easy specialist set` for profile-owned birth-time defaults

### Requirement: `houmao-specialist-mgr` preserves foreground-first launch-time gateway posture
The packaged `houmao-specialist-mgr` launch guidance SHALL explain that `project easy instance launch` enables launch-time gateway auto-attach by default unless `--no-gateway` or stored profile posture disables it.

The launch guidance SHALL state that default launch-time gateway auto-attach uses foreground same-session auxiliary-window execution when supported, and that detached background gateway execution is a separate gateway-sidecar posture.

The launch guidance SHALL NOT include `--gateway-background` in command examples or optional flag recommendations unless the current user prompt or recent conversation explicitly asks for background or detached gateway execution.

The launch guidance SHALL distinguish managed-agent `--headless` or `--no-headless` posture from gateway sidecar foreground or background execution, including for Gemini specialists whose managed-agent launch must remain headless.

#### Scenario: Specialist-backed launch keeps default foreground gateway posture
- **WHEN** an agent follows `houmao-specialist-mgr` guidance to launch an easy instance from an existing specialist
- **AND WHEN** the user has not explicitly requested detached background gateway execution
- **THEN** the guidance directs the agent to omit `--gateway-background`
- **AND THEN** it describes the resulting launch-time gateway auto-attach as foreground same-session auxiliary-window execution when supported

#### Scenario: Profile-backed launch keeps stored posture without inventing background mode
- **WHEN** an agent follows `houmao-specialist-mgr` guidance to launch through an easy profile
- **AND WHEN** the selected profile does not explicitly store or imply detached background gateway execution
- **THEN** the guidance does not add a background gateway flag as a one-shot override
- **AND THEN** it leaves profile-backed gateway posture to the stored profile defaults plus explicit user-provided CLI overrides

#### Scenario: Headless managed-agent launch does not imply background gateway execution
- **WHEN** the selected specialist or profile source requires or requests `--headless`
- **AND WHEN** the user has not explicitly requested background gateway execution
- **THEN** the guidance treats the managed-agent headless posture as separate from the gateway sidecar execution mode
- **AND THEN** it does not add `--gateway-background` merely because the managed-agent launch is headless

#### Scenario: Background gateway launch requires explicit user intent
- **WHEN** the user explicitly asks for background gateway execution, detached gateway process execution, or avoiding a gateway tmux window during easy launch
- **THEN** the guidance may include `--gateway-background` when the command surface supports it
- **AND THEN** it describes that flag as an explicit override rather than the normal launch posture

