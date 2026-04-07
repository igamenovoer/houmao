## MODIFIED Requirements

### Requirement: System-skills reference documents the packaged agent-instance lifecycle skill and its boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-manage-agent-instance` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for managed-agent instance lifecycle guidance across:

- `agents launch`
- `project easy instance launch`
- `agents join`
- `agents list`
- `agents stop`
- `agents cleanup session|logs`

That page SHALL explain that `houmao-manage-agent-instance` remains the canonical lifecycle skill while `houmao-agent-messaging` becomes the canonical ordinary communication/control skill for already-running managed agents and `houmao-agent-gateway` becomes the canonical gateway-specific skill.

That page SHALL explain that mailbox surfaces, prompt/mail follow-up, gateway-only services, reset-context guidance, and specialist CRUD remain outside the packaged `houmao-manage-agent-instance` skill scope.

That page SHALL describe the CLI-default system-skill install selection as including the packaged specialist-management, credential-management, agent-definition, agent-instance, agent-messaging, and agent-gateway skills.

That page SHALL explain that managed launch and managed join auto-install the messaging and gateway skills but do not auto-install the separate lifecycle-only `houmao-manage-agent-instance` skill.

#### Scenario: Reader sees the packaged lifecycle skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-manage-agent-instance` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering managed-agent instance lifecycle rather than gateway or messaging guidance

#### Scenario: Reader sees the boundary between lifecycle, messaging, and gateway skills
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page distinguishes `houmao-manage-agent-instance` from `houmao-agent-messaging` and `houmao-agent-gateway`
- **AND THEN** it explains that prompt/mail follow-up belongs to messaging while gateway lifecycle, discovery, and gateway-only services belong to the gateway skill

#### Scenario: Reader sees the updated default install behavior
- **WHEN** a reader checks the install-selection behavior in `docs/reference/cli/system-skills.md`
- **THEN** the page explains that CLI-default installation includes lifecycle, messaging, and gateway skills
- **AND THEN** it explains that managed launch and managed join auto-install the messaging and gateway skills without auto-installing the lifecycle-only skill

### Requirement: System-skills reference documents the packaged agent-messaging skill and its communication-path boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-agent-messaging` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for communicating with already-running managed agents across:

- `agents prompt`
- `agents interrupt`
- `agents gateway prompt|interrupt`
- `agents gateway send-keys`
- `agents gateway tui state|history|note-prompt`
- `agents mail resolve-live|status|check|send|reply|mark-read`

That page SHALL explain that the packaged skill routes by communication intent and not by one hardcoded transport path.

That page SHALL explain that ordinary prompting should prefer the managed-agent seam, while gateway lifecycle, current-session discovery, notifier control, and wakeup guidance belong to `houmao-agent-gateway`.

That page SHALL explain that transport-specific mailbox behavior remains in the mailbox skill family rather than in `houmao-agent-messaging`.

#### Scenario: Reader sees the packaged messaging skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-agent-messaging` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering managed-agent communication rather than lifecycle or gateway-control-plane ownership

#### Scenario: Reader sees the communication-path boundary
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page explains the distinction between synchronous prompt turns, queued gateway requests, raw `send-keys`, mailbox follow-up, and the separate gateway skill's lifecycle or reminder services
- **AND THEN** it does not imply that those paths are interchangeable shortcuts

## ADDED Requirements

### Requirement: System-skills reference documents the packaged agent-gateway skill and its gateway-service boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-agent-gateway` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for gateway-focused work across:

- `agents gateway attach|detach|status`
- `agents gateway mail-notifier status|enable|disable`
- current-session versus explicit managed-agent gateway targeting
- direct live gateway route families such as `/v1/status`, `/v1/wakeups`, and `/v1/mail-notifier` when the exact live `gateway.base_url` is already known from supported discovery

That page SHALL explain that the packaged gateway skill prefers `houmao-mgr agents gateway ...` and managed-agent `/houmao/agents/{agent_ref}/gateway...` routes when those higher-level surfaces exist.

That page SHALL explain that wakeups are direct live-gateway HTTP in the current implementation and remain in-memory state that does not survive gateway restart.

That page SHALL explain that ordinary prompt/mail follow-up remains in `houmao-agent-messaging` and the mailbox skill family rather than in `houmao-agent-gateway`.

#### Scenario: Reader sees the packaged gateway skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-agent-gateway` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering gateway lifecycle, gateway discovery, and gateway-only reminder/control surfaces

#### Scenario: Reader sees the wakeup boundary clearly
- **WHEN** a reader opens the packaged gateway-skill section of `docs/reference/cli/system-skills.md`
- **THEN** the page explains that current wakeup control uses direct live gateway `/v1/wakeups` routes
- **AND THEN** it does not imply that wakeups are durable across gateway restart or already projected through `houmao-mgr agents gateway ...`
