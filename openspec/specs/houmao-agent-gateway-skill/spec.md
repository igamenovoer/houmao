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
- `houmao-mgr agents gateway mail-notifier status|enable|disable`
- managed-agent HTTP routes under `/houmao/agents/{agent_ref}/gateway...`
- direct live gateway HTTP only when the exact live `{gateway.base_url}` is already available and the task genuinely needs a gateway-only surface such as `/v1/status`, `/v1/wakeups`, or `/v1/mail-notifier`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `lifecycle`
- `discover`
- `gateway-services`
- `wakeups`
- `mail-notifier`

That packaged skill SHALL remain the canonical Houmao-owned skill for gateway-specific lifecycle, discovery, gateway-only control, and reminder work whether the caller is another agent with an installed Houmao skill home or an external operator standing outside the managed session.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `agents launch|join|stop|relaunch|cleanup`
- `project easy specialist create|list|get|remove`
- ordinary prompt or mailbox follow-up that is already satisfied by `houmao-agent-messaging` and the mailbox skills
- mailbox transport-specific filesystem or Stalwart internals
- inventing new `houmao-mgr`, managed-agent API, or direct gateway routes that the current implementation does not expose

#### Scenario: Installed skill points the caller at the supported gateway surfaces
- **WHEN** an agent or operator opens the installed `houmao-agent-gateway` skill
- **THEN** the skill directs the caller to the supported gateway lifecycle, discovery, gateway-only control, and reminder surfaces
- **AND THEN** it does not redirect the caller to unrelated live-agent lifecycle, ordinary messaging, or transport-local mailbox repair work

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-agent-gateway` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for lifecycle, discovery, gateway-only services, wakeups, and notifier guidance
- **AND THEN** the detailed workflow lives in local action-specific documents rather than in one flattened entry page

#### Scenario: Installed skill keeps non-gateway concerns out of scope
- **WHEN** an agent reads the installed `houmao-agent-gateway` skill
- **THEN** the skill marks ordinary prompt/mail flows, transport-specific mailbox internals, and unrelated live-agent lifecycle work as outside the packaged skill scope
- **AND THEN** it does not present `houmao-agent-gateway` as the generic replacement for `houmao-manage-agent-instance`, `houmao-agent-messaging`, or the mailbox skills

### Requirement: `houmao-agent-gateway` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-agent-gateway` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace in this order:

1. repo-local `.venv` executable,
2. Pixi-managed project invocation,
3. project-local `uv run`,
4. globally installed `houmao-mgr` from uv tools.

The skill SHALL treat global uv-tools installation as the default end-user case when no development-project hints justify a repo-local launcher.

The skill SHALL tell the agent to look for development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` before choosing a repo-local launcher.

The resolved launcher SHALL be reused for any routed gateway action selected through the packaged skill.

#### Scenario: Repo-local `.venv` takes precedence over other launchers
- **WHEN** the current workspace provides `.venv/bin/houmao-mgr`
- **THEN** the skill tells the agent to use that repo-local executable first
- **AND THEN** it does not prefer Pixi, project-local `uv run`, or the global uv-tools install for that workspace

#### Scenario: Pixi-managed project takes precedence when no `.venv` launcher exists
- **WHEN** the current workspace has no repo-local `.venv` launcher
- **AND WHEN** the current workspace has Pixi development-project hints
- **THEN** the skill tells the agent to use `pixi run houmao-mgr`
- **AND THEN** it does not skip directly to project-local `uv run` or the global uv-tools install

#### Scenario: Global uv-tools install remains the end-user default
- **WHEN** the current workspace does not provide repo-local `.venv`, Pixi, or project-local uv hints
- **THEN** the skill tells the agent to use the globally installed `houmao-mgr` command from uv tools
- **AND THEN** it treats that path as the ordinary end-user launcher

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
- use direct `{gateway.base_url}/v1/wakeups...` only for wakeup registration, inspection, and cancellation because the current implementation does not project those operations through a higher-level CLI or managed-agent route,
- use direct `{gateway.base_url}/v1/...` only when the task genuinely requires a gateway-only lower-level surface and the exact live base URL is already available from supported discovery.

The packaged `houmao-agent-gateway` skill SHALL delegate ordinary prompt turns, mailbox follow-up, or transport-specific mailbox work to:

- `houmao-agent-messaging`
- `houmao-process-emails-via-gateway`
- `houmao-email-via-agent-gateway`
- `houmao-email-via-filesystem`
- `houmao-email-via-stalwart`

The skill SHALL prefer the managed-agent seam first when it already satisfies the current task and SHALL treat direct gateway listener URLs as the lower-level gateway-only path.

#### Scenario: Lifecycle and notifier work stay on the managed-agent seam when possible
- **WHEN** the user asks for gateway attach, detach, status, or mail-notifier control
- **THEN** the skill directs the caller to `houmao-mgr agents gateway ...` or the managed-agent `/houmao/agents/{agent_ref}/gateway...` routes
- **AND THEN** it does not require direct gateway listener discovery when the higher-level seam already satisfies the task

#### Scenario: Wakeups use the direct live gateway route family
- **WHEN** the user asks to create, inspect, or cancel one gateway wakeup job
- **THEN** the skill directs the caller to the live `{gateway.base_url}/v1/wakeups...` route family
- **AND THEN** it does not misdescribe wakeups as a current `houmao-mgr agents gateway ...` subcommand or as a managed-agent API projection that does not exist yet

#### Scenario: Ordinary prompt or mailbox work delegates away from the gateway skill
- **WHEN** the task is one normal prompt turn, one transport-neutral interrupt, or one mailbox follow-up action rather than gateway lifecycle or gateway-only service control
- **THEN** the skill directs the caller to `houmao-agent-messaging` and the existing mailbox skills instead of taking that work itself
- **AND THEN** it does not present the gateway skill as the primary ordinary communication surface

### Requirement: `houmao-agent-gateway` describes wakeups and mail-notifier honestly
The packaged `houmao-agent-gateway` skill SHALL describe `/v1/wakeups` as the supported gateway-owned timer and self-reminder surface for one live attached gateway.

The skill SHALL state that wakeup jobs are live-gateway in-memory state, are lost on gateway shutdown or restart, and are not a durable unfinished-job queue.

The skill SHALL describe `mail-notifier` as unread-mail reminder control for mailbox-enabled sessions and SHALL NOT present it as a general-purpose reminder service for arbitrary unfinished work.

The skill SHALL NOT describe wakeups or mail-notifier as durable queued work that survives gateway restart.

#### Scenario: Wakeup guidance states the in-memory lifetime clearly
- **WHEN** an attached agent or operator reads the wakeup guidance in the packaged gateway skill
- **THEN** the skill states that wakeups are process-local live-gateway state
- **AND THEN** it does not claim that scheduled or overdue wakeups survive gateway stop or restart

#### Scenario: Mail-notifier guidance stays mail-specific
- **WHEN** a caller reads the notifier guidance in the packaged gateway skill
- **THEN** the skill presents `mail-notifier` as unread-mail reminder control through the gateway mailbox facade
- **AND THEN** it does not describe notifier control as the generic answer for arbitrary unfinished-job persistence

