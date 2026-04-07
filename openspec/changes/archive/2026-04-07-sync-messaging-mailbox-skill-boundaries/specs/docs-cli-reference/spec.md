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

That page SHALL explain that `houmao-manage-agent-instance` remains the canonical lifecycle skill while `houmao-agent-messaging` becomes the canonical ordinary communication/control and mailbox-routing skill for already-running managed agents, `houmao-agent-email-comms` remains the ordinary mailbox operations skill, and `houmao-agent-gateway` becomes the canonical gateway-specific skill.

That page SHALL explain that mailbox surfaces, prompting, mailbox routing, ordinary mailbox operations, gateway-only services, reset-context guidance, and specialist CRUD remain outside the packaged `houmao-manage-agent-instance` skill scope.

That page SHALL describe the CLI-default system-skill install selection as including the packaged specialist-management, credential-management, agent-definition, agent-instance, agent-messaging, and agent-gateway skills.

That page SHALL explain that managed launch and managed join auto-install the messaging and gateway skills but do not auto-install the separate lifecycle-only `houmao-manage-agent-instance` skill.

#### Scenario: Reader sees the packaged lifecycle skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-manage-agent-instance` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering managed-agent instance lifecycle rather than gateway or messaging guidance

#### Scenario: Reader sees the boundary between lifecycle, messaging, and gateway skills
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page distinguishes `houmao-manage-agent-instance` from `houmao-agent-messaging` and `houmao-agent-gateway`
- **AND THEN** it explains that prompting and mailbox routing belong to messaging, ordinary mailbox operations belong to the mailbox skill family, and gateway lifecycle, discovery, and gateway-only services belong to the gateway skill

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
- `agents mail resolve-live`

That page SHALL explain that the packaged skill routes by communication intent and not by one hardcoded transport path.

That page SHALL explain that ordinary prompting should prefer the managed-agent seam, that mailbox discovery and mailbox routing begin from `agents mail resolve-live`, and that ordinary mailbox operations belong to `houmao-agent-email-comms` while notifier-round mailbox workflow belongs to `houmao-process-emails-via-gateway`.

That page SHALL explain that gateway lifecycle, current-session discovery, notifier control, and wakeup guidance belong to `houmao-agent-gateway`.

That page SHALL explain that transport-specific mailbox behavior remains in the mailbox skill family rather than in `houmao-agent-messaging`.

#### Scenario: Reader sees the packaged messaging skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-agent-messaging` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering managed-agent communication and mailbox routing rather than lifecycle or gateway-control-plane ownership

#### Scenario: Reader sees the communication-path boundary
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page explains the distinction between synchronous prompt turns, queued gateway requests, raw `send-keys`, mailbox handoff, ordinary mailbox operations in the mailbox skills, and the separate gateway skill's lifecycle or reminder services
- **AND THEN** it does not imply that those paths are interchangeable shortcuts
