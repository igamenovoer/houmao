# houmao-agent-gateway-skill Specification

## Purpose
TBD - created by archiving change add-houmao-agent-gateway-skill. Update Purpose after archive.
## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-gateway` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-gateway` under the maintained system-skill asset root.

That skill SHALL instruct agents and operators to handle gateway-specific work through these supported surfaces:

- `houmao-mgr agents gateway attach`
- `houmao-mgr agents gateway detach`
- `houmao-mgr agents gateway status`
- `houmao-mgr agents gateway prompt|interrupt`
- `houmao-mgr agents gateway send-keys`
- `houmao-mgr agents gateway tui state|history|watch|note-prompt`
- `houmao-mgr agents gateway reminders list|get|create|set|remove`
- `houmao-mgr agents gateway mail-notifier status|enable|disable`
- managed-agent HTTP routes under `/houmao/agents/{agent_ref}/gateway...`, including gateway reminder routes when the task is operating through pair-managed authority
- direct live gateway HTTP only when the exact live `{gateway.base_url}` is already available and the task genuinely needs a gateway-only surface such as `/v1/status`, `/v1/reminders`, or `/v1/mail-notifier`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `lifecycle`
- `discover`
- `gateway-services`
- `reminders`
- `mail-notifier`

That packaged skill SHALL remain the canonical Houmao-owned skill for gateway-specific lifecycle, discovery, gateway-only control, and reminder work whether the caller is another agent with an installed Houmao skill home or an external operator standing outside the managed session.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `agents launch|join|stop|relaunch|cleanup`
- `project easy specialist create|list|get|remove`
- ordinary prompt or mailbox work that is already satisfied by `houmao-agent-messaging` and the mailbox skills
- mailbox transport-specific filesystem or Stalwart internals
- inventing new `houmao-mgr`, managed-agent API, or direct gateway routes that the current implementation does not expose

#### Scenario: Installed skill points the caller at the supported gateway surfaces
- **WHEN** an agent or operator opens the installed `houmao-agent-gateway` skill
- **THEN** the skill directs the caller to the supported gateway lifecycle, reminder, notifier, and gateway-only control surfaces
- **AND THEN** it does not redirect the caller to unrelated live-agent lifecycle, ordinary messaging, or transport-local mailbox repair work

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-agent-gateway` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for lifecycle, discovery, gateway-only services, reminders, and notifier guidance
- **AND THEN** the detailed workflow lives in local action-specific documents rather than in one flattened entry page

#### Scenario: Installed skill keeps non-gateway concerns out of scope
- **WHEN** an agent reads the installed `houmao-agent-gateway` skill
- **THEN** the skill marks ordinary prompt/mail flows, transport-specific mailbox internals, and unrelated live-agent lifecycle work as outside the packaged skill scope
- **AND THEN** it does not present `houmao-agent-gateway` as the generic replacement for `houmao-agent-instance`, `houmao-agent-messaging`, or the mailbox skills

### Requirement: `houmao-agent-gateway` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-agent-gateway` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace using this default order unless the user explicitly requests a different launcher:

1. resolve `houmao-mgr` with `command -v houmao-mgr` and use the command found on `PATH`,
2. if that lookup fails, use the uv-managed fallback `uv tool run --from houmao houmao-mgr`,
3. if the PATH lookup and uv-managed fallback do not satisfy the turn, choose an appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`.

The skill SHALL treat the `command -v houmao-mgr` result as the ordinary first-choice launcher for the current turn.

The skill SHALL treat the uv-managed fallback as the ordinary non-PATH fallback because Houmao's documented installation path uses uv tools.

The skill SHALL only probe development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` after PATH resolution and uv fallback do not satisfy the turn, unless the user explicitly asks for a development launcher.

The skill SHALL honor an explicit user instruction to use a specific launcher family even when a higher-priority default launcher is available.

The resolved launcher SHALL be reused for any routed gateway action selected through the packaged skill.

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

### Requirement: `houmao-agent-gateway` uses the supported discovery contract for current-session, live-binding, and mailbox-gateway work
The packaged `houmao-agent-gateway` skill SHALL tell the caller to recover omitted target selectors from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess a missing required target, live gateway base URL, or discovery lane that is not explicit in current or recent conversation context.

For current-session lifecycle work inside the owning managed tmux session, the skill SHALL describe manifest-first targeting through:

- `HOUMAO_MANIFEST_PATH` when present and valid, then
- `HOUMAO_AGENT_ID` plus fresh shared-registry resolution when that manifest pointer is missing or stale.

For live gateway binding discovery, the skill SHALL describe `HOUMAO_AGENT_GATEWAY_HOST`, `HOUMAO_AGENT_GATEWAY_PORT`, `HOUMAO_GATEWAY_STATE_PATH`, and `HOUMAO_GATEWAY_PROTOCOL_VERSION` as the live-binding publication surface when a gateway is already attached.

For mailbox-related gateway work that needs the exact shared `/v1/mail/*` endpoint, the skill SHALL direct the caller to `houmao-mgr agents mail resolve-live` or `GET /houmao/agents/{agent_ref}/mail/resolve-live` and SHALL use the returned `gateway.base_url` when it exists.

The skill SHALL NOT describe retired `HOUMAO_GATEWAY_ATTACH_PATH` or `HOUMAO_GATEWAY_ROOT` as the supported current-session attach contract.

The skill SHALL NOT guess a direct gateway host or port when the exact live `gateway.base_url` is unavailable.

#### Scenario: Current-session lifecycle discovery stays manifest-first
- **WHEN** an attached agent needs to resolve its own managed-agent gateway context from inside the owning tmux session
- **THEN** the skill directs that agent to the manifest-first `HOUMAO_MANIFEST_PATH` then `HOUMAO_AGENT_ID` discovery contract
- **AND THEN** it does not present retired attach-path env vars as the authoritative current-session attach workflow

#### Scenario: Mailbox-related gateway work uses the mailbox live resolver
- **WHEN** the gateway task needs the exact current shared mailbox gateway endpoint
- **THEN** the skill directs the caller to `houmao-mgr agents mail resolve-live` or the managed-agent `mail/resolve-live` route
- **AND THEN** it does not teach the caller to derive that endpoint by scraping live gateway env vars or guessing a loopback port

#### Scenario: Missing live gateway URL requires supported discovery or a higher-level path
- **WHEN** the requested gateway task would require direct live gateway HTTP
- **AND WHEN** the current context does not provide an exact live `gateway.base_url`
- **THEN** the skill does not guess a gateway host or port
- **AND THEN** it instead directs the caller to a supported higher-level `houmao-mgr agents gateway ...` or `/houmao/agents/{agent_ref}/gateway...` surface when one exists

### Requirement: `houmao-agent-gateway` routes by gateway-specific intent and keeps ordinary messaging on the existing skills
The packaged `houmao-agent-gateway` skill SHALL select commands by gateway-specific intent:

- use `houmao-mgr agents gateway attach|detach|status` or `/houmao/agents/{agent_ref}/gateway...` for gateway lifecycle and summary state,
- use `houmao-mgr agents gateway mail-notifier ...` or `/houmao/agents/{agent_ref}/gateway/mail-notifier` for unread-mail notifier control,
- use `houmao-mgr agents gateway reminders list|get|create|set|remove` or `/houmao/agents/{agent_ref}/gateway/reminders...` for reminder creation, inspection, update, and cancellation,
- use direct `{gateway.base_url}/v1/reminders...` only when the task genuinely requires the low-level live reminder HTTP contract and the exact live base URL is already available from supported discovery,
- treat reminder delivery through the supported reminder surfaces as supporting both semantic `prompt` reminders and raw `send_keys` reminders,
- use direct `{gateway.base_url}/v1/...` only when the task genuinely requires a gateway-only lower-level surface and the exact live base URL is already available from supported discovery.

The packaged `houmao-agent-gateway` skill SHALL delegate ordinary prompt turns, mailbox routing, ordinary mailbox work, or transport-specific mailbox work to:

- `houmao-agent-messaging`
- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`

The skill SHALL prefer the managed-agent seam first when it already satisfies the current task and SHALL treat direct gateway listener URLs as the lower-level gateway-only path.

#### Scenario: Reminders use the native gateway reminder surfaces when available
- **WHEN** the user asks to create, inspect, update, or cancel live gateway reminders
- **THEN** the skill directs the caller to `houmao-mgr agents gateway reminders ...` or the matching `/houmao/agents/{agent_ref}/gateway/reminders...` projection when pair-managed authority is in use
- **AND THEN** it does not misdescribe reminders as an HTTP-only workflow when the supported higher-level reminder surfaces already exist

#### Scenario: Direct live reminder HTTP stays the lower-level contract
- **WHEN** the user asks to debug or inspect the exact live reminder HTTP contract
- **AND WHEN** the exact current `gateway.base_url` is already available from supported discovery
- **THEN** the skill may direct the caller to the live `{gateway.base_url}/v1/reminders...` route family
- **AND THEN** it keeps that direct route family positioned as the lower-level contract rather than the first-choice operator surface

#### Scenario: Ordinary prompt or mailbox work delegates away from the gateway skill
- **WHEN** the task is one normal prompt turn, one transport-neutral interrupt, or mailbox work rather than gateway lifecycle or gateway-only service control
- **THEN** the skill directs the caller to `houmao-agent-messaging` and the current mailbox skills instead of taking that work itself
- **AND THEN** it does not present the gateway skill as the primary ordinary communication surface

### Requirement: `houmao-agent-gateway` describes reminders and mail-notifier honestly
The packaged `houmao-agent-gateway` skill SHALL describe `/v1/reminders` as the supported gateway-owned live reminder surface for one attached gateway.

The skill SHALL state that reminder records are live-gateway in-memory state, are lost on gateway shutdown or restart, and are not a durable unfinished-job queue.

The skill SHALL state that the reminder with the smallest ranking value is the effective reminder and that a paused effective reminder still blocks lower-ranked reminders.

The skill SHALL explain that reminders support two delivery forms:

- semantic `prompt`
- raw `send_keys`

For `send_keys` reminders, the skill SHALL explain:

- `send_keys.sequence` uses exact raw control-input `<[key-name]>` semantics,
- `title` remains reminder metadata and is not terminal input,
- `ensure_enter` defaults to `true`,
- `ensure_enter=false` is the correct choice for pure special-key reminders such as `<[Escape]>`,
- unsupported gateway backends reject `send_keys` reminders explicitly rather than silently downgrading them to prompt text.

The skill SHALL describe `mail-notifier` as unread-mail reminder control for mailbox-enabled sessions and SHALL NOT present it as a general-purpose reminder service for arbitrary unfinished work.

The skill SHALL NOT describe reminders or mail-notifier as durable queued work that survives gateway restart.

#### Scenario: Reminder guidance states the in-memory lifetime and ranking boundary clearly
- **WHEN** an attached agent or operator reads the reminder guidance in the packaged gateway skill
- **THEN** the skill states that reminders are process-local live-gateway state and that the smallest ranking is effective
- **AND THEN** it does not claim that reminder state survives gateway stop or restart

#### Scenario: Send-keys reminder guidance explains ensure-enter default and opt-out
- **WHEN** an attached agent or operator reads the send-keys reminder guidance in the packaged gateway skill
- **THEN** the skill explains that `ensure_enter` defaults to `true`
- **AND THEN** it also explains that pure special-key reminders should set `ensure_enter=false`

#### Scenario: Mail-notifier guidance stays mail-specific
- **WHEN** a caller reads the notifier guidance in the packaged gateway skill
- **THEN** the skill presents `mail-notifier` as unread-mail reminder control through the gateway mailbox facade
- **AND THEN** it does not describe notifier control as the generic answer for arbitrary unfinished-job persistence

### Requirement: `houmao-agent-gateway` delegates generic managed-agent inspection to `houmao-agent-inspect`
The packaged `houmao-agent-gateway` skill SHALL treat generic requests to inspect managed-agent liveness, tmux backing, mailbox posture, runtime artifacts, or non-gateway logs as outside its primary ownership unless that inspection is specifically about gateway lifecycle, gateway-only control, reminder state, or mail-notifier state.

For those generic managed-agent inspection requests, the packaged skill SHALL direct the caller to `houmao-agent-inspect`.

The packaged skill MAY continue using gateway status and gateway-owned TUI tracker surfaces when the inspection target is explicitly gateway-specific.

#### Scenario: Generic managed-agent inspection routes to the inspect skill
- **WHEN** a caller asks the gateway skill to inspect a managed agent broadly rather than to inspect the gateway lifecycle or gateway-only services specifically
- **THEN** the skill directs the caller to `houmao-agent-inspect`
- **AND THEN** it does not present the gateway skill as the canonical owner of generic managed-agent inspection

#### Scenario: Gateway-specific inspection remains on the gateway skill
- **WHEN** a caller asks to inspect live gateway status, raw gateway-owned TUI tracker state, reminder state, or notifier state
- **THEN** the skill continues directing the caller to the supported gateway surfaces
- **AND THEN** it does not require a handoff to `houmao-agent-inspect` for that gateway-specific inspection work

### Requirement: `houmao-agent-gateway` teaches foreground-first gateway attach posture
The packaged `houmao-agent-gateway` lifecycle guidance SHALL present `houmao-mgr agents gateway attach` without `--background` as the first-choice command shape for tmux-backed managed sessions.

The lifecycle guidance SHALL state that foreground gateway attach uses a same-session auxiliary tmux window when supported, leaving the managed-agent surface on tmux window `0` and using a non-zero gateway tmux window for the live sidecar.

The lifecycle guidance SHALL state that `--background` requests detached gateway process execution and SHALL only be used when the current user prompt or recent conversation explicitly asks for background or detached gateway execution.

The lifecycle guidance SHALL tell agents to report foreground execution metadata returned by status, including `execution_mode` and `gateway_tmux_window_index` when present, instead of inferring gateway topology from tmux window names or ordering.

#### Scenario: Default attach uses foreground command shape
- **WHEN** an agent follows `houmao-agent-gateway` lifecycle guidance to attach a gateway to a tmux-backed managed session
- **AND WHEN** the user has not explicitly requested detached background gateway execution
- **THEN** the guidance directs the agent to use `houmao-mgr agents gateway attach` without `--background`
- **AND THEN** it describes that as the foreground same-session auxiliary-window attach path when supported

#### Scenario: Background attach requires explicit user intent
- **WHEN** an agent follows `houmao-agent-gateway` lifecycle guidance
- **AND WHEN** the user explicitly asks for background gateway execution, detached gateway process execution, or avoiding a gateway tmux window
- **THEN** the guidance may direct the agent to use `houmao-mgr agents gateway attach --background`
- **AND THEN** it does not present `--background` as the default attach posture

#### Scenario: Foreground metadata is reported instead of guessed
- **WHEN** a foreground gateway attach or status command returns `execution_mode` and `gateway_tmux_window_index`
- **THEN** the guidance tells the agent to report those returned fields as the authoritative gateway execution metadata
- **AND THEN** it does not tell the agent to guess gateway topology from tmux window names or ordering

### Requirement: Gateway system skill documents notifier notification mode
The packaged `houmao-agent-gateway` system skill SHALL describe gateway `mail-notifier` as mailbox-driven notification control for mailbox-enabled sessions rather than as a generic reminder service.

The skill's mail-notifier guidance SHALL state that the default notifier mode is `any_inbox`, where any unarchived inbox mail remains notification-eligible.

The guidance SHALL document the opt-in `unread_only` mode, where only unread unarchived inbox mail is notification-eligible.

The guidance SHALL mention that `unread_only` is a lower-noise mode and that read-but-unarchived mail will not by itself trigger future notifier prompts in that mode.

#### Scenario: Gateway skill shows default notifier mode
- **WHEN** a caller reads the `houmao-agent-gateway` mail-notifier guidance
- **THEN** the guidance states that `any_inbox` is the default notifier mode
- **AND THEN** it describes that default as notification for unarchived inbox mail regardless of read or answered state

#### Scenario: Gateway skill shows unread-only opt-in mode
- **WHEN** a caller reads the `houmao-agent-gateway` mail-notifier guidance
- **THEN** the guidance documents `unread_only` as an opt-in notifier mode
- **AND THEN** it explains that read-but-unarchived mail is not notifier-eligible in that mode

#### Scenario: Gateway skill stays mail-specific
- **WHEN** a caller reads the notifier guidance in the packaged gateway skill
- **THEN** the skill presents `mail-notifier` as mailbox-driven notification control
- **AND THEN** it does not describe notifier mode as a generic unfinished-job persistence mechanism

