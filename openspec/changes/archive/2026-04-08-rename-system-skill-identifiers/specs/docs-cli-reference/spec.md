## MODIFIED Requirements

### Requirement: System-skills reference documents the renamed specialist-management skill
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe the current project-easy packaged skill as `houmao-specialist-mgr`.

That page SHALL describe the packaged skill as the Houmao-owned specialist-management entry point for `project easy specialist create|list|get|remove` plus specialist-scoped `project easy instance launch|stop`.

The page SHALL describe the top-level packaged skill page as an index/router and SHALL state that further agent management after those specialist-scoped runtime actions goes to `houmao-agent-instance`.

The page SHALL NOT continue to describe `houmao-manage-specialist` as the active packaged project-easy skill.

#### Scenario: Reader sees the renamed packaged skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-specialist-mgr` as the packaged project-easy skill
- **AND THEN** it describes that skill as covering `create`, `list`, `get`, `remove`, `launch`, and `stop`

#### Scenario: Reader does not see the superseded packaged specialist name
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page does not present `houmao-manage-specialist` as the current packaged specialist-management skill

### Requirement: System-skills reference documents the packaged `houmao-mailbox-mgr` skill and its mailbox-admin boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-mailbox-mgr` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for mailbox-administration guidance across:

- `houmao-mgr mailbox ...`
- `houmao-mgr project mailbox ...`
- `houmao-mgr agents mailbox ...`

That page SHALL explain that `houmao-mailbox-mgr` covers filesystem mailbox root lifecycle, mailbox account lifecycle, structural mailbox inspection, and late filesystem mailbox binding for existing local managed agents.

That page SHALL explain that ordinary mailbox participation remains in `houmao-agent-email-comms`, notifier-driven unread-email rounds remain in `houmao-process-emails-via-gateway`, and gateway mail-notifier control remains in `houmao-agent-gateway`.

That page SHALL explain that the maintained mailbox-admin CLI remains filesystem-oriented in v1 and that Stalwart stays a transport/bootstrap boundary rather than a peer mailbox-admin CLI family.

#### Scenario: Reader sees the packaged mailbox-admin skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-mailbox-mgr` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering mailbox administration across mailbox, project mailbox, and agents mailbox surfaces

#### Scenario: Reader sees the boundary between mailbox admin and mailbox participation
- **WHEN** a reader opens the packaged mailbox-admin skill section of `docs/reference/cli/system-skills.md`
- **THEN** the page distinguishes mailbox root and binding administration from ordinary mailbox send/check/reply work
- **AND THEN** it does not imply that `houmao-mailbox-mgr` replaces `houmao-agent-email-comms`, `houmao-process-emails-via-gateway`, or `houmao-agent-gateway`
- **AND THEN** it explains that follow-up live-agent management after specialist launch or stop belongs to `houmao-agent-instance`

### Requirement: System-skills reference documents the packaged agent-instance lifecycle skill and its boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-agent-instance` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for managed-agent instance lifecycle guidance across:

- `agents launch`
- `project easy instance launch`
- `agents join`
- `agents list`
- `agents stop`
- `agents cleanup session|logs`

That page SHALL explain that `houmao-agent-instance` remains the canonical lifecycle skill while `houmao-agent-messaging` becomes the canonical ordinary communication/control and mailbox-routing skill for already-running managed agents, `houmao-agent-email-comms` remains the ordinary mailbox operations skill, and `houmao-agent-gateway` becomes the canonical gateway-specific skill.

That page SHALL explain that mailbox surfaces, prompting, mailbox routing, ordinary mailbox operations, gateway-only services, reset-context guidance, and specialist CRUD remain outside the packaged `houmao-agent-instance` skill scope.

That page SHALL describe the CLI-default system-skill install selection as including the packaged specialist-management, credential-management, agent-definition, agent-instance, agent-messaging, and agent-gateway skills, using the active names `houmao-specialist-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, `houmao-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway`.

That page SHALL explain that managed launch and managed join auto-install the messaging and gateway skills but do not auto-install the separate lifecycle-only `houmao-agent-instance` skill.

#### Scenario: Reader sees the packaged lifecycle skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-agent-instance` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering managed-agent instance lifecycle rather than gateway or messaging guidance

#### Scenario: Reader sees the boundary between lifecycle, messaging, and gateway skills
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page distinguishes `houmao-agent-instance` from `houmao-agent-messaging` and `houmao-agent-gateway`
- **AND THEN** it explains that prompting and mailbox routing belong to messaging, ordinary mailbox operations belong to the mailbox skill family, and gateway lifecycle, discovery, and gateway-only services belong to the gateway skill

#### Scenario: Reader sees the updated default install behavior
- **WHEN** a reader checks the install-selection behavior in `docs/reference/cli/system-skills.md`
- **THEN** the page explains that CLI-default installation includes lifecycle, messaging, and gateway skills
- **AND THEN** it explains that managed launch and managed join auto-install the messaging and gateway skills without auto-installing the lifecycle-only skill
