## MODIFIED Requirements

### Requirement: System-skills reference documents the packaged agent-messaging skill and its communication-path boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-agent-messaging` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for communicating with already-running managed agents across:

- `agents prompt`
- `agents interrupt`
- `agents gateway prompt|interrupt`
- `agents gateway send-keys`
- `agents gateway tui state|history|note-prompt`
- `agents mail resolve-live`

That page SHALL explain that the packaged skill routes by communication intent and not by one hardcoded transport path.

That page SHALL explain that ordinary prompting should prefer the managed-agent seam, that mailbox discovery and mailbox routing begin from `agents mail resolve-live`, and that ordinary mailbox operations belong to `houmao-agent-email-comms` while notifier-round mailbox workflow belongs to `houmao-process-emails-via-gateway`.

That page SHALL explain that gateway lifecycle, current-session discovery, notifier control, and reminder guidance belong to `houmao-agent-gateway`.

That page SHALL explain that transport-specific mailbox behavior remains in the mailbox skill family rather than in `houmao-agent-messaging`.

#### Scenario: Reader sees the packaged messaging skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-agent-messaging` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering managed-agent communication and mailbox routing rather than lifecycle or gateway-control-plane ownership

#### Scenario: Reader sees the communication-path boundary
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page explains the distinction between synchronous prompt turns, queued gateway requests, raw `send-keys`, mailbox handoff, ordinary mailbox operations in the mailbox skills, and the separate gateway skill's lifecycle or reminder services
- **AND THEN** it does not imply that those paths are interchangeable shortcuts

### Requirement: System-skills reference documents the packaged agent-gateway skill and its gateway-service boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-agent-gateway` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for gateway-focused work across:

- `agents gateway attach|detach|status`
- `agents gateway mail-notifier status|enable|disable`
- current-session versus explicit managed-agent gateway targeting
- direct live gateway route families such as `/v1/status`, `/v1/reminders`, and `/v1/mail-notifier` when the exact live `gateway.base_url` is already known from supported discovery

That page SHALL explain that the packaged gateway skill prefers `houmao-mgr agents gateway ...` and managed-agent `/houmao/agents/{agent_ref}/gateway...` routes when those higher-level surfaces exist.

That page SHALL explain that reminders are direct live-gateway HTTP in the current implementation, remain in-memory state that does not survive gateway restart, and are selected by smallest ranking value rather than by independent wakeup-job ownership.

That page SHALL explain that ordinary prompt/mail follow-up remains in `houmao-agent-messaging` and the mailbox skill family rather than in `houmao-agent-gateway`.

#### Scenario: Reader sees the packaged gateway skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-agent-gateway` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering gateway lifecycle, gateway discovery, and gateway-only reminder/control surfaces

#### Scenario: Reader sees the reminder boundary clearly
- **WHEN** a reader opens the packaged gateway-skill section of `docs/reference/cli/system-skills.md`
- **THEN** the page explains that current reminder control uses direct live gateway `/v1/reminders` routes
- **AND THEN** it does not imply that reminders are durable across gateway restart or already projected through `houmao-mgr agents gateway ...`
