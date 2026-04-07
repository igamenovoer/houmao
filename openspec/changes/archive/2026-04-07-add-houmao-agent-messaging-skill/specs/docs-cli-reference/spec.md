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

That page SHALL explain that `houmao-manage-agent-instance` remains the canonical lifecycle skill while `houmao-agent-messaging` becomes the canonical communication/control skill for already-running managed agents.

That page SHALL explain that mailbox surfaces, prompt/gateway control, reset-context guidance, and specialist CRUD remain outside the packaged `houmao-manage-agent-instance` skill scope.

That page SHALL describe the CLI-default system-skill install selection as including the packaged specialist-management, credential-management, agent-definition, agent-instance, and agent-messaging skills.

That page SHALL explain that managed launch and managed join auto-install the messaging skill but do not auto-install the separate lifecycle-only `houmao-manage-agent-instance` skill.

#### Scenario: Reader sees the packaged lifecycle skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-manage-agent-instance` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering managed-agent instance lifecycle rather than managed-agent messaging

#### Scenario: Reader sees the boundary between lifecycle and messaging skills
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page distinguishes `houmao-manage-agent-instance` from `houmao-agent-messaging`
- **AND THEN** it explains that prompt, gateway, interrupt, raw-input, and reset-context guidance belongs to the latter

#### Scenario: Reader sees the updated default install behavior
- **WHEN** a reader checks the install-selection behavior in `docs/reference/cli/system-skills.md`
- **THEN** the page explains that CLI-default installation includes both lifecycle and messaging skills
- **AND THEN** it explains that managed launch and managed join auto-install the messaging skill without auto-installing the lifecycle-only skill

## ADDED Requirements

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

That page SHALL explain that ordinary prompting should prefer the managed-agent seam, while direct gateway HTTP remains a lower-level path for gateway-only control behaviors such as current reset-context APIs.

That page SHALL explain that transport-specific mailbox behavior remains in the mailbox skill family rather than in `houmao-agent-messaging`.

#### Scenario: Reader sees the new packaged messaging skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-agent-messaging` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering managed-agent communication rather than lifecycle or specialist authoring

#### Scenario: Reader sees the communication-path boundary
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page explains the distinction between synchronous prompt turns, queued gateway requests, raw `send-keys`, mailbox follow-up, and lower-level reset-context APIs
- **AND THEN** it does not imply that those paths are interchangeable shortcuts
